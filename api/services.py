from fastapi import HTTPException, Request
from typing import Dict, Any
import httpx, json, logging
from datetime import datetime

from models import DatabaseType
from settings import PROXY_TARGETS
from connstr_builder import ConnectionStringBuilder
from tools import DatabaseTools, SearchTools

logger = logging.getLogger(__name__)

class UniversalProxyService:
    def __init__(self):
        self.connection_builder = ConnectionStringBuilder()
        self.database_tools = DatabaseTools()
        self.search_tools = SearchTools()
    
    async def execute_universal_flow(
        self,
        request: Request,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """
        Universal Flow - Call logic function directly:
        1. Get UUID from request
        2. Get DB config from Vault
        3. Create connection string
        4. Call logic function directly with connection string
        5. Return result
        """
        
        try:
            # Step 1: Get UUID
            uuid = await self._extract_uuid(request)
            logger.info(f"Step 1: Extracted UUID: {uuid}")
            
            # Step 2: Get DB config from Vault
            db_config = await self._get_db_config_from_vault(uuid, client)
            logger.info(f"Step 2: Retrieved DB config from Vault")
            
            # Step 3: Create connection string
            connection_string = self._generate_connection_string(db_config)
            logger.info(f"Step 3: Generated connection string for {db_config.get('type', 'mysql')}")
            logger.info(f"Step 3: Connection string: {connection_string}")
            
            # Step 4: Call logic function directly with connection string
            # need fix: forwarding to API
            result = await self._call_logic_function(
                request, connection_string, db_config
            )
            
            logger.info(f"Step 4: Called logic function")
            
            # Step 5: Return result
            return {
                "uuid": uuid,
                "connection_string": connection_string,
                "db_config": db_config,
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error in universal flow: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }

    async def _extract_uuid(self, request: Request) -> str:
        """Get UUID from request"""
        # Try headers first
        uuid = request.headers.get("X-User-UUID")
        
        if not uuid:
            # try body if POST/PUT/PATCH
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        body_data = json.loads(body)
                        uuid = body_data.get("uuid")
                except:
                    pass
        
        if not uuid:
            # Try query params
            uuid = request.query_params.get("uuid")
        
        if not uuid:
            raise HTTPException(status_code=400, detail="UUID is required")
        
        return uuid

    async def _call_logic_function(
        self,
        request: Request,
        connection_string: str,
        db_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call logic function directly"""
        try:
            # determine logic function from path
            path = request.url.path.strip('/')
            logic_function = self._determine_logic_function(path)
            logger.info(f"Logic function: {logic_function}")
            
            if not logic_function:
                raise HTTPException(status_code=404, detail=f"No logic function found for path: {path}")
            
            logger.info(f"Calling logic function: {logic_function}")
            
            # call logic function directly
            result = await logic_function(request, connection_string, db_config)
            
            return {
                "function": logic_function.__name__,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error calling logic function: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Logic function call failed: {str(e)}")

    def _determine_logic_function(self, path: str):
        """Determine logic function from path"""
        # get operation from path
        operation = path.split('/')[1] if path else "database"
        logger.info(f"Operation: {operation}")
        
        # mapping operation → logic function
        logic_functions = {
            "database": self.database_tools.database_logic,
            "search": self.search_tools.search_logic,
        }
        
        if operation in PROXY_TARGETS and operation != "vault":
            return logic_functions.get(operation)
        
        return None
    
    def _generate_connection_string(self, db_config: Dict[str, Any]) -> str:
        """Create connection string using ConnectionStringBuilder"""
        return self.connection_builder.generate_connection_string(db_config)

    async def _get_db_config_from_vault(self, uuid: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Get DB config from Vault"""
        try:
            vault_url = PROXY_TARGETS["vault"]
            logger.info(f"Getting DB config from Vault: {vault_url}")
            response = await client.get(f"{vault_url}/secrets?user_id={uuid}&include_values=true&name=string")
            
            if response.status_code == 200:
                vault_data = response.json()
                logger.info(f"Vault data: {vault_data}")
                return vault_data[0].get("data", {})
            else:
                raise HTTPException(status_code=404, detail="DB config not found in Vault")
            
        except Exception as e:
            logger.error(f"Error getting DB config from Vault for UUID {uuid}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get DB config from Vault")