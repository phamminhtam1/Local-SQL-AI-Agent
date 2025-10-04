import asyncio
import logging
import os
from fastmcp import Client

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class MCPClient:
    def __init__(self, url: str = None):
        self.url = url or os.getenv("MCP_SERVER_URL", "http://mcp_server:8000/mcp")
        self.client = None
        self.connected = False

    async def connect(self):
        try:
            self.client = Client(self.url)
            self.connected = True
            logger.info("Connected to MCP server at %s", self.url)
        except Exception as e:
            logger.error("Failed to connect to MCP server: %s", e)
            raise

    async def get_available_tools(self, timeout: int = 5):
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            async with self.client:
                # Get available tools using the new API
                tools = await self.client.list_tools()
                return tools
        except Exception as e:
            logger.error("Failed to get available tools: %s", e)
            return None

    async def call_tool(self, tool_name: str, arguments=None, timeout: int = 10):
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
        
        try:
            async with self.client:
                result = await self.client.call_tool(tool_name, arguments or {})
                return result
        except Exception as e:
            logger.error("Failed to call tool %s: %s", tool_name, e)
            return None

    async def disconnect(self):
        if self.client:
            self.client = None
            self.connected = False
            logger.info("Disconnected from MCP server")
