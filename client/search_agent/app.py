import asyncio
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from search_agent.node import researcher, researcher_router, tools

async def final_answer_generator(state: MessagesState):
    """Convert search agent result to orchestrator format"""
    messages = state.get("messages", [])
    if messages:
        last_message = messages[-1]
        if hasattr(last_message, 'content'):
            final_answer = last_message.content
        else:
            final_answer = str(last_message)
    else:
        final_answer = "No answer generated"
    return {
        "final_answer": final_answer,
        "messages": messages
    }

def build_app():
    # Create the StateGraph for the research agent
    builder = StateGraph(MessagesState)
    builder.add_node("researcher", researcher)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("final_answer_generator", final_answer_generator)
    builder.set_entry_point("researcher")
    builder.add_edge("tools", "researcher")
    builder.add_conditional_edges(
        "researcher",
        researcher_router,
        {"tools": "tools", END: "final_answer_generator"},
    )
    builder.add_edge("final_answer_generator", END)
    graph = builder.compile()
    
    return graph
