from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import httpx, logging, json
from datetime import datetime

from proxy_service import UniversalProxyService
from models import DatabaseType, ProxyRequest
from settings import PROXY_TARGETS

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Universal API Proxy",
    description="A flexible API proxy service with dual mode support (self-forwarding and external forwarding)",
    version="1.0.0"
)

# Middleware
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

# HTTP client với timeout và retry
async def get_http_client():
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
    )

# Dependency để lấy HTTP client
async def get_client():
    async with get_http_client() as client:
        yield client

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

# Universal Proxy Endpoint với Flexible Arguments
@app.api_route("/proxy/{target}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"], include_in_schema=False)
async def universal_proxy(
    target: str,
    path: str,
    request: Request,
    client: httpx.AsyncClient = Depends(get_client)
):
    """
    Universal Proxy với Flexible Arguments:
    1. Nhận UUID và các arguments khác từ client
    2. Gọi Vault API để lấy DB config
    3. Tạo connection string
    4. Quyết định mode (self hoặc external)
    5. Xử lý và trả về kết quả
    """
    return await proxy_service.execute_universal_flow(request, client)

# Endpoint để lấy danh sách targets
@app.get("/targets")
async def get_targets():
    """Get available proxy targets"""
    return {
        "targets": PROXY_TARGETS,
        "count": len(PROXY_TARGETS)
    }

# Endpoint để lấy danh sách supported databases
@app.get("/databases")
async def get_supported_databases():
    """Get supported database types"""
    return {
        "supported_databases": [db.value for db in DatabaseType],
        "count": len(DatabaseType)
    }

# Middleware để log requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
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
    Nhận tất cả arguments trong request body
    """    
    # Tạo body từ request_data
    body = json.dumps(request_data.model_dump()).encode()
    
    # Tạo mock request
    mock_request = Request({
        "type": "http", 
        "method": "POST", 
        "url": "/proxy/flexible",
        "headers": [],
        "query_string": b""
    })
    
    # Set body cho request
    mock_request._body = body
    
    return await proxy_service.execute_universal_flow(mock_request, client)