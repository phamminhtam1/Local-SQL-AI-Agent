import json
import os
import re
import asyncio
from langchain_core.messages import SystemMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch, TavilyExtract
from search_agent.state import SearchAgentState
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

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

# 1. Planner LLM - Đánh giá câu hỏi và chọn tool
async def planner_llm(state: SearchAgentState) -> SearchAgentState:
    
    q = state["question"] 
    iteration_count = state.get("iteration_count", 0)
    execution_history = state.get("execution_history", [])
    
    # Available tools for search agent
    available_tools = {
        "search_web": {
            "name": "search_web",
            "description": "Search the web for current information. Use this to find recent news, facts, or general information.",
            "inputs": ["query", "num_results"],
            "outputs": ["formatted_results"]
        },
        "extract_content_from_webpage": {
            "name": "extract_content_from_webpage", 
            "description": "Extract full content from a specific webpage URL. Use this when you need detailed information from a specific page.",
            "inputs": ["url"],
            "outputs": ["extracted_content"]
        }
    }
    
    has_search_results = False
    for exec_info in execution_history:
        if exec_info.get("tool") == "search_web" and not exec_info.get("error", False):
            has_search_results = True
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
    You are a Planner LLM for a search agent. Based on the user's question and execution history, choose the most appropriate tool.
    
    Available tools:
    {json.dumps(available_tools, indent=2, ensure_ascii=False)}
    
    User question: "{q}"
    Current iteration: {iteration_count + 1}
    Search results already available: {has_search_results}
    {history_context}
    
    IMPORTANT RULES:
    1. If search_web has already been executed and results are available, consider using extract_content_from_webpage for specific URLs
    2. If no search has been done yet, start with search_web
    3. Use extract_content_from_webpage when you have specific URLs that need detailed content
    4. Prefer search_web for general information gathering
    5. Use extract_content_from_webpage when you need full content from specific pages
    
    Consider:
    1. What information is needed to answer the user's question?
    2. What tools have been executed before and what did they return?
    3. Do we need to search for more information or extract content from specific URLs?
    
    Respond with ONLY the tool name from the available tools above.
    """
    
    selected_tool = llm.invoke(planner_prompt).content.strip().lower()
    logger.info(f"Planner LLM selected tool: {selected_tool}")
    
    valid_tools = list(available_tools.keys())
    if selected_tool not in valid_tools:
        logger.warning(f"Invalid tool selection: {selected_tool}, defaulting to search_web")
        selected_tool = "search_web"

    return {
        **state, 
        "selected_tool": selected_tool,
        "tool_metadata": available_tools.get(selected_tool, {})
    }

# 2. Executor - Thực thi tool được chọn
async def executor(state: SearchAgentState) -> SearchAgentState:
    
    selected_tool = state["selected_tool"]
    question = state["question"]
    execution_history = state.get("execution_history", [])
    tool_results = state.get("tool_results", [])    
    logger.info(f"Executing tool: {selected_tool}")
    
    try:
        if selected_tool == "search_web":
            # Create search query based on the question
            search_prompt = f"""
            Create a search query for the following question: "{question}"
            
            Return ONLY the search query, no explanations or additional text.
            """
            search_query = llm.invoke(search_prompt).content.strip()
            
            web_search = TavilySearch(max_results=3, topic="general")
            search_results = web_search.invoke({"query": search_query})
            
            formatted_result = {
                "query": search_query,
                "result": []
            }
            for result in search_results["results"]:
                formatted_result["result"].append({
                    "title": result["title"],
                    "url": result["url"],
                    "content": result["content"]
                })
            
            result = formatted_result
            
        elif selected_tool == "extract_content_from_webpage":
            # Find URLs from previous search results
            urls_to_extract = []
            for exec_info in execution_history:
                if exec_info.get("tool") == "search_web" and not exec_info.get("error", False):
                    search_result = exec_info.get("result", {})
                    if isinstance(search_result, dict) and "result" in search_result:
                        for item in search_result["result"]:
                            if "url" in item:
                                urls_to_extract.append(item["url"])
                    break
            
            if not urls_to_extract:
                # If no URLs from search, try to extract from question
                url_prompt = f"""
                Extract any URLs from this question: "{question}"
                Return ONLY the URLs, one per line, or "none" if no URLs found.
                """
                urls_text = llm.invoke(url_prompt).content.strip()
                if urls_text.lower() != "none":
                    urls_to_extract = [url.strip() for url in urls_text.split('\n') if url.strip()]
            
            if urls_to_extract:
                extractor = TavilyExtract()
                results = extractor.invoke(input={"urls": urls_to_extract[:2]})["results"]  # Limit to 2 URLs
                result = format_extracted_content(results)
            else:
                result = {"error": "No URLs found to extract content from"}
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
def evaluator_llm(state: SearchAgentState) -> SearchAgentState:
    
    question = state["question"]
    tool_results = state.get("tool_results", [])
    execution_history = state.get("execution_history", [])
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)    
    all_results = "\n".join([str(result) for result in tool_results])
    
    has_search_results = False
    has_extracted_content = False
    for exec_info in execution_history:
        if exec_info.get("tool") == "search_web" and not exec_info.get("error", False):
            has_search_results = True
        if exec_info.get("tool") == "extract_content_from_webpage" and not exec_info.get("error", False):
            has_extracted_content = True
    
    # Kiểm tra xem có search lặp lại không
    search_count = 0
    for exec_info in execution_history:
        if exec_info.get("tool") == "search_web" and not exec_info.get("error", False):
            search_count += 1
    
    has_repetitive_searches = search_count >= 2
        
    evaluator_prompt = f"""
        You are an Evaluator LLM. Assess whether the current results adequately answer the user's question.

        User Question: "{question}"
        Current Results: {all_results}
        Iteration: {iteration_count + 1}/{max_iterations}
        
        IMPORTANT: Analysis
        - Has search_web been executed: {has_search_results}
        - Has content extraction been executed: {has_extracted_content}
        - Search executed count: {search_count}
        - Has repetitive searches: {has_repetitive_searches}
        
        CRITICAL RULES:
        1. If search_web has been executed and provided good results, consider it complete
        2. If extract_content_from_webpage has been executed, likely complete
        3. If search_count >= 2, likely complete
        4. Only mark as incomplete if genuinely new information is needed
        
        EVALUATION CRITERIA:
        - Does the current data answer the user's question?
        - Are we getting repetitive results?
        - Would additional searches provide genuinely new information?
        
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
    
    if has_repetitive_searches:
        logger.warning(f"Repetitive searches detected, forcing complete")
        is_complete = True
    
    if search_count >= 2:
        logger.warning(f"Too many search executions ({search_count}), forcing complete")
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
def final_answer_generator(state: SearchAgentState) -> SearchAgentState:
    question = state["question"]
    tool_results = state.get("tool_results", [])
    execution_history = state.get("execution_history", [])    
    all_results = "\n".join([str(result) for result in tool_results])
    final_prompt = f"""
    You are a Final Answer Generator. Create a comprehensive, natural language answer based on search results.
    
    Current User Question: "{question}"
    Search Results: {all_results}
    
    Execution History:
    {json.dumps(execution_history, indent=2)}
    
    Requirements:
    1. Provide a clear, direct answer to the user's question
    2. Use natural language reasoning to explain the results
    3. Include relevant information from the search results
    4. Make the answer informative and easy to understand
    5. If there are multiple results, synthesize them coherently
    6. Cite sources when appropriate
    7. If information is not available, say so clearly
    
    Generate a comprehensive final answer that combines natural language reasoning with the search results.
    """
    
    final_answer = llm.invoke(final_prompt).content
    logger.info(f"Generated final answer: {final_answer}")
    
    return {
        **state,
        "final_answer": final_answer
    }

