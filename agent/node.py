import json
from langchain_openai import ChatOpenAI
from .state import AgentState
from .tools import list_tables_tool, query_sql_tool
import logging
logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

TOOL_METADATA = {
    "list_tables": {
        "name": "list_tables",
        "description": "List all tables in the database with schema and sample rows",
        "use_case": "Use when user asks for general table information, schema, or structure"
    },
    "query_sql": {
        "name": "query_sql", 
        "description": "Execute SQL SELECT queries to get specific data",
        "use_case": "Use when user asks for specific data, calculations, rankings, or complex queries"
    }
}

# 1. Kiểm tra câu hỏi có liên quan DB không
def check_relevancy(state: AgentState) -> AgentState:
    q = state["question"]
    prompt = f"""
    You are a classifier. User question: "{q}"
    If related to SQL/Database, respond 'relevant', else 'not_relevant'.
    """
    resp = llm.invoke(prompt).content.strip().lower()
    logger.info(f"Relevancy: {resp}")
    
    relevancy = "not_relevant" if "not_relevant" in resp else "relevant"
    logger.info(f"Setting relevancy to: {relevancy}")
    
    return {**state, "relevancy": relevancy}

# 2. Planner LLM - Đánh giá câu hỏi và chọn tool
def planner_llm(state: AgentState) -> AgentState:
    relevancy = state.get("relevancy")
    if relevancy != "relevant":
        logger.warning(f"Planner LLM called with relevancy: {relevancy}, skipping...")
        return state
    
    q = state["question"]
    iteration_count = state.get("iteration_count", 0)
    execution_history = state.get("execution_history", [])
    
    has_schema = False
    for exec_info in execution_history:
        if exec_info.get("tool") == "list_tables" and not exec_info.get("error", False):
            has_schema = True
            break
    
    history_context = ""
    if execution_history:
        history_context = "\nPrevious tool executions:\n"
        for i, exec_info in enumerate(execution_history):
            history_context += f"Step {i+1}: {exec_info.get('tool', '')} -> {exec_info.get('result', '')[:200]}...\n"
    
    planner_prompt = f"""
    You are a Planner LLM. Based on the user's question and execution history, choose the most appropriate tool.
    
    Available tools:
    {json.dumps(TOOL_METADATA, indent=2)}
    
    User question: "{q}"
    Current iteration: {iteration_count + 1}
    Schema already available: {has_schema}
    {history_context}
    
    IMPORTANT RULES:
    1. If list_tables has already been executed and schema is available, DO NOT choose list_tables again
    2. If schema is available, prefer query_sql to get specific data
    3. Only choose list_tables if no schema information is available yet
    
    Consider:
    1. What information is needed to answer the user's question?
    2. What tools have been executed before and what did they return?
    3. Is additional information needed from the database?
    
    Respond with ONLY the tool name: "list_tables" or "query_sql"
    """
    
    selected_tool = llm.invoke(planner_prompt).content.strip().lower()
    logger.info(f"Planner LLM selected tool: {selected_tool}")
    
    if selected_tool == "list_tables" and has_schema:
        logger.warning(f"Planner LLM selected list_tables but schema already available, overriding to query_sql")
        selected_tool = "query_sql"
    
    if selected_tool not in ["list_tables", "query_sql"]:
        logger.warning(f"Invalid tool selection: {selected_tool}, defaulting to query_sql")
        selected_tool = "query_sql"
    
    return {
        **state, 
        "selected_tool": selected_tool,
        "tool_metadata": TOOL_METADATA[selected_tool]
    }

# 3. Executor - Thực thi tool được chọn
def executor(state: AgentState) -> AgentState:
    relevancy = state.get("relevancy")
    if relevancy != "relevant":
        logger.warning(f"Executor called with relevancy: {relevancy}, skipping...")
        return state
    
    selected_tool = state["selected_tool"]
    question = state["question"]
    execution_history = state.get("execution_history", [])
    tool_results = state.get("tool_results", [])
    
    logger.info(f"Executing tool: {selected_tool}")
    
    try:
        if selected_tool == "list_tables":
            result = list_tables_tool._run()
        elif selected_tool == "query_sql":
            schema_info = None
            for exec_info in execution_history:
                if exec_info.get("tool") == "list_tables":
                    schema_info = exec_info.get("result")
                    break
            
            if not schema_info:
                try:
                    schema_info = list_tables_tool._run()
                except Exception as e:
                    schema_info = f"Could not retrieve schema: {str(e)}"
            
            sql_prompt = f"""
            You are a SQL generator. Convert the user question to a valid SQL SELECT query.
            
            Database Schema Information:
            {schema_info}
            
            Rules:
            - Only use SELECT statements
            - No UPDATE, DELETE, DROP, or INSERT
            - Use the exact table and column names from the schema above
            - For "list all [table_name]" → SELECT * FROM [exact_table_name]
            - Be precise with column names and table names from the schema
            - If schema shows table names, use those exact names
            - NEVER use UNION ALL with LIMIT in a single query
            - For multiple tables, generate separate queries for each table
            - Use LIMIT only on individual SELECT statements, not on UNION queries
            - If user asks for "top 5 tables with most columns", use separate queries for each table
            - You can generate multiple SQL statements separated by semicolons
            - Each statement will be executed separately
            
            User question: "{question}"
            
            Return ONLY the SQL query without explanations or markdown formatting.
            """
            
            sql = llm.invoke(sql_prompt).content.strip()
            if sql.startswith("```sql"):
                sql = sql.replace("```sql", "").replace("```", "").strip()
            elif sql.startswith("```"):
                sql = sql.replace("```", "").strip()
            
            logger.info(f"Generated SQL: {sql}")
            result = query_sql_tool._run(sql)
        else:
            result = f"Unknown tool: {selected_tool}"
            
        new_execution_history = execution_history + [{
            "tool": selected_tool,
            "result": result,
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

# 4. Evaluator LLM - Đánh giá kết quả có đủ chưa
def evaluator_llm(state: AgentState) -> AgentState:
    relevancy = state.get("relevancy")
    if relevancy != "relevant":
        logger.warning(f"Evaluator LLM called with relevancy: {relevancy}, skipping...")
        return state
    
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
            if "SELECT" in result:
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
    elif evaluation_result.startswith("incomplete"):
        is_complete = False
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

# 5. Final Answer Generator - Kết hợp reasoning và kết quả cuối
def final_answer_generator(state: AgentState) -> AgentState:
    question = state["question"]
    tool_results = state.get("tool_results", [])
    execution_history = state.get("execution_history", [])
    
    all_results = "\n".join([str(result) for result in tool_results])
    
    final_prompt = f"""
    You are a Final Answer Generator. Create a comprehensive, natural language answer.
    
    User Question: "{question}"
    Database Results: {all_results}
    
    Execution History:
    {json.dumps(execution_history, indent=2)}
    
    Requirements:
    1. Provide a clear, direct answer to the user's question
    2. Use natural language reasoning to explain the results
    3. Include relevant data from the database results
    4. Make the answer informative and easy to understand
    5. If there are multiple results, synthesize them coherently
    
    Generate a comprehensive final answer that combines natural language reasoning with the database results.
    """
    
    final_answer = llm.invoke(final_prompt).content
    logger.info(f"Generated final answer: {final_answer[:200]}...")
    
    return {
        **state,
        "final_answer": final_answer
    }

# 6. Funny response khi không liên quan DB
def funny_response(state: AgentState) -> AgentState:
    q = state["question"]
    return {**state, "final_answer": f"😂 Câu hỏi '{q}' không liên quan database rồi!"}