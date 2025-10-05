from search_agent.state import SearchAgentState
from langgraph.graph import END
import logging

logger = logging.getLogger(__name__)

def evaluator_router(state: SearchAgentState):
    is_complete = state.get("is_complete")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if is_complete or iteration_count >= max_iterations:
        return "final_answer_generator"
    else:
        return "planner_llm"