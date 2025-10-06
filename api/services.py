from fastapi import HTTPException, Request
from typing import Dict, Any
import httpx, json, logging
from datetime import datetime

from models import DatabaseType
from settings import PROXY_TARGETS
from connstr_builder import ConnectionStringBuilder

logger = logging.getLogger(__name__)

class UniversalProxyService:
    def __init__(self):
        self.connection_builder = ConnectionStringBuilder()

    async def execute_universal_flow(
        self,
        request: Request,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """
        Universal Flow - Forward to API:
        1. Get UUID from request (optional)
        2. Get DB config from Vault (only if UUID exists)
        3. Create connection string (only if DB config exists)
        4. Forward request to API
        5. Return result
        """
        
        try:
            # Step 1: Get UUID (optional)
            uuid = await self._extract_uuid(request)
            logger.info(f"Step 1: Extracted UUID: {uuid}")
            
            # Step 2-3: Get config and connection string (only if UUID exists)
            connection_string = None
            
            if uuid:
                try:
                    db_config = await self._get_db_config_from_vault(uuid, client)
                    logger.info(f"Step 2: Retrieved DB config from Vault")
                    
                    if db_config:
                        connection_string = self._generate_connection_string(db_config)
                        logger.info(f"Step 3: Generated connection string for {db_config.get('type', 'mysql')}")
                        logger.info(f"Step 3: Connection string: {connection_string}")
                except Exception as e:
                    logger.warning(f"Failed to get DB config: {str(e)}")
                    # Continue without config
            
            # Step 4: Forward request to API (always)
            modified_request = await self._modifier_request(request, connection_string)
            result = await self._forward_request(modified_request, client)
            logger.info(f"Step 4: Forwarded request to API")
            
            # Step 5: Return result
            return {
                "uuid": uuid,
                "connection_string": connection_string,
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

    async def _extract_uuid(self, request: Request) -> str | None:
        """Get UUID from request - flexible, return None if not found"""
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
        
        # Return None if not found instead of raising exception
        return uuid

    async def _modifier_request(
        self,
        request: Request,
        connection_string: str | None
    ) -> Request:
        """Add connection string to request (if available)"""
        # Store connection string for later use
        request._connection_string = connection_string
        
        # Always create modified body for POST/PUT/PATCH to avoid Content-Length issues
        if request.method in ["POST", "PUT", "PATCH"]:
            body = await request.body()
            if body:
                try:
                    body_data = json.loads(body)
                    if connection_string:
                        body_data["connection_string"] = connection_string
                    request._modified_body = json.dumps(body_data).encode()
                except:
                    # If not JSON, create new body
                    if connection_string:
                        body_data = {"connection_string": connection_string}
                    else:
                        body_data = {}
                    request._modified_body = json.dumps(body_data).encode()
            else:
                # Empty body, create new body
                if connection_string:
                    body_data = {"connection_string": connection_string}
                else:
                    body_data = {}
                request._modified_body = json.dumps(body_data).encode()
        
        return request
    
    async def _forward_request(
        self,
        request: Request,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Forward the request to API (with optional connection_string)"""
        try:
            # Get the full path after the first segment
            path = request.url.path.strip('/')
            path_parts = path.split('/')
            
            if len(path_parts) > 1:
                operation = '/'.join(path_parts[1:])
            else:
                operation = "database"
            
            base_url = PROXY_TARGETS["self"]
            target_url = f"{base_url}/{operation}"
            
            logger.info(f"Forwarding request to: {target_url}")
            
            # Prepare headers
            headers = dict(request.headers)
            
            # Remove Content-Length headers completely - let httpx handle it
            headers.pop('Content-Length', None)
            headers.pop('content-length', None)
            
            # Get connection string from request if available
            connection_string = getattr(request, '_connection_string', None)
            
            # Prepare body and params based on method
            request_body = None
            params = dict(request.query_params)
            
            if request.method in ["POST", "PUT", "PATCH"]:
                # Use modified body if available
                if hasattr(request, '_modified_body'):
                    request_body = request._modified_body
                # Don't try to read body again if it's already been consumed
            else:
                # For GET and other methods, add connection_string to query params if available
                if connection_string:
                    params["connection_string"] = connection_string
            
            # Add connection string to headers if available
            if connection_string:
                headers["X-Connection-String"] = connection_string
            
            # Forward the request - let httpx handle Content-Length automatically
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=request_body,
                params=params
            )
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error forwarding request: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Request forwarding failed: {str(e)}")
    
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