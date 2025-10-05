from fastapi import HTTPException, Request
from typing import Dict, Any
import logging, json
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseTools:
    """Tools cho database operations"""
    
    async def database_logic(self, request: Request, connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Logic process database operations"""
        try:
            # Lấy request data
            body_data = {}
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    body_data = json.loads(body)
            
            # process logic database
            path = request.url.path.strip('/')
            logger.info(f"Path: {path}")
            sub_path = '/'.join(path.split('/')[2:]) if len(path.split('/')) > 1 else "health"
            logger.info(f"Sub path: {sub_path}")
            
            if sub_path == "health":
                return await self.check_db_health(connection_string, db_config)
            elif sub_path == "query":
                return await self.execute_db_query(body_data, connection_string, db_config)
            elif sub_path == "tables":
                return await self.get_db_tables(connection_string, db_config)
            elif sub_path == "schema":
                return await self.get_db_schema(body_data, connection_string, db_config)
            else:
                raise HTTPException(status_code=404, detail=f"DB path '{sub_path}' not supported")
                
        except Exception as e:
            logger.error(f"Error in db logic: {str(e)}")
            raise HTTPException(status_code=500, detail=f"DB logic failed: {str(e)}")

    async def check_db_health(self, connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Kiểm tra health của database"""
        try:
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
    
    async def execute_db_query(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
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
    
    async def get_db_tables(self, connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
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
    
    async def get_db_schema(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
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

class SearchTools:
    """Tools cho search operations"""
    
    async def search_logic(self, request: Request, connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Logic process search operations"""
        try:
            body_data = {}
            if request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    body_data = json.loads(body)
            
            path = request.url.path.strip('/')
            sub_path = '/'.join(path.split('/')[1:]) if len(path.split('/')) > 1 else "query"
            
            if sub_path == "query":
                return await self.execute_search_query(body_data, connection_string, db_config)
            elif sub_path == "index":
                return await self.create_search_index(body_data, connection_string, db_config)
            else:
                raise HTTPException(status_code=404, detail=f"Search path '{sub_path}' not supported")
                
        except Exception as e:
            logger.error(f"Error in search logic: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Search logic failed: {str(e)}")

    async def execute_search_query(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
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
    
    async def create_search_index(self, body_data: Dict[str, Any], connection_string: str, db_config: Dict[str, Any]) -> Dict[str, Any]:
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