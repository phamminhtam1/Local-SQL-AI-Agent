from .state import AgentState
from langgraph.graph import END

def relevance_router(state: AgentState):
    return "select_tools" if state["relevancy"] == "relevant" else "funny_response"

def execute_tools_router(state: AgentState):
    if state.get("tool_results"):
        return "generate_answer"
    return END

def validation_router(state: AgentState):
    """Router để điều hướng sau khi validate response"""
    validation_passed = state.get("validation_passed")
    
    if validation_passed is True:
        return END  # Response hợp lệ, kết thúc
    elif validation_passed is False:
        return "regenerate_sql"  # Response không hợp lệ, sinh SQL lại
    else:
        return END  # Fallback, kết thúc

def regenerate_router(state: AgentState):
    """Router để điều hướng sau khi regenerate SQL"""
    sql_attempts = state.get("sql_attempts", 0)
    max_attempts = 3
    
    if sql_attempts >= max_attempts:
        return END  # Đã thử quá nhiều lần, kết thúc
    else:
        return "validate_response"  # Validate lại response mới