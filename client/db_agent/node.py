import json
import os
import re
import asyncio
from langchain_core.messages import SystemMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from db_agent.state import AgentState
from .mcp_client import MCPClient
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Initialize MCP client
mcp_client = MCPClient()

def extract_text_from_result(result) -> str:
    if hasattr(result, "content") and isinstance(result.content, list):
        texts = []
        for item in result.content:
            if hasattr(item, "text"):
                texts.append(item.text)
        joined = "\n".join(texts)
    elif isinstance(result, dict) and "content" in result:
        joined = json.dumps(result["content"], ensure_ascii=False)
    else:
        joined = str(result)
    return joined.strip()

def clean_schema_text(raw_text: str) -> str:
    if not raw_text:
        return "No schema available."
    text = extract_text_from_result(raw_text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    tables = re.findall(r"CREATE TABLE.*?;\n", text, flags=re.DOTALL | re.IGNORECASE)
    if tables:
        cleaned = "\n\n".join(tables).strip()
    else:
        cleaned = text.strip()
    return cleaned

# 1. Planner LLM - Đánh giá câu hỏi và chọn tool
async def planner_llm(state: AgentState) -> AgentState:
    
    q = state["question"] 
    iteration_count = state.get("iteration_count", 0)
    execution_history = state.get("execution_history", [])
    
    # Get available tools from MCP server
    if not mcp_client.connected:
        await mcp_client.connect()
    
    available_tools = await mcp_client.get_available_tools()
    enhanced_tool_metadata = {}
    if available_tools:
        for tool in available_tools:
            try:
                tool_dict = tool.model_dump() if hasattr(tool, "model_dump") else dict(tool)
                name = tool_dict.get("name", "")
                desc = tool_dict.get("description", "")
                inputs = list(tool_dict.get("inputSchema", {}).get("properties", {}).keys())
                outputs = list(tool_dict.get("outputSchema", {}).get("properties", {}).keys())

                enhanced_tool_metadata[name] = {
                    "name": name,
                    "description": desc.strip(),
                    "inputs": inputs,
                    "outputs": outputs
                }
            except Exception as e:
                logger.warning(f"Error parsing tool metadata: {e}")
    
    has_schema = False
    for exec_info in execution_history:
        if exec_info.get("tool") == "list_tables" and not exec_info.get("error", False):
            has_schema = True
            break
    
    history_context = ""
    if execution_history:
        history_context = "\nPrevious tool executions:\n"
        for i, exec_info in enumerate(execution_history, start=1):
            tool_name = exec_info.get("tool", "")
            result_obj = exec_info.get("result", "")
            result_text = extract_text_from_result(result_obj)
            history_context += f"Step {i}: {tool_name}\n{result_text}\n\n"
    
    planner_prompt = f"""
    You are a Planner LLM. Based on the database-specific question assigned to you and execution history, choose the most appropriate tool.
    
    Available tools:
    {json.dumps(enhanced_tool_metadata, indent=2, ensure_ascii=False)}
    
    Database task assigned: "{q}"
    Current iteration: {iteration_count + 1}
    Schema already available: {has_schema}
    {history_context}
    
    IMPORTANT RULES:
    1. If list_tables has already been executed and schema is available, DO NOT choose list_tables again
    2. If schema is available, prefer query_sql to get specific data
    3. Only choose list_tables if no schema information is available yet
    4. Use query_sql for database overview questions and statistics
    5. Use query_sql for relationship analysis and complex queries
    
    Consider:
    1. What information is needed to answer the user's question?
    2. What tools have been executed before and what did they return?
    3. Is additional information needed from the database?
    
    Respond with ONLY the tool name from the available tools above.
    """
    
    selected_tool = llm.invoke(planner_prompt).content.strip().lower()
    # logger.info(f"Prompt Node Planner LLM: {planner_prompt}")
    logger.info(f"Planner LLM selected tool: {selected_tool}")
    
    if selected_tool == "list_tables" and has_schema:
        logger.warning(f"Planner LLM selected list_tables but schema already available, overriding to query_sql")
        selected_tool = "query_sql"
    
    valid_tools = list(enhanced_tool_metadata.keys())
    if selected_tool not in valid_tools:
        logger.warning(f"Invalid tool selection: {selected_tool}, defaulting to query_sql")
        selected_tool = "query_sql"

    return {
        **state, 
        "selected_tool": selected_tool,
        "tool_metadata": enhanced_tool_metadata.get(selected_tool, {})
    }

# 2. Executor - Thực thi tool được chọn
async def executor(state: AgentState) -> AgentState:
    
    selected_tool = state["selected_tool"]
    question = state["question"]
    execution_history = state.get("execution_history", [])
    tool_results = state.get("tool_results", [])    
    logger.info(f"Executing tool: {selected_tool}")
    
    try:
        if not mcp_client.connected:
            await mcp_client.connect()
        
        if selected_tool == "list_tables":
            result = await mcp_client.call_tool("list_tables", {})
        elif selected_tool == "query_sql":
            schema_info = None
            for exec_info in execution_history:
                if exec_info.get("tool") == "list_tables" and not exec_info.get("error"):
                    schema_info = exec_info.get("result")
                    break

            if not schema_info:
                try:
                    schema_info = await mcp_client.call_tool("list_tables", {})
                except Exception as e:
                    schema_info = f"Could not retrieve schema: {str(e)}"

            schema_info = clean_schema_text(schema_info)
    
            sql_prompt = f"""
            You are a SQL generator. Convert the user question to a valid SQL SELECT query.
            
            Database Schema Information:
            {schema_info}
            
            Rules:
            - Use only SELECT statements.
            - Never use UPDATE, DELETE, DROP, or INSERT.
            - Always use exact table and column names from the provided schema.
            - For requests like "list all [table]" → SELECT * FROM [exact_table_name].
            - For multi-table questions, you may generate separate SELECT queries (each separated by semicolons).
            - Each SQL statement will be executed separately.
            - Do not include explanations or markdown formatting — return only raw SQL.

            User Question: "{question}"
            
            Return ONLY the SQL query without explanations or markdown formatting.
            """
            
            sql = llm.invoke(sql_prompt).content.strip()
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()
            logger.info(f"Generated SQL: {sql}")
            result = await mcp_client.call_tool("query_sql", {"sql": sql})
        else:
            result = f"Unknown tool: {selected_tool}"
            
        clean_result = extract_text_from_result(result)
        new_execution_history = execution_history + [{
            "tool": selected_tool,
            "result": clean_result,
            "iteration": state.get("iteration_count", 0) + 1
        }]
        
        new_tool_results = tool_results + [result]
        logger.info(f"Tool execution successful: {selected_tool}")
        
        return {
            **state,
            "tool_results": new_tool_results,
            "execution_history": new_execution_history
        }
        
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logger.error(f"Tool execution error: {error_msg}")
        
        new_execution_history = execution_history + [{
            "tool": selected_tool,
            "result": error_msg,
            "iteration": state.get("iteration_count", 0) + 1,
            "error": True
        }]
        
        return {
            **state,
            "execution_history": new_execution_history
        }

# 3. Evaluator LLM - Đánh giá kết quả có đủ chưa
def evaluator_llm(state: AgentState) -> AgentState:
    
    question = state["question"]
    tool_results = state.get("tool_results", [])
    execution_history = state.get("execution_history", [])
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 5)    
    all_results = "\n".join([str(result) for result in tool_results])
    
    has_schema = False
    schema_available = False
    for exec_info in execution_history:
        if exec_info.get("tool") == "list_tables" and not exec_info.get("error", False):
            has_schema = True
            schema_available = True
            break
    
    # Kiểm tra xem có query_sql lặp lại không
    query_sql_count = 0
    recent_queries = []
    for exec_info in execution_history:
        if exec_info.get("tool") == "query_sql" and not exec_info.get("error", False):
            query_sql_count += 1
            # Lấy SQL query từ result (nếu có)
            result = exec_info.get("result", "")
            if result and "SELECT" in result:
                recent_queries.append(result[:100])
    
    has_repetitive_queries = len(set(recent_queries)) < len(recent_queries) if recent_queries else False
        
    evaluator_prompt = f"""
        You are an Evaluator LLM. Assess whether the current results adequately answer the user's question.

        User Question: "{question}"
        Current Results: {all_results}
        Iteration: {iteration_count + 1}/{max_iterations}
        
        IMPORTANT: Analysis
        - Has list_tables been executed: {has_schema}
        - Schema is available: {schema_available}
        - Query SQL executed count: {query_sql_count}
        - Has repetitive queries: {has_repetitive_queries}
        
        CRITICAL RULES:
        1. If list_tables has already been executed and schema is available, do not request list_tables again
        2. If query_sql has been executed multiple times with similar results, consider it complete
        3. If the same SQL queries are being repeated, mark as complete
        4. If query_sql_count >= 3, likely complete
        5. Only mark as incomplete if genuinely new information is needed
        
        EVALUATION CRITERIA:
        - Does the current data answer the user's question?
        - Are we getting repetitive results?
        - Would additional queries provide genuinely new information?
        
        Respond with ONLY one word:
        - "complete" (if the question is answered or results are repetitive)
        - "incomplete" (if genuinely new information is needed)
        """
    
    evaluation_result = llm.invoke(evaluator_prompt).content.strip().lower()
    if evaluation_result.startswith("complete"):
        is_complete = True
    else:
        is_complete = False
    
    if iteration_count >= max_iterations:
        logger.warning(f"Max iterations reached ({max_iterations}), forcing complete")
        is_complete = True
    
    if has_repetitive_queries and query_sql_count >= 2:
        logger.warning(f"Repetitive queries detected, forcing complete")
        is_complete = True
    
    if query_sql_count >= 3:
        logger.warning(f"Too many query_sql executions ({query_sql_count}), forcing complete")
        is_complete = True
    
    logger.info(f"Evaluator LLM result: {evaluation_result}")
    logger.info(f"Assessment: {'Complete' if is_complete else 'Incomplete'}")
    
    return {
        **state,
        "is_complete": is_complete,
        "evaluation_reason": evaluation_result,
        "iteration_count": iteration_count + 1
    }

# 4. Final Answer Generator - Kết hợp reasoning và kết quả cuối
def final_answer_generator(state: AgentState) -> AgentState:
    question = state["question"]
    tool_results = state.get("tool_results", [])
    execution_history = state.get("execution_history", [])    
    all_results = "\n".join([str(result) for result in tool_results])
    final_prompt = f"""
    You are a Final Answer Generator. Create a comprehensive, natural language answer.
    
    Current User Question: "{question}"
    Database Results: {all_results}
    
    Execution History:
    {json.dumps(execution_history, indent=2)}
    
    Requirements:
    1. Provide a clear, direct answer to the user's question
    2. Use natural language reasoning to explain the results
    3. Include relevant data from the database results
    4. Make the answer informative and easy to understand
    5. If there are multiple results, synthesize them coherently
    6. Consider the conversation context - if this is a follow-up question, reference previous results appropriately
    
    Generate a comprehensive final answer that combines natural language reasoning with the database results.
    """
    
    final_answer = llm.invoke(final_prompt).content
    logger.info(f"Generated final answer: {final_answer}")
    
    return {
        **state,
        "final_answer": final_answer
    }

