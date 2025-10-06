from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class DatabaseType(str, Enum):
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"
    REDIS = "redis"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    SQLSERVER = "sqlserver"

class ProxyRequest(BaseModel):
    """Base model cho proxy requests"""
    uuid: str
    operation: Optional[str] = None
    target: Optional[str] = None
    path: Optional[str] = None
    arguments: Optional[Dict[str, Any]] = {}
    metadata: Optional[Dict[str, Any]] = {}