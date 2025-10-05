import asyncio
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from search_agent.node import researcher, researcher_router, tools

def build_app():
    # Create the StateGraph for the research agent
    builder = StateGraph(MessagesState)
    builder.add_node(researcher)
    builder.add_node("tools", ToolNode(tools))
    builder.set_entry_point("researcher")
    builder.add_edge("tools", "researcher")
    builder.add_conditional_edges(
        "researcher",
        researcher_router,
        {"tools": "tools", END: END},
    )
    graph = builder.compile()
    
    return graph

async def main():
    graph = build_app()
    result = await graph.ainvoke({
        "messages": [
            {"role": "user", "content": "Hãy tìm thông tin về giá hiện tại của Bitcoin và viết báo cáo ngắn."}
        ]
    })
    print("\n✅ Kết quả cuối cùng:")
    print(result["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
