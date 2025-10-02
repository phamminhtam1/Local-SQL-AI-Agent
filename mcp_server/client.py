import asyncio
import json
import os
from contextlib import AsyncExitStack
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.tools import load_mcp_tools

load_dotenv()
SSE_URL = "http://127.0.0.1:5050/sse"

class MCPClient:
    def __init__(self, sse_url: str = SSE_URL):
        self.sse_url = sse_url
        self.session = None
        self.exit_stack = None
        self.tools = []
        self.state_graph = None
        self.memory = MemorySaver()
        self.supervisor_agent = None

    async def connect(self):
        self.exit_stack = AsyncExitStack()
        await self.exit_stack.__aenter__()
        read, write = await self.exit_stack.enter_async_context(sse_client(self.sse_url))
        self.session = await self.exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        print("Connected to MCP server")
        await self.load_tools()

    async def load_tools(self):
        self.tools = await load_mcp_tools(self.session)
        tool_names = [t.name for t in self.tools]
        print(f"Available tools: {tool_names}")




# -------------------- Run --------------------
async def main():
    client = MCPClient()
    await client.connect()
    # Define langgraph workflow 
    await client.build_graph()
    try:
        # Define chat loop
        await client.chat_loop()
    finally:
        if client.exit_stack:
            await client.exit_stack.aclose()
            print("Session closed.")

if __name__=="__main__":
    asyncio.run(main())