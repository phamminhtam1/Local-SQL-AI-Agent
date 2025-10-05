import asyncio
import os
from fastmcp import Client
import json
import logging
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, url: str = None):
        self.url = url or os.getenv("MCP_SEARCH_SERVER_URL")
        self.connected = False
        self.client = None
        self.available_tools = []
        
    async def connect(self):
        """Connect to MCP server"""
        try:
            self.client = Client(self.url)
            self.connected = True
            logger.info("Connected to Search MCP server ")
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
    
    async def get_available_tools(self):
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
        try:
            async with self.client:
                tools = await self.client.list_tools()
                return tools
        except Exception as e:
            logger.error(f"Failed to get available tools: {e}")
            return []

    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.client:
            self.client = None
            self.connected = False
            logger.info("Disconnected from Search MCP server")
            
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