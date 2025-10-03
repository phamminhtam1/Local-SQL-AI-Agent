import asyncio
import json
import subprocess
import logging
from typing import Dict, Any, Optional, List
import os
import sys

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self):
        self.available_tools = []
        self.server_process = None
        self.connected = False
        
    async def connect(self):
        try:
            from mcp_server import mcp
        
            self.available_tools = [
                {"name": "list_tables", "description": "List all tables in the database with schema and sample rows"},
                {"name": "query_sql", "description": "Execute safe SELECT SQL queries on the database"}
            ]
            
            self.connected = True
            logger.info(f"Connected to MCP server with {len(self.available_tools)} tools")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False
    
    async def discover_tools(self):
        logger.info(f"Discovered tools: {[tool['name'] for tool in self.available_tools]}")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> str:
        try:
            if not self.connected:
                await self.connect()
                            
            tool_func = None
            if tool_name == "list_tables":
                from mcp_server import list_tables
                tool_func = list_tables
            elif tool_name == "query_sql":
                from mcp_server import query_sql
                tool_func = query_sql
            else:
                return f"Tool '{tool_name}' not found. Available tools: {[tool['name'] for tool in self.available_tools]}"
            
            if arguments and 'sql' in arguments:
                result = tool_func(arguments['sql'])
            else:
                result = tool_func()
            return str(result)
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return f"Error calling tool {tool_name}: {str(e)}"
    
    async def get_available_tools(self) -> List[str]:
        if not self.connected:
            await self.connect()
        return [tool['name'] for tool in self.available_tools]
    
    async def get_tool_info(self, tool_name: str) -> Optional[Dict]:
        try:
            tool = next((t for t in self.available_tools if t['name'] == tool_name), None)
            if tool:
                return {
                    "name": tool['name'],
                    "description": tool['description']
                }
            return None
        except Exception as e:
            logger.error(f"Error getting tool info for {tool_name}: {e}")
            return None
    
    async def disconnect(self):
        try:
            self.connected = False
            logger.info("Disconnected from MCP server")
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")

# Global MCP client instance
mcp_client = MCPClient()
