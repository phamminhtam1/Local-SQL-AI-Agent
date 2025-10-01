from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.node import check_relevancy, select_tools, execute_tools, generate_answer, funny_response, validate_response, regenerate_sql
from agent.routers import relevance_router, execute_tools_router, validation_router, regenerate_router

def build_app():
    workflow = StateGraph(AgentState)

    workflow.add_node("check_relevance", check_relevancy)
    workflow.add_node("select_tools", select_tools)
    workflow.add_node("execute_tools", execute_tools)
    workflow.add_node("generate_answer", generate_answer)
    workflow.add_node("validate_response", validate_response)
    workflow.add_node("regenerate_sql", regenerate_sql)
    workflow.add_node("funny_response", funny_response)
    workflow.add_conditional_edges(
        "check_relevance",
        relevance_router,
        {"select_tools": "select_tools", "funny_response": "funny_response"}
    )
    workflow.add_edge("select_tools", "execute_tools")
    workflow.add_conditional_edges(
        "execute_tools",
        execute_tools_router,
        {"generate_answer": "generate_answer", END: END}
    )
    workflow.add_edge("generate_answer", "validate_response")
    workflow.add_conditional_edges(
        "validate_response",
        validation_router,
        {"regenerate_sql": "regenerate_sql", END: END}
    )
    workflow.add_conditional_edges(
        "regenerate_sql",
        regenerate_router,
        {"validate_response": "validate_response", END: END}
    )
    workflow.add_edge("funny_response", END)
    workflow.set_entry_point("check_relevance")
    return workflow.compile()

if __name__ == "__main__":
    app = build_app()
    print(app.invoke({"question": "Show me all users"}))
