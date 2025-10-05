from fastapi import HTTPException, Request
from typing import Dict, Any
import httpx, json, logging
from datetime import datetime

from models import DatabaseType, ProxyRequest
from settings import PROXY_TARGETS

logger = logging.getLogger(__name__)

class UniversalProxyService:
    def __init__(self):
        self.targets = PROXY_TARGETS
        self.db_connection_generators = {
            DatabaseType.MYSQL: self._generate_mysql_connection,
            DatabaseType.POSTGRESQL: self._generate_postgresql_connection,
            DatabaseType.MONGODB: self._generate_mongodb_connection,
            DatabaseType.REDIS: self._generate_redis_connection,
            DatabaseType.SQLITE: self._generate_sqlite_connection,
            DatabaseType.ORACLE: self._generate_oracle_connection,
            DatabaseType.SQLSERVER: self._generate_sqlserver_connection,
        }
    
    async def execute_universal_flow(
        self,
        request: Request,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """
        Universal Flow với Flexible Arguments:
        1. Nhận UUID và các arguments khác từ client
        2. Gọi Vault API để lấy DB config
        3. Tạo connection string
        4. Quyết định forward mode (self hoặc external)
        5. Xử lý và trả về kết quả
        """
        
        try:
            # Step 1: Nhận UUID và các arguments khác từ client
            request_data = await self._extract_request_data(request)
            logger.info(f"Step 1: Extracted request data: {request_data}")
            
            # Step 2: Gọi Vault API để lấy DB config
            db_config = await self._get_db_config_from_vault(request_data.uuid, client)
            logger.info(f"Step 2: Retrieved DB config from Vault")
            
            # Step 3: Tạo connection string
            connection_string = self._generate_connection_string(db_config)
            logger.info(f"Step 3: Generated connection string for {db_config.get('type', 'mysql')}")
            
            # Step 4: Quyết định forward mode
            target, path = await self._determine_target(request, request_data)
            
            if target == "self":
                # Mode 1: Self-processing
                result = await self._handle_self_processing(
                    request, path, connection_string, db_config, request_data, client
                )
            else:
                # Mode 2: External forwarding
                result = await self._handle_external_forwarding(
                    target, path, request, connection_string, db_config, request_data, client
                )
            
            logger.info(f"Step 4: Processed request in {target} mode")
            
            # Step 5: Trả về kết quả
            return {
                "uuid": request_data.uuid,
                "target": target,
                "path": path,
                "mode": "self" if target == "self" else "external",
                "arguments": request_data.arguments,
                "metadata": request_data.metadata,
                "db_config": db_config,
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

    async def _extract_request_data(self, request: Request) -> ProxyRequest:
        """Step 1: Nhận UUID và các arguments khác từ client"""
        try:
            # Lấy từ headers
            uuid = request.headers.get("X-User-UUID")
            operation = request.headers.get("X-Operation")
            target = request.headers.get("X-Target")
            path = request.headers.get("X-Path")
            
            # Lấy từ body nếu có
            body_data = {}
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        body_data = json.loads(body)
                    except:
                        body_data = {}
            
            # Ưu tiên body data nếu có
            if body_data:
                uuid = body_data.get("uuid") or uuid
                operation = body_data.get("operation") or operation
                target = body_data.get("target") or target
                path = body_data.get("path") or path
                arguments = body_data.get("arguments", {})
                metadata = body_data.get("metadata", {})
            else:
                arguments = {}
                metadata = {}
            
            # Lấy từ query parameters
            query_params = dict(request.query_params)
            if query_params:
                uuid = query_params.get("uuid") or uuid
                operation = query_params.get("operation") or operation
                target = query_params.get("target") or target
                path = query_params.get("path") or path
                arguments.update({k: v for k, v in query_params.items() 
                                if k not in ["uuid", "operation", "target", "path"]})
            
            if not uuid:
                raise HTTPException(status_code=400, detail="UUID is required")
            
            return ProxyRequest(
                uuid=uuid,
                operation=operation,
                target=target,
                path=path,
                arguments=arguments,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error extracting request data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid request data: {str(e)}")
    
    async def _handle_self_processing(
        self,
        request: Request,
        path: str,
        connection_string: str,
        db_config: Dict[str, Any],
        request_data: ProxyRequest,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Mode 1: Self-processing với flexible arguments"""
        try:
            # Xác định operation từ path hoặc request_data
            operation, sub_path = await self._determine_operation_from_path(path, request_data)
            
            # Lấy method và body
            method = request.method
            body_data = {}
            if method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        body_data = json.loads(body)
                    except:
                        body_data = {}
            
            # Merge arguments từ request_data và body_data
            merged_arguments = {**request_data.arguments, **body_data}
            
            # Xử lý các operations khác nhau
            if operation == "db":
                return await self._process_db_operations(
                    sub_path, method, merged_arguments, connection_string, db_config, request_data
                )
            elif operation == "search":
                return await self._process_search_operations(
                    sub_path, method, merged_arguments, connection_string, db_config, request_data
                )
            elif operation == "health":
                return await self._process_health_operations(
                    sub_path, method, merged_arguments, connection_string, db_config, request_data
                )
            else:
                raise HTTPException(status_code=404, detail=f"Operation '{operation}' not supported in self mode")
                
        except Exception as e:
            logger.error(f"Error in self-processing: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Self-processing failed: {str(e)}")
    
    async def _handle_external_forwarding(
        self,
        target: str,
        path: str,
        request: Request,
        connection_string: str,
        db_config: Dict[str, Any],
        request_data: ProxyRequest,
        client: httpx.AsyncClient
    ) -> Dict[str, Any]:
        """Mode 2: External forwarding với flexible arguments"""
        try:
            if target not in self.targets:
                raise HTTPException(status_code=404, detail=f"Target '{target}' not found")
            
            target_url = self.targets[target]
            full_url = f"{target_url.rstrip('/')}/{path.lstrip('/')}"
            
            # Chuẩn bị headers
            headers = dict(request.headers)
            headers["X-Connection-String"] = connection_string
            headers["X-Database-Type"] = db_config.get("type", "mysql")
            headers["X-User-UUID"] = request_data.uuid
            headers["X-Arguments"] = json.dumps(request_data.arguments)
            headers["X-Metadata"] = json.dumps(request_data.metadata)
            
            # Loại bỏ headers có thể gây conflict
            forward_headers = {k: v for k, v in headers.items() 
                            if k.lower() not in ['host', 'content-length']}
            
            # Lấy body nếu có
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
            
            # Lấy query parameters
            params = dict(request.query_params)
            
            # Forward đến external service
            response = await client.request(
                method=request.method,
                url=full_url,
                headers=forward_headers,
                content=body,
                params=params
            )
            
            return {
                "type": "external_forward",
                "target": target,
                "url": full_url,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.content,
                "text": response.text
            }
            
        except Exception as e:
            logger.error(f"Error in external forwarding to {target}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"External forwarding failed: {str(e)}")
    
    # Self-processing methods
    async def _process_db_operations(
        self,
        path: str,
        method: str,
        body_data: Dict[str, Any],
        connection_string: str,
        db_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Xử lý database operations trong self mode"""
        
        if path == "health":
            return await self._check_db_health(connection_string, db_config)
        elif path == "query":
            return await self._execute_db_query(body_data, connection_string, db_config)
        elif path == "tables":
            return await self._get_db_tables(connection_string, db_config)
        elif path == "schema":
            return await self._get_db_schema(body_data, connection_string, db_config)
        else:
            raise HTTPException(status_code=404, detail=f"DB path '{path}' not supported")
    
    async def _process_search_operations(
        self,
        path: str,
        method: str,
        body_data: Dict[str, Any],
        connection_string: str,
        db_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Xử lý search operations trong self mode"""
        
        if path == "query":
            return await self._execute_search_query(body_data, connection_string, db_config)
        elif path == "index":
            return await self._create_search_index(body_data, connection_string, db_config)
        else:
            raise HTTPException(status_code=404, detail=f"Search path '{path}' not supported")
    
    async def _process_health_operations(
        self,
        path: str,
        method: str,
        body_data: Dict[str, Any],
        connection_string: str,
        db_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Xử lý health operations trong self mode"""
        
        return {
            "status": "healthy",
            "database_type": db_config.get("type", "mysql"),
            "connection_string": connection_string,
            "timestamp": datetime.now().isoformat()
        }
    
    # Database operation implementations
    async def _check_db_health(self, connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Kiểm tra health của database"""
        try:
            # Simulate database health check
            return {
                "status": "healthy",
                "database_type": db_config.get("type", "mysql"),
                "connection_string": connection_string,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_db_query(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Thực thi database query"""
        try:
            sql = body_data.get("sql", "")
            params = body_data.get("params", [])
            
            # Simulate query execution
            return {
                "sql": sql,
                "params": params,
                "result": "Query executed successfully",
                "rows_affected": 1,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _get_db_tables(self, connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Lấy danh sách tables"""
        try:
            return {
                "tables": ["users", "orders", "products"],
                "count": 3,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _get_db_schema(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Lấy schema của table"""
        try:
            table_name = body_data.get("table", "")
            return {
                "table": table_name,
                "columns": [
                    {"name": "id", "type": "INT", "nullable": False},
                    {"name": "name", "type": "VARCHAR", "nullable": True},
                    {"name": "email", "type": "VARCHAR", "nullable": True}
                ],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # Search operation implementations
    async def _execute_search_query(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Thực thi search query"""
        try:
            query = body_data.get("query", "")
            filters = body_data.get("filters", {})
            
            return {
                "query": query,
                "filters": filters,
                "results": [
                    {"id": 1, "title": "Sample Result 1", "score": 0.95},
                    {"id": 2, "title": "Sample Result 2", "score": 0.87}
                ],
                "total": 2,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _create_search_index(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Tạo search index"""
        try:
            index_name = body_data.get("name", "")
            fields = body_data.get("fields", [])
            
            return {
                "index_name": index_name,
                "fields": fields,
                "status": "created",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    # Helper methods
    async def _extract_uuid(self, request: Request) -> str:
        """Nhận UUID từ client"""
        uuid = request.headers.get("X-User-UUID")
        
        if not uuid:
            try:
                body = await request.body()
                if body:
                    body_data = json.loads(body)
                    uuid = body_data.get("uuid")
            except:
                pass
        
        if not uuid:
            raise HTTPException(status_code=400, detail="UUID is required in header 'X-User-UUID' or in request body")
        
        return uuid
    
    async def _get_db_config_from_vault(self, uuid: str, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Gọi Vault API để lấy DB config"""
        try:
            vault_url = PROXY_TARGETS["vault"]
            response = await client.get(f"{vault_url}/v1/secret/data/{uuid}/db-config")
            
            if response.status_code == 200:
                vault_data = response.json()
                return vault_data.get("data", {}).get("data", {})
            else:
                raise HTTPException(status_code=404, detail="DB config not found in Vault")
                
        except Exception as e:
            logger.error(f"Error getting DB config from Vault for UUID {uuid}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get DB config from Vault")
    
    def _generate_connection_string(self, db_config: Dict[str, Any]) -> str:
        """Tạo connection string"""
        try:
            db_type = db_config.get("type", "mysql").lower()
            
            if db_type in [db.value for db in DatabaseType]:
                db_enum = DatabaseType(db_type)
                return self.db_connection_generators[db_enum](db_config)
            else:
                logger.warning(f"Unknown database type '{db_type}', using MySQL")
                return self._generate_mysql_connection(db_config)
                
        except Exception as e:
            logger.error(f"Error generating connection string: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate connection string")
    
    async def _determine_target(self, request: Request, request_data: ProxyRequest) -> tuple[str, str]:
        """Xác định target và path từ request hoặc request_data"""
        # Ưu tiên request_data.target
        if request_data.target:
            return request_data.target, request_data.path or "health"
        
        # Fallback về path parsing
        path_parts = request.url.path.strip('/').split('/')
        
        if len(path_parts) >= 3:
            target = path_parts[2]
            path = '/'.join(path_parts[3:])
        else:
            target = "self"
            path = "db/health"
        
        return target, path
    
    async def _determine_operation_from_path(self, path: str, request_data: ProxyRequest) -> tuple[str, str]:
        """Xác định operation từ path hoặc request_data"""
        if request_data.operation:
            return request_data.operation, path
        
        path_parts = path.strip('/').split('/')
        
        if len(path_parts) >= 1:
            operation = path_parts[0]
            sub_path = '/'.join(path_parts[1:]) if len(path_parts) > 1 else ""
        else:
            operation = "db"
            sub_path = "health"
        
        return operation, sub_path
    
    # Connection string generators (giữ nguyên)
    def _generate_mysql_connection(self, config: Dict[str, Any]) -> str:
        host = config.get("host", "localhost")
        port = config.get("port", "3306")
        database = config.get("database", "default")
        username = config.get("username", "root")
        password = config.get("password", "")
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    
    def _generate_postgresql_connection(self, config: Dict[str, Any]) -> str:
        host = config.get("host", "localhost")
        port = config.get("port", "5432")
        database = config.get("database", "default")
        username = config.get("username", "postgres")
        password = config.get("password", "")
        return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    def _generate_mongodb_connection(self, config: Dict[str, Any]) -> str:
        host = config.get("host", "localhost")
        port = config.get("port", "27017")
        database = config.get("database", "default")
        username = config.get("username", "")
        password = config.get("password", "")
        if username and password:
            return f"mongodb://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"mongodb://{host}:{port}/{database}"
    
    def _generate_redis_connection(self, config: Dict[str, Any]) -> str:
        host = config.get("host", "localhost")
        port = config.get("port", "6379")
        database = config.get("database", "0")
        password = config.get("password", "")
        if password:
            return f"redis://:{password}@{host}:{port}/{database}"
        else:
            return f"redis://{host}:{port}/{database}"
    
    def _generate_sqlite_connection(self, config: Dict[str, Any]) -> str:
        database = config.get("database", "default.db")
        return f"sqlite:///{database}"
    
    def _generate_oracle_connection(self, config: Dict[str, Any]) -> str:
        host = config.get("host", "localhost")
        port = config.get("port", "1521")
        database = config.get("database", "default")
        username = config.get("username", "system")
        password = config.get("password", "")
        return f"oracle://{username}:{password}@{host}:{port}/{database}"
    
    def _generate_sqlserver_connection(self, config: Dict[str, Any]) -> str:
        host = config.get("host", "localhost")
        port = config.get("port", "1433")
        database = config.get("database", "default")
        username = config.get("username", "sa")
        password = config.get("password", "")
        return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"