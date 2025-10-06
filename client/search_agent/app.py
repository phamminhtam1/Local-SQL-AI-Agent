import asyncio
from langgraph.graph import END, StateGraph
from search_agent.state import SearchAgentState
from search_agent.node import planner_llm, executor, evaluator_llm, final_answer_generator

def should_continue(state: SearchAgentState) -> str:
    """Determine if we should continue the loop or finish"""
    is_complete = state.get("is_complete", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if is_complete or iteration_count >= max_iterations:
        return "final_answer_generator"
    else:
        return "planner_llm"

def build_app():
    # Create the StateGraph for the search agent using React pattern
    builder = StateGraph(SearchAgentState)
    
    # Add nodes
    builder.add_node("planner_llm", planner_llm)
    builder.add_node("executor", executor)
    builder.add_node("evaluator_llm", evaluator_llm)
    builder.add_node("final_answer_generator", final_answer_generator)
    
    # Set entry point
    builder.set_entry_point("planner_llm")
    
    # Add edges
    builder.add_edge("planner_llm", "executor")
    builder.add_edge("executor", "evaluator_llm")
    builder.add_conditional_edges(
        "evaluator_llm",
        should_continue,
        {
            "planner_llm": "planner_llm",
            "final_answer_generator": "final_answer_generator"
        }
    )
    builder.add_edge("final_answer_generator", END)
    
    graph = builder.compile()
    return graph
