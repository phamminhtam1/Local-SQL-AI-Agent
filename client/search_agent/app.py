from langgraph.graph import StateGraph, END
from search_agent.state import SearchAgentState
from search_agent.node import planner_llm, executor, evaluator_llm, final_answer_generator
from search_agent.routers import evaluator_router

def build_app():
    workflow = StateGraph(SearchAgentState)

    workflow.add_node("planner_llm", planner_llm)
    workflow.add_node("executor", executor)
    workflow.add_node("evaluator_llm", evaluator_llm)
    workflow.add_node("final_answer_generator", final_answer_generator)
    
    workflow.add_edge("planner_llm", "executor")
    workflow.add_edge("executor", "evaluator_llm")
    workflow.add_conditional_edges(
        "evaluator_llm",
        evaluator_router,
        {"planner_llm": "planner_llm", "final_answer_generator": "final_answer_generator"}
    )
    workflow.add_edge("final_answer_generator", END)
    
    workflow.set_entry_point("planner_llm")
    return workflow.compile()
