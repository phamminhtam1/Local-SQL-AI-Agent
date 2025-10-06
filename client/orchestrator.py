import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from db_agent.app import build_app as build_db_app
from search_agent.app import build_app as build_search_app

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class OrchestratorState:
    def __init__(self):
        self.question: str = ""
        self.relevance_check: Optional[str] = None
        self.db_agent_result: Optional[Dict[str, Any]] = None
        self.search_agent_result: Optional[Dict[str, Any]] = None
        self.verify_result: Optional[Dict[str, Any]] = None
        self.final_answer: Optional[str] = None
        self.chat_history: List[Dict[str, str]] = []
        self.retry_count: int = 0
        self.max_retries: int = 3
        self.iteration_info: List[Dict[str, Any]] = []  # history of loops
        

db_agent = build_db_app()
search_agent = build_search_app()

def _build_chat_context(chat_history: List[Dict]) -> str:
    if not chat_history:
        return ""
    context = "\nPrevious conversation:\n"
    for msg in chat_history[-4:]:
        role = msg.get("role")
        content = msg.get("content")
        context += f"{role}: {content}\n"
    return context

async def check_relevance(question: str, chat_history: List[Dict] = None) -> str:
    chat_context = _build_chat_context(chat_history or [])
    prompt = f"""
    You are a relevance classifier.
    User question: "{question}"
    {chat_context}

    Classify into one of: relevance, not_relevance.
    Rules:
    - "relevance_db": SQL, schema, data analysis
    - "relevance_search": web, info retrieval, news
    - "relevance_both": needs both
    - "not_relevance": unrelated
    Respond with ONE word only.
    """
    resp = llm.invoke(prompt).content.strip().lower()
    logger.info(f"Relevance: {resp}")
    return resp

async def run_db_agent(question: str) -> Dict[str, Any]:
    try:
        logger.info("Running DB agent...")
        result = await db_agent.ainvoke({"question": question, "max_iterations": 3})
        return result
    except Exception as e:
        logger.error(f"DB agent error: {e}")
        return {"error": str(e), "final_answer": f"Database agent failed: {e}"}

async def run_search_agent(question: str) -> str:
    try:
        logger.info("Running Search agent...")
        from search_agent.state import SearchAgentState
        
        initial_state: SearchAgentState = {
            "question": question,
            "final_answer": None,
        }
        result = await search_agent.ainvoke(initial_state)
        if result.get("final_answer"):
            return result['final_answer']
        else:
            return ""
    except Exception as e:
        logger.error(f"Search agent error: {e}")
        return f"Search agent failed: {e}"

async def verify_answer(
    question: str,
    db_result: Dict[str, Any],
    search_result: str,
    chat_history: List[Dict] = None,
    previous_iterations: List[Dict] = None,
) -> Dict[str, Any]:
    chat_context = _build_chat_context(chat_history or [])
    db_answer = db_result.get("final_answer", "")
    search_answer = search_result if isinstance(search_result, str) else search_result.get("final_answer", "")
    previous_summary = ""

    if previous_iterations:
        summaries = [
            f"Round {it['round']}: {it['verify_result'].get('reason', '')}"
            for it in previous_iterations[-2:]
        ]
        previous_summary = "\nPrevious verification summary:\n" + "\n".join(summaries)

    prompt = f"""
    You are an answer verifier. Evaluate if the answers adequately address the question.

    User Question: "{question}"
    {chat_context}
    {previous_summary}

    Database Answer: {db_answer}
    Search Answer: {search_answer}

    Respond with JSON:
    {{
        "is_adequate": true/false,
        "reason": "why adequate or not",
        "missing_info": "what info is missing if any",
        "suggestions": "improvement advice"
    }}
    """
    raw = llm.invoke(prompt).content.strip()
    try:
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        logger.warning("verify_answer JSON parse failed.")
        return {"is_adequate": False, "reason": raw, "missing_info": "", "suggestions": ""}

