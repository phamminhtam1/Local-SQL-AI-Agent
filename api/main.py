import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import create_engine, text
import httpx, logging, json
from datetime import datetime
from sqlalchemy import URL, create_engine, text
from services import UniversalProxyService
from models import DatabaseType, ProxyRequest
from settings import PROXY_TARGETS

# config logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import socket

app = FastAPI(
    title="Universal API Proxy",
    description="A flexible API proxy service with dual mode support (self-forwarding and external forwarding)",
    version="1.0.0"
)

# middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

# HTTP client with timeout and retry
async def get_http_client():
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    )

# Dependency to get HTTP client
async def get_client():
    client = await get_http_client()
    try:
        yield client
    finally:
        await client.aclose()

proxy_service = UniversalProxyService()

SUPPORTED_DB_DIRS = {
    "mysql": "mysql",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "mssql": "sqlserver",
    "sqlserver": "sqlserver",
    "oracle": "oracle",
    "sqlite": "sqlite",
    "redis": "Redis",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
}

def detect_db_type(connection_string: str) -> str:
    low = connection_string.lower()
    if "://" in low:
        scheme = low.split("://", 1)[0]
        base = scheme.split("+", 1)[0]
        if base == "postgres": base = "postgresql"
        if base in ("mssql", "sqlserver"): base = "sqlserver"
        if base == "mongo": base = "mongodb"
        return base
    return "mysql"


def resolve_query_path(op: str, db_type: str) -> str:
    """
    Trả về đường dẫn file query theo op và db_type.
    - SQL DBs → .sql
    - MongoDB/Redis → .py
    """
    dbt = SUPPORTED_DB_DIRS.get(db_type.lower())
    if not dbt:
        raise HTTPException(status_code=400, detail=f"Unsupported db_type: {db_type}")

    # Chọn phần mở rộng theo loại DB
    ext = ".py" if dbt in ("MongoDB", "Redis") else ".sql"

    candidate = os.path.join("queries", dbt, f"{op}{ext}")
    if os.path.exists(candidate):
        return candidate

    # Fallback legacy (chỉ áp dụng cho SQL .sql)
    if ext == ".sql":
        legacy = os.path.join("queries", f"{op}.sql")
        if os.path.exists(legacy):
            return legacy

    raise HTTPException(status_code=404, detail=f"Query file not found: {candidate}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "targets": list(PROXY_TARGETS.keys()),
        "supported_databases": [db.value for db in DatabaseType],
        "modes": ["self", "external"],
        "supported_arguments": ["uuid", "operation", "target", "path", "arguments", "metadata"]
    }

# Universal Proxy Endpoint with Flexible Arguments
@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], include_in_schema=True)
async def universal_proxy(
    request: Request,
    client: httpx.AsyncClient = Depends(get_client)
):
    """
    Universal Proxy with Flexible Arguments:
    1. Receive UUID and other arguments from client
    2. Call Vault API to get DB config
    3. Create connection string
    4. Decide mode (self or external)
    5. Process and return result
    """
    return await proxy_service.execute_universal_flow(request, client)

# Endpoint to get list of targets
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "targets": list(PROXY_TARGETS.keys()),
        "supported_databases": [db.value for db in DatabaseType],
        "logic_functions": [target for target in PROXY_TARGETS.keys() if target != "vault"],
        "external_services": ["vault"],
        "modes": ["self", "external"],
        "supported_arguments": ["uuid", "operation", "target", "path", "arguments", "metadata"]
    }

# Endpoint to get list of supported databases
@app.get("/databases")
async def get_supported_databases():
    """Get supported database types"""
    return {
        "supported_databases": [db.value for db in DatabaseType],
        "count": len(DatabaseType)
    }

# Middleware to log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    
    # log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # process request
    response = await call_next(request)
    
    # log response
    process_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"Response: {response.status_code} - {process_time:.3f}s")
    
    return response

