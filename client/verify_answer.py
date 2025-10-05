import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

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
    6. Are the answers accurate and well-structured?
    7. Do the answers address all parts of the user's question?
    
    Respond with JSON format:
    {{
        "is_adequate": true/false,
        "reason": "explanation of why adequate or not",
        "missing_info": "what information is missing if not adequate",
        "suggestions": "suggestions for improvement if not adequate",
        "quality_score": 1-10,
        "completeness_score": 1-10,
        "accuracy_score": 1-10
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
        # Fallback if JSON parsing fails
        logger.warning("Failed to parse verify_answer JSON, using fallback")
        return {
            "is_adequate": "adequate" in response.lower() or "yes" in response.lower(),
            "reason": response,
            "missing_info": "",
            "suggestions": "",
            "quality_score": 5,
            "completeness_score": 5,
            "accuracy_score": 5
        }

async def generate_retry_instructions(verify_result: Dict[str, Any], question: str) -> str:
    """Generate specific retry instructions based on verification feedback"""
    missing_info = verify_result.get("missing_info", "")
    suggestions = verify_result.get("suggestions", "")
    reason = verify_result.get("reason", "")
    
    retry_prompt = f"""
    Based on the verification feedback, generate specific retry instructions for the agents.
    
    Original Question: "{question}"
    Verification Reason: {reason}
    Missing Information: {missing_info}
    Suggestions: {suggestions}
    
    Generate specific, actionable instructions for the agents to improve their results.
    Focus on:
    1. What specific information is missing
    2. How to search for that information
    3. What additional queries or searches to perform
    4. Any specific requirements or constraints
    
    Return clear, actionable instructions.
    """
    
    retry_instructions = llm.invoke(retry_prompt).content
    logger.info(f"Generated retry instructions: {retry_instructions}")
    return retry_instructions

async def analyze_agent_results(db_result: Dict[str, Any], search_result: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the quality and completeness of agent results"""
    db_answer = db_result.get("final_answer", "")
    search_answer = search_result.get("final_answer", "")
    
    db_execution_history = db_result.get("execution_history", [])
    search_execution_history = search_result.get("execution_history", [])
    
    analysis_prompt = f"""
    Analyze the results from both agents to understand their strengths and weaknesses.
    
    Database Agent:
    - Answer: {db_answer}
    - Execution History: {json.dumps(db_execution_history, indent=2)}
    
    Search Agent:
    - Answer: {search_answer}
    - Execution History: {json.dumps(search_execution_history, indent=2)}
    
    Provide analysis in JSON format:
    {{
        "db_agent_analysis": {{
            "strengths": ["list of strengths"],
            "weaknesses": ["list of weaknesses"],
            "completeness": 1-10,
            "accuracy": 1-10
        }},
        "search_agent_analysis": {{
            "strengths": ["list of strengths"],
            "weaknesses": ["list of weaknesses"],
            "completeness": 1-10,
            "accuracy": 1-10
        }},
        "combined_analysis": {{
            "synergy": 1-10,
            "gaps": ["list of information gaps"],
            "recommendations": ["list of recommendations"]
        }}
    }}
    """
    
    response = llm.invoke(analysis_prompt).content.strip()
    
    try:
        if response.startswith("```json"):
            response = response.replace("```json", "").replace("```", "").strip()
        elif response.startswith("```"):
            response = response.replace("```", "").strip()
        
        result = json.loads(response)
        return result
    except json.JSONDecodeError:
        logger.warning("Failed to parse analysis JSON, using fallback")
        return {
            "db_agent_analysis": {
                "strengths": ["Database queries executed"],
                "weaknesses": ["Unknown"],
                "completeness": 5,
                "accuracy": 5
            },
            "search_agent_analysis": {
                "strengths": ["Search queries executed"],
                "weaknesses": ["Unknown"],
                "completeness": 5,
                "accuracy": 5
            },
            "combined_analysis": {
                "synergy": 5,
                "gaps": ["Unknown"],
                "recommendations": ["Improve both agents"]
            }
        }


