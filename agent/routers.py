from .state import AgentState

def relevance_router(state: AgentState):
    return "select_tools" if state["relevancy"] == "relevant" else "funny_response"

def execute_tools_router(state: AgentState):
    if state.get("tool_results"):
        return "generate_answer"
    return "END"