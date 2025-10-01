from .state import AgentState
from langgraph.graph import END

def relevance_router(state: AgentState):
    return "select_tools" if state["relevancy"] == "relevant" else "funny_response"

def execute_tools_router(state: AgentState):
    if state.get("tool_results"):
        return "generate_answer"
    return END

def validation_router(state: AgentState):
    validation_passed = state.get("validation_passed")
    
    if validation_passed is True:
        return END
    elif validation_passed is False:
        return "regenerate_sql"
    else:
        return END

def regenerate_router(state: AgentState):
    sql_attempts = state.get("sql_attempts", 0)
    max_attempts = 3
    
    if sql_attempts >= max_attempts:
        return END
    else:
        return "validate_response"