# Flexible Proxy Endpoint
@app.post("/proxy/flexible")
async def flexible_proxy(
    request_data: ProxyRequest,
    client: httpx.AsyncClient = Depends(get_client)
):
    """
    Flexible Proxy Endpoint:
    Receive all arguments in request body
    """    
    # create body from request_data
    body = json.dumps(request_data.model_dump()).encode()
    
    # create mock request
    mock_request = Request({
        "type": "http", 
        "method": "POST", 
        "url": "/proxy/flexible",
        "headers": [],
        "query_string": b""
    })
    
    # set body for request
    mock_request._body = body
    
    return await proxy_service.execute_universal_flow(mock_request, client)

@app.post('/health_check')
async def check_health(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        db_type = detect_db_type(connection_string)
        query_path = resolve_query_path("health_check", db_type)

        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open(query_path).read())
            result = conn.execute(query)

            logger.info("Log query path: "+query_path)
            # Convert Row objects to dictionaries
            rows = []
            for row in result:
                rows.append(dict(row._mapping))  # Sử dụng _mapping

            logger.info("Health check query executed successfully")
            return rows
    except Exception as e:
        logger.error(f"Error checking health: {e}")
        return {"error": str(e)}


@app.post("/db_size")
async def check_db_size(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")
        db_name = data.get("db_name")
        
        if not connection_string:
            return {"error": "Missing connection_string in payload"}
        
        db_type = detect_db_type(connection_string)
        query_path = resolve_query_path("db_size", db_type)
        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open(query_path).read())
            result = conn.execute(query, {"db_name": db_name})

            logger.info("Log query path: "+query_path)
            # Convert Row objects to dictionaries
            rows = []
            for row in result:
                rows.append(dict(row._mapping))  # Sử dụng _mapping

            logger.info("DB Size query executed successfully")
            return rows
    except Exception as e:
        logger.error(f"Error checking database size: {e}")


@app.post("/log_space")
async def check_log_space(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        db_type = detect_db_type(connection_string)
        query_path = resolve_query_path("log_space", db_type)
        engine = create_engine(connection_string)
        with engine.connect() as conn:
            query = text(open(query_path).read())
            result = conn.execute(query)
            
            logger.info("Log query path: "+query_path)
            # Convert Row objects to dictionaries
            rows = []
            for row in result:
                rows.append(dict(row._mapping))  # Sử dụng _mapping
            
            logger.info("Log Space query executed successfully")
            return rows
            
    except Exception as e:
        logger.error(f"Error checking log space: {e}")
        return {"error": str(e)}


@app.post("/blocking_sessions")
async def check_blocking_sessions(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}
            
        db_type = detect_db_type(connection_string)
        query_path = resolve_query_path("blocking_session", db_type)
        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open(query_path).read())
            result = conn.execute(query)
            
            logger.info("Log query path: "+query_path)
            # Convert Row objects to dictionaries
            rows = []
            for row in result:
                rows.append(dict(row._mapping))

            logger.info("Blocking Sessions query executed successfully")
            return rows
    except Exception as e:
        logger.error(f"Error checking blocking sessions: {e}")


@app.post("/index_frag")
async def check_index_fragmentation(request: Request):

    try:
        data = await request.json()
        connection_string = data.get("connection_string")
        db_name = data.get("db_name")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        db_type = detect_db_type(connection_string)
        query_path = resolve_query_path("index_frag", db_type)
        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open(query_path).read())
            result = conn.execute(query, {"db_name": db_name})

            logger.info("Log query path: "+query_path)
            # Convert Row objects to dictionaries
            rows = []
            for row in result:
                rows.append(dict(row._mapping))

            logger.info("Index Fragmentation query executed successfully")
            return rows
    except Exception as e:
        logger.error(f"Error checking index frag: {e}")

        
@app.post("/change_pwd")
async def change_password(request: Request):

    try:
        data = await request.json()
        connection_string = data.get("connection_string")
        login_name = data.get("login_name")
        new_password = data.get("new_password")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        db_type = detect_db_type(connection_string)
        query_path = resolve_query_path("change_pwd", db_type)
        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open(query_path).read())
            result = conn.execute(query, {"login_name": login_name, "password": new_password})

            logger.info("Log query path: "+query_path)
            # Convert Row objects to dictionaries
            rows = []
            for row in result:
                rows.append(dict(row._mapping))

            logger.info("Change Password query executed successfully")
            return rows
    except Exception as e:
        logger.error(f"Error changing password: {e}")