def format_extracted_content(results: list):
    """Format TavilyExtract raw results into clean, readable Markdown structure."""
    formatted = []

    for item in results:
        url = item.get("url", "")
        raw_content = item.get("raw_content", "")
        title = extract_title_from_content(raw_content) or "Untitled"

        cleaned = re.sub(r"\s+", " ", raw_content)
        cleaned = re.sub(r"#\s*", "", cleaned)
        cleaned = re.sub(r"\*\*+", "", cleaned)
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

        snippet = cleaned[:8000] + ("..." if len(cleaned) > 8000 else "")

        summary = summarize_heuristic(cleaned)

        formatted.append({
                    "url": url,
                    "markdown": f"""
        ### {title}
        **URL:** {url}

        **Summary:** {summary}

        **Excerpt:**  
        {snippet}
        """
        })

    return formatted

def extract_title_from_content(text: str) -> str:
    match = re.search(r"^#\s*(.+)", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"(?m)^##\s*(.+)", text)
    return match.group(1).strip() if match else None

def summarize_heuristic(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    first_sentences = sentences[:3]
    return " ".join(first_sentences).strip()

    """
    Shorten text to specified maximum length while preserving sentence boundaries.
    
    Args:
        text: The text to shorten
        max_length: Maximum length of the shortened text (default: 2000)
    
    Returns:
        Shortened text with ellipsis if truncated
    """
    if len(text) <= max_length:
        return text
    
    # Try to break at sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text)
    shortened = ""
    
    for sentence in sentences:
        if len(shortened + sentence) <= max_length - 3:  # Reserve space for "..."
            shortened += sentence + " "
        else:
            break
    
    # If no sentences fit, truncate at word boundaries
    if not shortened:
        words = text.split()
        for word in words:
            if len(shortened + word) <= max_length - 3:
                shortened += word + " "
            else:
                break
    
    shortened = shortened.strip()
    if len(shortened) < len(text):
        shortened += "..."
    
    return shortened