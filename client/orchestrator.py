import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from db_agent.app import build_app as build_db_app
from search_agent.app import build_app as build_search_app

logger = logging.getLogger(__name__)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

class OrchestratorState:
    def __init__(self):
        self.question = ""
        self.relevance_check = None
        self.db_agent_result = None
        self.search_agent_result = None
        self.verify_result = None
        self.final_answer = None
        self.retry_count = 0
        self.max_retries = 3
        self.chat_history = []
        self.iteration_info = {}  # Thông tin về lý do retry và kết quả agents

# Initialize agents
db_agent = build_db_app()
search_agent = build_search_app()

async def check_relevance(question: str, chat_history: List[Dict] = None) -> str:
    """Check if question is relevant to database or search functionality"""
    if chat_history is None:
        chat_history = []
    
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
    
    prompt = f"""
    You are a relevance classifier. User question: "{question}"
    {chat_context}
    
    Classify the question into one of these categories:
    1. "database" - Questions about SQL, database queries, tables, schema, data analysis
    2. "search" - Questions about web search, information retrieval, current events, news
    3. "both" - Questions that might need both database and search capabilities
    4. "neither" - Questions unrelated to database or search functionality
    
    Examples:
    - "Show me all users" → database
    - "Search for latest AI news" → search  
    - "Find users and search for their company info" → both
    - "What's the weather?" → neither
    
    Respond with ONLY one word: database, search, both, or neither.
    """
    
    response = llm.invoke(prompt).content.strip().lower()
    logger.info(f"Relevance check result: {response}")
    return response

