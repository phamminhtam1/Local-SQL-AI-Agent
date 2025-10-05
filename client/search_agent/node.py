import json
import re
import asyncio
from langchain_openai import ChatOpenAI
from search_agent.state import SearchAgentState
from .mcp_client import MCPClient
import logging
logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Initialize MCP client
mcp_client = MCPClient()

def extract_text_from_result(result) -> str:
    """Extract readable text from MCP CallToolResult or similar response."""
    if hasattr(result, "data") and isinstance(result.data, str) and result.data.strip():
        return result.data.strip()
    if hasattr(result, "content") and isinstance(result.content, list):
        texts = []
        for item in result.content:
            if hasattr(item, "text") and item.text:
                texts.append(item.text)
        if texts:
            return "\n".join(texts).strip()
    if hasattr(result, "structured_content"):
        sc = result.structured_content
        if isinstance(sc, dict):
            for k in ("result", "content", "data"):
                if k in sc and isinstance(sc[k], str):
                    return sc[k].strip()
            return json.dumps(sc, ensure_ascii=False)
    if isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)
    return str(result).strip()

# 1. Planner LLM - Đánh giá câu hỏi và chọn tool
async def planner_llm(state: SearchAgentState) -> SearchAgentState:
    
    q = state["question"]
    iteration_count = state.get("iteration_count", 0)
    execution_history = state.get("execution_history", [])
    chat_history = state.get("chat_history", [])
    
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
    
    chat_context = ""
    if chat_history:
        chat_context = "\nPrevious conversation:\n"
        for msg in chat_history[-6:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_context += f"User: {content}\n"
            elif role == "assistant":
                chat_context += f"Assistant: {content}\n"
    
    history_context = ""
    if execution_history:
        history_context = "\nPrevious tool executions:\n"
        for i, exec_info in enumerate(execution_history, start=1):
            tool_name = exec_info.get("tool", "")
            result_obj = exec_info.get("result", "")
            result_text = extract_text_from_result(result_obj)
            history_context += f"Step {i}: {tool_name}\n{result_text}\n\n"

    planner_prompt = f"""
    You are a Search Planner LLM. Based on the user's question, choose the most appropriate search tool.
    
    Available tools:
    {json.dumps(enhanced_tool_metadata, indent=2, ensure_ascii=False)}
    
    Current user question: "{q}"
    Current iteration: {iteration_count + 1}
    {chat_context}
    {history_context}
    
    IMPORTANT RULES:
    1. Choose web_search for general web search queries
    2. Choose news_search for current news and events
    3. Consider the user's intent and the type of information they need
    
    Consider:
    1. What type of information is the user looking for?
    2. Is it a general web search or news search?
    3. What tools have been executed before and what did they return?
    4. Is additional search needed?
    
    Respond with ONLY the tool name from the available tools above.
    """
    
    selected_tool = llm.invoke(planner_prompt).content.strip().lower()
    logger.info(f"Search Planner LLM selected tool: {selected_tool}")
    
    valid_tools = list(enhanced_tool_metadata.keys())
    if selected_tool not in valid_tools:
        logger.warning(f"Invalid tool selection: {selected_tool}, defaulting to web_search")
        selected_tool = "web_search"

    return {
        **state, 
        "selected_tool": selected_tool,
        "tool_metadata": enhanced_tool_metadata.get(selected_tool, {})
    }

# 2. Executor - Thực thi tool được chọn
async def executor(state: SearchAgentState) -> SearchAgentState:
    
    selected_tool = state["selected_tool"]
    question = state["question"]
    execution_history = state.get("execution_history", [])
    tool_results = state.get("tool_results", [])
    chat_history = state.get("chat_history", [])
    
    logger.info(f"Executing search tool: {selected_tool}")
    
    try:
        if not mcp_client.connected:
            await mcp_client.connect()
        
        if selected_tool == "web_search":
            result = await mcp_client.call_tool("web_search", {"query": question})
        elif selected_tool == "news_search":
            result = await mcp_client.call_tool("news_search", {"query": question})
        else:
            result = await mcp_client.call_tool(selected_tool, {"query": question})
            
        clean_result = extract_text_from_result(result)
        new_execution_history = execution_history + [{
            "tool": selected_tool,
            "result": clean_result,
            "iteration": state.get("iteration_count", 0) + 1
        }]
        
        new_tool_results = tool_results + [result]
        logger.info(f"Search tool execution successful: {selected_tool}")
        logger.info(f"Search tool execution result: {clean_result}")
        
        return {
            **state,
            "tool_results": new_tool_results,
            "execution_history": new_execution_history
        }
        
    except Exception as e:
        error_msg = f"Search tool execution failed: {str(e)}"
        logger.error(f"Search tool execution error: {error_msg}")
        
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
def evaluator_llm(state: SearchAgentState) -> SearchAgentState:
    
    question = state["question"]
    tool_results = state.get("tool_results", [])
    execution_history = state.get("execution_history", [])
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    chat_history = state.get("chat_history", [])
    
    all_results = "\n".join([str(result) for result in tool_results])
    
    # Count search executions
    search_count = 0
    for exec_info in execution_history:
        if exec_info.get("tool") in ["web_search", "news_search"] and not exec_info.get("error", False):
            search_count += 1
    
    chat_context = ""
    if chat_history:
        chat_context = "\nPrevious conversation:\n"
        for msg in chat_history[-4:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_context += f"User: {content}\n"
            elif role == "assistant":
                chat_context += f"Assistant: {content}\n"
    
    evaluator_prompt = f"""
        You are a Search Evaluator LLM. Assess whether the current search results adequately answer the user's question.

        User Question: "{question}"
        Current Results: {all_results}
        Iteration: {iteration_count + 1}/{max_iterations}
        Search executions: {search_count}
        {chat_context}
        
        EVALUATION CRITERIA:
        - Does the current search data answer the user's question?
        - Are the search results comprehensive and relevant?
        - Would additional searches provide genuinely new information?
        - Are we getting repetitive results?
        
        Respond with ONLY one word:
        - "complete" (if the question is answered or results are comprehensive)
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
    
    if search_count >= 2:
        logger.warning(f"Too many search executions ({search_count}), forcing complete")
        is_complete = True
    
    logger.info(f"Search Evaluator LLM result: {evaluation_result}")
    logger.info(f"Assessment: {'Complete' if is_complete else 'Incomplete'}")
    
    return {
        **state,
        "is_complete": is_complete,
        "evaluation_reason": evaluation_result,
        "iteration_count": iteration_count + 1
    }

# 4. Final Answer Generator - Kết hợp reasoning và kết quả cuối
def final_answer_generator(state: SearchAgentState) -> SearchAgentState:
    question = state["question"]
    tool_results = state.get("tool_results", [])
    execution_history = state.get("execution_history", [])
    chat_history = state.get("chat_history", [])
    
    all_results = "\n".join([str(result) for result in tool_results])
    
    chat_context = ""
    if chat_history:
        chat_context = "\nPrevious conversation:\n"
        for msg in chat_history[-4:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_context += f"User: {content}\n"
            elif role == "assistant":
                chat_context += f"Assistant: {content}\n"
    
    final_prompt = f"""
    You are a Search Final Answer Generator. Create a comprehensive, natural language answer based on search results.
    
    Current User Question: "{question}"
    Search Results: {all_results}
    {chat_context}
    
    Execution History:
    {json.dumps(execution_history, indent=2)}
    
    Requirements:
    1. Provide a clear, direct answer to the user's question
    2. Use natural language reasoning to explain the search results
    3. Include relevant information from the search results
    4. Make the answer informative and easy to understand
    5. If there are multiple results, synthesize them coherently
    6. Consider the conversation context - if this is a follow-up question, reference previous results appropriately
    
    Generate a comprehensive final answer that combines natural language reasoning with the search results.
    """
    
    final_answer = llm.invoke(final_prompt).content
    logger.info(f"Generated search final answer: {final_answer}")
    
    new_chat_history = chat_history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": final_answer}
    ]
    
    return {
        **state,
        "final_answer": final_answer,
        "chat_history": new_chat_history
    }

# 5. Funny response (không cần thiết nữa vì orchestrator xử lý)
def funny_response(state: SearchAgentState) -> SearchAgentState:
    q = state["question"]
    chat_history = state.get("chat_history", [])
    
    chat_context = ""
    if chat_history:
        chat_context = "\nPrevious conversation:\n"
        for msg in chat_history[-4:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                chat_context += f"User: {content}\n"
            elif role == "assistant":
                chat_context += f"Assistant: {content}\n"
    
    final_prompt = f"""
    You are a Funny Response Generator. Create a funny response to the user's question.
    
    User Question: "{q}"
    {chat_context}
    
    Generate a funny response to the user's question.
    """
    final_answer = llm.invoke(final_prompt).content
    logger.info(f"Generated funny response: {final_answer}")
    
    new_chat_history = chat_history + [
        {"role": "user", "content": q},
        {"role": "assistant", "content": final_answer}
    ]
    
    return {
        **state, 
        "final_answer": final_answer,
        "chat_history": new_chat_history
    }