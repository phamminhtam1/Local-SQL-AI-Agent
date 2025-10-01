from .state import AgentState
from langgraph.graph import END

def relevance_router(state: AgentState):
    """Router sau khi kiểm tra relevance"""
    relevancy = state.get("relevancy")
    print(f"DEBUG: relevance_router - relevancy: {relevancy}")
    print(f"DEBUG: relevance_router - state keys: {list(state.keys())}")
    
    if relevancy == "relevant":
        print("DEBUG: Routing to planner_llm")
        return "planner_llm"
    else:
        print("DEBUG: Routing to funny_response")
        return "funny_response"

def evaluator_router(state: AgentState):
    """Router sau khi Evaluator LLM đánh giá kết quả"""
    is_complete = state.get("is_complete")
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 5)
    
    # Nếu đã đủ hoặc đã hết số lần lặp
    if is_complete or iteration_count >= max_iterations:
        return "final_answer_generator"
    else:
        # Nếu chưa đủ, quay lại Planner LLM để chọn tool tiếp theo
        return "planner_llm"