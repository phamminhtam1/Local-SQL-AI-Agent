from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import httpx, logging, json
from datetime import datetime

from services import UniversalProxyService
from models import DatabaseType, ProxyRequest
from settings import PROXY_TARGETS

# config logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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