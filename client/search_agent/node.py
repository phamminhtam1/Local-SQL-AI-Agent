import json
import os
import asyncio
from langchain_core.messages import SystemMessage
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_tavily import TavilySearch, TavilyExtract
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

llm = ChatOpenAI(
    name="Researcher",
    model="gpt-4o-mini", 
    api_key=os.getenv("OPENAI_API_KEY"),
)

prompt = """
## Role
You are a research assistant. Your job is to help the user answer questions by performing research. 
You MUST use the available tools to search for information. Do not provide generic answers.

## Instructions
1. ALWAYS start by using the search_web tool to find current information
2. If you need more details, use extract_content_from_webpage to get full content from relevant URLs
3. Base your answer on the search results you find
4. If you cannot find information, say so clearly

## Available Tools
- search_web: Search the web for current information. Use this FIRST for any research question.
- extract_content_from_webpage: Extract full content from a specific webpage URL.

## Example
User asks: "What is the current Bitcoin price?"
You should:
1. Call search_web with query "current Bitcoin price 2024"
2. Analyze the results
3. Provide the current price based on the search results
"""


@tool
def search_web(query: str, num_results: int = 3):
    """Search the web and get back a list of results."""
    print(f"🔍 search_web called with query: '{query}', num_results: {num_results}")
    
    try:
        web_search = TavilySearch(max_results=min(num_results, 3), topic="general")
        search_results = web_search.invoke({"query": query})
        
        print(f"📊 Search returned {len(search_results.get('results', []))} results")

        formatted_result = {
            "query": query,
            "result": []
        }
        for result in search_results["results"]:
            formatted_result["result"].append({
                "title": result["title"],
                "url": result["url"],
                "content": result["content"]
            })
        
        print(f"✅ search_web returning {len(formatted_result['result'])} results")
        return formatted_result
    except Exception as e:
        print(f"❌ search_web error: {e}")
        return {
            "query": query,
            "result": [],
            "error": str(e)
        }

@tool
def extract_content_from_webpage(url: str):
    """Extract the content from a webpage."""
    extractor = TavilyExtract()
    results = extractor.invoke(input={"urls": [url]})["results"]
    return results

tools = [search_web, extract_content_from_webpage]

async def researcher(state: MessagesState):
    research_agent = create_react_agent(llm, tools=tools)
    # Invoke the agent with proper dict-shaped state and prepend the system message
    messages = state.get("messages", [])
    
    # Debug: Print what we're sending to the agent
    print(f"🔍 Sending to agent: {len(messages)} messages")
    
    agent_state = await research_agent.ainvoke({
        "messages": [SystemMessage(content=prompt)] + messages
    })
    
    # Debug: Print the agent's response
    print(f"🤖 Agent response: {len(agent_state['messages'])} messages")
    if agent_state["messages"]:
        last_message = agent_state["messages"][-1]
        print(f"📝 Last message type: {type(last_message)}")
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            print(f"🔧 Tool calls: {len(last_message.tool_calls)}")
            for i, tool_call in enumerate(last_message.tool_calls):
                print(f"  Tool {i+1}: {tool_call['name']}")
    
    # Return only the latest assistant message to append to MessagesState
    return {"messages": [agent_state["messages"][-1]]}

async def researcher_router(state: MessagesState) -> str:
    messages = state.get("messages", [])
    if messages and hasattr(messages[-1], "tool_calls") and messages[-1].tool_calls:
        return "tools"
    return END

# StateGraph definition moved to app.py