async def generate_final_answer(question, db_result, search_result, chat_history=None):
    chat_context = _build_chat_context(chat_history or [])
    db_answer = db_result.get("final_answer", "")
    search_answer = search_result if isinstance(search_result, str) else search_result.get("final_answer", "")
    prompt = f"""
    You are a final answer generator.
    Combine DB and Search results coherently to answer the question.

    Question: "{question}"
    {chat_context}

    DB Results: {db_answer}
    Search Results: {search_answer}

    Output a clear, concise, and informative final answer.
    """
    return llm.invoke(prompt).content.strip()

async def generate_funny_response(question: str, chat_history: List[Dict] = None) -> str:
    prompt = f"You are a witty assistant. Make a humorous answer to: '{question}'"
    return llm.invoke(prompt).content.strip()

async def plan_task_for_agents(question: str, chat_history: List[Dict] = None, iteration_info: List[Dict] = None) -> Dict[str, str]:
    chat_context = _build_chat_context(chat_history or [])
    
    iteration_context = ""
    if iteration_info:
        iteration_context = "\n## Previous Attempts and Results:\n"
        for i, iteration in enumerate(iteration_info[-3:], 1):
            round_num = iteration.get("round", i)
            db_result = iteration.get("db_result", {})
            search_result = iteration.get("search_result", {})
            verify_result = iteration.get("verify_result", {})
            
            iteration_context += f"\n### Round {round_num}:\n"
            
            if db_result and db_result.get("final_answer"):
                db_answer = db_result.get("final_answer", "")
                iteration_context += f"**Database Agent Result:** {db_answer}\n"
            elif db_result and db_result.get("error"):
                iteration_context += f"**Database Agent Error:** {db_result.get('error')}\n"
            
            if search_result:
                if isinstance(search_result, str):
                    iteration_context += f"**Search Agent Result:** {search_result}\n"
                elif search_result.get("final_answer"):
                    search_answer = search_result.get("final_answer", "")
                    iteration_context += f"**Search Agent Result:** {search_answer}\n"
                elif search_result.get("error"):
                    iteration_context += f"**Search Agent Error:** {search_result.get('error')}\n"
            
            if verify_result:
                is_adequate = verify_result.get("is_adequate", False)
                reason = verify_result.get("reason", "")
                missing_info = verify_result.get("missing_info", "")
                suggestions = verify_result.get("suggestions", "")
                
                iteration_context += f"**Verification Result:** {'ADEQUATE' if is_adequate else 'INADEQUATE'}\n"
                if reason:
                    iteration_context += f"**Reason:** {reason}\n"
                if missing_info:
                    iteration_context += f"**Missing Information:** {missing_info}\n"
                if suggestions:
                    iteration_context += f"**Improvement Suggestions:** {suggestions}\n"
            
            iteration_context += "\n"
    
    is_retry = bool(iteration_info and len(iteration_info) > 0)
    retry_guidance = ""
    if is_retry:
        retry_guidance = """
    ## RETRY ATTEMPT - CRITICAL INSTRUCTIONS:
    - This is a retry attempt. Previous attempts failed verification.
    - CAREFULLY analyze the verification feedback and missing information.
    - Modify your approach based on what went wrong before.
    - If previous DB results were inadequate, refine the database question.
    - If previous Search results were inadequate, refine the search question.
    - Consider combining both agents if only one was used before.
    - Address the specific missing information and suggestions provided.
    """
    else:
        retry_guidance = "## FIRST ATTEMPT - Plan the initial strategy for this question."

    prompt = f"""
    You are an intelligent task planner for a multi-agent system. Your role is to analyze user questions and determine which specialized agents should handle them.

    ## Available Agents:
    1. **Database Agent**: Handles SQL queries, database schema analysis, data extraction, and database-related questions
    2. **Search Agent**: Handles web research, current information retrieval, news, and general knowledge questions

    ## Current Question: "{question}"
    
    ## Conversation Context:
    {chat_context if chat_context.strip() else "No previous conversation context."}
    
    {iteration_context if iteration_context.strip() else "No previous attempts."}
    
    {retry_guidance}

    ## Planning Guidelines:
    - **Database Agent**:
        handles concrete SQL queries, schema inspection, data extraction, or performance *analysis based on actual DB data*.
    - **Search Agent**:
        handles conceptual questions (e.g., "how to improve performance", "what is normalization", "best practices", etc.),
        and general knowledge not requiring actual database access.
    - **Both agents** may be needed for complex questions requiring both database data and external context
    
    ## Context-Aware Planning:
    - Use conversation history to understand the user's intent and context
    - If this is a retry, learn from previous failures and improve the approach
    - Consider what information is missing and how to address it
    - Build upon previous attempts rather than repeating them
    - Use verification feedback to refine your strategy

    ## Output Format:
    Respond with JSON containing:
    - "database_question": Specific question for Database Agent (empty string if not needed)
    - "search_question": Specific question for Search Agent (empty string if not needed)

    ## Examples:
    - "Show me sales data for last month" → database_question: "Show me sales data for last month"
    - "What's the latest news about AI?" → search_question: "What's the latest news about AI?"
    - "Compare our Q3 sales with industry trends" → both agents needed

    Respond in JSON:
    {{
      "database_question": "<specific question for DB agent or empty string>",
      "search_question": "<specific question for Search agent or empty string>"
    }}
    """
    logger.info(f"Prompt for Plan Task: {prompt}")
    raw = llm.invoke(prompt).content.strip()
    try:
        raw = raw.replace("```json", "").replace("```", "").strip()

        logger.info(f"Plan Task: {raw}")
        return json.loads(raw)
    except Exception:
        logger.warning("Failed to parse plan_task JSON.")
        return {"database_question": question, "search_question": ""}