async def run_db_agent(question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
    """Run database agent"""
    try:
        logger.info("Running DB agent...")
        result = await db_agent.ainvoke({
            "question": question,
            "chat_history": chat_history or [],
            "max_iterations": 3
        })
        logger.info("DB agent completed")
        return result
    except Exception as e:
        logger.error(f"DB agent error: {e}")
        return {"error": str(e), "final_answer": f"Database agent failed: {str(e)}"}

async def run_search_agent(question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
    """Run search agent"""
    try:
        logger.info("Running Search agent...")
        result = await search_agent.ainvoke({
            "question": question,
            "chat_history": chat_history or [],
            "max_iterations": 3
        })
        logger.info("Search agent completed")
        return result
    except Exception as e:
        logger.error(f"Search agent error: {e}")
        return {"error": str(e), "final_answer": f"Search agent failed: {str(e)}"}

async def verify_answer(question: str, db_result: Dict[str, Any], search_result: Dict[str, Any], chat_history: List[Dict] = None) -> Dict[str, Any]:
    """Verify if the combined results adequately answer the question"""
    if chat_history is None:
        chat_history = []
    
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
    
    db_answer = db_result.get("final_answer", "")
    search_answer = search_result.get("final_answer", "")
    
    prompt = f"""
    You are an answer verifier. Evaluate if the provided answers adequately address the user's question.
    
    User Question: "{question}"
    {chat_context}
    
    Database Agent Answer: {db_answer}
    Search Agent Answer: {search_answer}
    
    Evaluation Criteria:
    1. Does the database answer provide relevant data/information?
    2. Does the search answer provide relevant information?
    3. Are the answers comprehensive and complete?
    4. Do the answers work well together?
    5. Is any critical information missing?
    
    Respond with JSON format:
    {{
        "is_adequate": true/false,
        "reason": "explanation of why adequate or not",
        "missing_info": "what information is missing if not adequate",
        "suggestions": "suggestions for improvement if not adequate"
    }}
    """
    
    response = llm.invoke(prompt).content.strip()
    
    try:
        # Try to parse JSON response
        if response.startswith("```json"):
            response = response.replace("```json", "").replace("```", "").strip()
        elif response.startswith("```"):
            response = response.replace("```", "").strip()
        
        result = json.loads(response)
        return result
    except json.JSONDecodeError:
        logger.warning("Failed to parse verify_answer JSON, using fallback")
        return {
            "is_adequate": "adequate" in response.lower() or "yes" in response.lower(),
            "reason": response,
            "missing_info": "",
            "suggestions": ""
        }

async def generate_final_answer(question: str, db_result: Dict[str, Any], search_result: Dict[str, Any], chat_history: List[Dict] = None) -> str:
    """Generate final answer combining results from both agents"""
    if chat_history is None:
        chat_history = []
    
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
    
    db_answer = db_result.get("final_answer", "")
    search_answer = search_result.get("final_answer", "")
    
    prompt = f"""
    You are a final answer generator. Create a comprehensive answer that combines information from both database and search results.
    
    User Question: "{question}"
    {chat_context}
    
    Database Results: {db_answer}
    Search Results: {search_answer}
    
    Requirements:
    1. Provide a clear, direct answer to the user's question
    2. Combine relevant information from both sources
    3. Use natural language reasoning
    4. Make the answer informative and easy to understand
    5. If one source is more relevant, prioritize that information
    6. Synthesize the information coherently
    
    Generate a comprehensive final answer.
    """
    
    final_answer = llm.invoke(prompt).content
    logger.info("Generated final answer")
    return final_answer

async def generate_funny_response(question: str, chat_history: List[Dict] = None) -> str:
    """Generate funny response for irrelevant questions"""
    if chat_history is None:
        chat_history = []
    
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
    
    prompt = f"""
    You are a funny response generator. Create a humorous response to the user's question.
    
    User Question: "{question}"
    {chat_context}
    
    Generate a funny response to the user's question.
    """
    
    funny_answer = llm.invoke(prompt).content
    logger.info("Generated funny response")
    return funny_answer

async def orchestrate(question: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
    """Main orchestration function"""
    if chat_history is None:
        chat_history = []
    
    logger.info(f"Orchestrating question: {question}")
    relevance = await check_relevance(question, chat_history)
    
    if relevance == "neither":
        funny_answer = await generate_funny_response(question, chat_history)
        new_chat_history = chat_history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": funny_answer}
        ]
        return {
            "final_answer": funny_answer,
            "chat_history": new_chat_history,
            "relevance": relevance
        }
    
    db_result = None
    search_result = None
    if relevance in ["database", "both"]:
        db_result = await run_db_agent(question, chat_history)
    
    if relevance in ["search", "both"]:
        search_result = await run_search_agent(question, chat_history)
    
    verify_result = await verify_answer(question, db_result or {}, search_result or {}, chat_history)
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        if verify_result.get("is_adequate", False):
            final_answer = await generate_final_answer(question, db_result or {}, search_result or {}, chat_history)
            new_chat_history = chat_history + [
                {"role": "user", "content": question},
                {"role": "assistant", "content": final_answer}
            ]
            return {
                "final_answer": final_answer,
                "chat_history": new_chat_history,
                "relevance": relevance,
                "db_result": db_result,
                "search_result": search_result,
                "verify_result": verify_result
            }
        else:
            retry_count += 1
            logger.info(f"Answer not adequate, retrying... (attempt {retry_count}/{max_retries})")
            retry_instructions = verify_result.get("suggestions", "")
            missing_info = verify_result.get("missing_info", "")
            
            retry_question = f"{question}\n\nAdditional requirements: {retry_instructions}\nMissing information needed: {missing_info}"
            if relevance in ["database", "both"]:
                db_result = await run_db_agent(retry_question, chat_history)
            
            if relevance in ["search", "both"]:
                search_result = await run_search_agent(retry_question, chat_history)
            
            verify_result = await verify_answer(question, db_result or {}, search_result or {}, chat_history)
    
    logger.warning("Max retries reached, generating final answer with available results")
    final_answer = await generate_final_answer(question, db_result or {}, search_result or {}, chat_history)
    new_chat_history = chat_history + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": final_answer}
    ]
    return {
        "final_answer": final_answer,
        "chat_history": new_chat_history,
        "relevance": relevance,
        "db_result": db_result,
        "search_result": search_result,
        "verify_result": verify_result,
        "retry_count": retry_count
    }

