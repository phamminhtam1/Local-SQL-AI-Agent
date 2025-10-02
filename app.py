from langgraph.graph import StateGraph, END
from agent.state import AgentState
from agent.node import check_relevancy, planner_llm, executor, evaluator_llm, final_answer_generator, funny_response
from agent.routers import relevance_router, evaluator_router
from langgraph.checkpoint.memory import MemorySaver
def build_app():
    memory = MemorySaver()
    workflow = StateGraph(AgentState)

    workflow.add_node("check_relevance", check_relevancy)
    workflow.add_node("planner_llm", planner_llm)
    workflow.add_node("executor", executor)
    workflow.add_node("evaluator_llm", evaluator_llm)
    workflow.add_node("final_answer_generator", final_answer_generator)
    workflow.add_node("funny_response", funny_response)
    workflow.add_conditional_edges(
        "check_relevance",
        relevance_router,
        {
            "planner_llm": "planner_llm", 
            "funny_response": "funny_response"
        }
    )
    workflow.add_edge("planner_llm", "executor")
    workflow.add_edge("executor", "evaluator_llm")
    workflow.add_conditional_edges(
        "evaluator_llm",
        evaluator_router,
        {"planner_llm": "planner_llm", "final_answer_generator": "final_answer_generator"}
    )
    workflow.add_edge("final_answer_generator", END)
    workflow.add_edge("funny_response", END)
    
    workflow.set_entry_point("check_relevance")
    return workflow.compile(
        checkpointer=memory
    )


if __name__ == "__main__":
    app = build_app()
    print(app.invoke({"question": "Show me all users"}))
