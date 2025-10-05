import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
try:
    import websockets
except ImportError:
    websockets = None
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self):
        self.connected = False
        self.websocket = None
        self.available_tools = []
        
    async def connect(self):
        """Connect to MCP server"""
        if websockets is None:
            logger.error("websockets library not available")
            self.connected = False
            return
            
        try:
            self.websocket = await websockets.connect("http://localhost:8002")
            self.connected = True
            logger.info("Connected to MCP server")
            
            # Get available tools on connection
            await self.get_available_tools()
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            self.connected = False
            
    async def disconnect(self):
        """Disconnect from MCP server"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("Disconnected from MCP server")
            
    async def get_available_tools(self) -> List[Dict]:
        """Get list of available tools from MCP server"""
        if not self.connected:
            await self.connect()
            
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list"
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if "result" in data and "tools" in data["result"]:
                self.available_tools = data["result"]["tools"]
                logger.info(f"Retrieved {len(self.available_tools)} tools")
                return self.available_tools
            else:
                logger.error(f"Failed to get tools: {data}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting available tools: {e}")
            return []
            
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """Call a specific tool with parameters"""
        if not self.connected:
            await self.connect()
            
        try:
            request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": parameters
                }
            }
            
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if "result" in data:
                return data["result"]
            else:
                error_msg = data.get("error", {}).get("message", "Unknown error")
                logger.error(f"Tool call failed: {error_msg}")
                raise Exception(f"Tool call failed: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            raise