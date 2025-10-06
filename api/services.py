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
        1. Require UUID and name from request body (all methods)
        2. Get DB config from Vault (by UUID)
        3. Create connection string (if DB config exists)
        4. Forward request to API
        5. Return result
        """
        
        try:
            # Step 1: Get UUID and name (optional)
            uuid, name = await self._extract_required_fields(request)
            logger.info(f"Step 1: Extracted UUID: {uuid}")
            
            # Step 2-3: Get config and connection string (only if UUID exists)
            connection_string = None
            
            if uuid and name:
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

    async def _extract_required_fields(self, request: Request) -> tuple[str, str]:
        """Require uuid and name from request body for any method"""
        try:
            body = await request.body()
            if not body:
                raise HTTPException(status_code=400, detail="Request body is required and must include 'uuid' and 'name'")
            data = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body. Must include 'uuid' and 'name'")

        uuid = data.get("uuid")
        name = data.get("name")

        if not uuid or not name:
            raise HTTPException(status_code=400, detail="Missing required fields: 'uuid' and 'name'")

        # store parsed body for later reuse to avoid double reads
        request._original_body_json = data
        return uuid, name

    async def _modifier_request(
        self,
        request: Request,
        connection_string: str | None
    ) -> Request:
        """Add connection string to request (if available)"""
        # Store connection string for later use
        request._connection_string = connection_string

        # Always add connection string to request body
        body_json = {}

        # Reuse already parsed body if available
        if hasattr(request, '_original_body_json'):
            body_json = dict(request._original_body_json)
        else:
            body_json = await request.body()
            if body_json:
                try:
                    body_json = json.loads(body_json)
                except:
                    body_json = {}

        # Add connection string to request body
        if connection_string:
            body_json["connection_string"] = connection_string
        
        request._modified_body = json.dumps(body_json).encode()
        
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
            headers.setdefault('Content-Type', 'application/json')
            headers.setdefault('Accept', 'application/json')
            
            # Get connection string from request if available
            connection_string = getattr(request, '_connection_string', None)
            
            # Always use modified body for POST/PUT/PATCH
            request_body = getattr(request, '_modified_body', None)

            # Prepare body and params based on method
            params = dict(request.query_params)
            
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

            fallback_methods = {"GET", "PUT","PATCH", "DELETE"}
            retryable_status = {400, 405, 411, 415, 501}

            original_method = request.method.upper()
            if original_method in fallback_methods and response.status_code in retryable_status:
                retry_headers = dict(headers)
                retry_headers["X-HTTP-Method-Override"] = original_method

                # Retry by POST               
                response = await client.request(
                    method="POST",
                    url=target_url,
                    headers=retry_headers,
                    content=request_body,
                    params=params
                )

            try:
                return response.json()
            except:
                content = await response.aread()
                return {
                    "status_code": response.status_code,
                    "text": content.decode(errors="ignore")
                }
            
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