async def orchestrate(question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
    state = OrchestratorState()
    state.question = question
    state.chat_history = chat_history or []

    logger.info(f" Orchestrating: {question}")
    relevance = await check_relevance(question, state.chat_history)

    if relevance == "not_relevance":
        funny = await generate_funny_response(question, state.chat_history)
        return {"final_answer": funny, "relevance": relevance}

    plan = await plan_task_for_agents(question, state.chat_history, state.iteration_info)
    db_q, search_q = plan.get("database_question", ""), plan.get("search_question", "")
    logger.info(f"DB Question: {db_q}, Search Question: {search_q}")

    if relevance in ["relevance_db" or "relevance_both"] and db_q:
        state.db_agent_result = await run_db_agent(db_q)
    if relevance in ["relevance_search" or "relevance_both"] and search_q:
        state.search_agent_result = await run_search_agent(search_q)

    while state.retry_count < state.max_retries:
        state.verify_result = await verify_answer(
            state.question,
            state.db_agent_result or {},
            state.search_agent_result or {},
            state.chat_history,
            state.iteration_info,
        )
        logger.info(f"Verify Result: {state.verify_result}")

        state.iteration_info.append({
            "round": state.retry_count + 1,
            "db_result": state.db_agent_result,
            "search_result": state.search_agent_result,
            "verify_result": state.verify_result,
        })

        if state.verify_result.get("is_adequate", False):
            break

        state.retry_count += 1
        logger.info(f"Re-planning (attempt {state.retry_count}/{state.max_retries})")

        suggestions = state.verify_result.get("suggestions", "")
        missing = state.verify_result.get("missing_info", "")
        enhanced_q = f"{question}\n\nConsider these improvements:\n{suggestions}\nMissing info: {missing}"

        plan = await plan_task_for_agents(enhanced_q, state.chat_history, state.iteration_info)
        db_q, search_q = plan.get("database_question", ""), plan.get("search_question", "")

        if relevance in ["relevance_db", "relevance_both"] and db_q:
            state.db_agent_result = await run_db_agent(db_q)
            logger.info(f"DB Agent Result: {state.db_agent_result}")
        if relevance in ["relevance_search", "relevance_both"] and search_q:
            state.search_agent_result = await run_search_agent(search_q)
            logger.info(f"Search Agent Result: {state.search_agent_result}")

    state.final_answer = await generate_final_answer(
        question, state.db_agent_result or {}, state.search_agent_result or {}, state.chat_history
    )
    logger.info(f"Final Answer Output: {state.final_answer}")

    return {
        "final_answer": state.final_answer,
        "relevance": relevance,
        "verify_result": state.verify_result,
        "iteration_info": state.iteration_info,
        "retry_count": state.retry_count,
        "db_result": state.db_agent_result,
        "search_result": state.search_agent_result,
    }
