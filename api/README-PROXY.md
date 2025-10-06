# Universal API Proxy - Hướng dẫn sử dụng

## 📋 Tổng quan

Universal API Proxy là một service proxy linh hoạt hỗ trợ:
- **Request Forwarding**: Forward request tới API endpoints
- **Multi-Database**: MySQL, PostgreSQL, MongoDB, Redis, SQLite, Oracle, SQL Server
- **Vault Integration**: Tự động lấy database configuration (optional)
- **Flexible Arguments**: Hỗ trợ nhiều cách truyền dữ liệu

## 🏗️ Kiến trúc

```
Client Request → Universal Proxy → Vault (DB Config) → Forward to API → Response
```

### Flow xử lý:
1. **Nhận request** từ client
2. **Extract UUID** (optional) từ request
3. **Gọi Vault API** để lấy DB config (nếu có UUID)
4. **Tạo connection string** từ DB config (nếu có)
5. **Forward request** tới API endpoint với connection string
6. **Trả về response** từ API

## 🚀 Cài đặt và chạy

### 1. Environment Variables
```bash
# .env file
VAULT_SERVICE_URL=http://host.docker.internal:8000
API_BASE_URL=http://localhost:8888
```

### 2. Chạy với Docker
```bash
# Build và chạy
docker-compose up --build -d

# Hoặc chỉ chạy API service
docker-compose up api
```

### 3. Chạy development
```bash
# Install dependencies
pip install -r requirements.txt

# Chạy server
uvicorn main:app --host 0.0.0.0 --port 8888 --reload
```

## 📡 API Endpoints

### 1. Health Check
```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00",
  "targets": ["vault", "self"],
  "supported_databases": ["mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle", "sqlserver"],
  "modes": ["forward"],
  "supported_arguments": ["uuid", "connection_string"]
}
```

### 2. Get Supported Databases
```bash
GET /databases
```

**Response:**
```json
{
  "supported_databases": ["mysql", "postgresql", "mongodb", "redis", "sqlite", "oracle", "sqlserver"],
  "count": 7
}
```

### 3. Universal Flow (Forward Request)
```bash
/proxy/{path:path}
```

**Ví dụ:**
```bash
POST /proxy/database/query
POST /proxy/search/users
GET /proxy/database/health
```

## 🎯 Cách sử dụng

### 1. Request với UUID (có Vault integration)

#### Database Operations
```bash
curl -X POST http://localhost:8888/proxy/database/query \
  -H "Content-Type: application/json" \
  -H "X-User-UUID: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{
    "sql": "SELECT * FROM users WHERE id = ?",
    "params": [123]
  }'
```

#### Search Operations
```bash
curl -X POST http://localhost:8888/proxy/search/query \
  -H "Content-Type: application/json" \
  -H "X-User-UUID: 123e4567-e89b-12d3-a456-426614174000" \
  -d '{
    "query": "search term",
    "filters": {"category": "tech"}
  }'
```

### 2. Request không có UUID (forward trực tiếp)

```bash
curl -X POST http://localhost:8888/proxy/database/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users",
    "params": []
  }'
```

### 3. Sử dụng Query Parameters

```bash
curl -X GET "http://localhost:8888/proxy/database/health?uuid=123e4567-e89b-12d3-a456-426614174000"
```

## 🗄️ Database Support

### Supported Databases
- **MySQL**: `mysql+pymysql://user:pass@host:port/db`
- **PostgreSQL**: `postgresql://user:pass@host:port/db`
- **MongoDB**: `mongodb://user:pass@host:port/db`
- **Redis**: `redis://:pass@host:port/db`
- **SQLite**: `sqlite:///path/to/db.db`
- **Oracle**: `oracle://user:pass@host:port/db`
- **SQL Server**: `mssql+pyodbc://user:pass@host:port/db`

### Vault Configuration
Proxy tự động lấy DB config từ Vault:
```json
{
  "type": "mysql",
  "host": "localhost",
  "port": 3306,
  "database": "mydb",
  "username": "user",
  "password": "pass"
}
```

## 📊 Response Format

### Success Response
```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "connection_string": "mysql+pymysql://...",
  "result": {
    "sql": "SELECT * FROM users",
    "params": [123],
    "result": "Query executed successfully",
    "rows_affected": 1,
    "timestamp": "2024-01-01T00:00:00"
  },
  "timestamp": "2024-01-01T00:00:00",
  "status": "success"
}
```

### Error Response
```json
{
  "error": "Error message",
  "timestamp": "2024-01-01T00:00:00",
  "status": "failed"
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Vault Configuration
VAULT_SERVICE_URL=http://host.docker.internal:8000

# API Configuration
API_BASE_URL=http://localhost:8888

# Environment
ENVIRONMENT=development
```

### Docker Compose
```yaml
api:
  build: ./api
  container_name: api_proxy
  env_file:
    - ./.env
  environment:
    - VAULT_SERVICE_URL=http://host.docker.internal:8000
    - API_BASE_URL=http://localhost:8888
  ports:
    - "8888:8888"
  volumes:
    - ./api:/app
    - ./.env:/app/.env:ro
```

## 🐛 Debugging

### 1. Logs
```bash
# Xem logs
docker-compose logs -f api

# Hoặc
docker logs api_proxy
```

### 2. Health Check
```bash
# Kiểm tra health
curl http://localhost:8888/health
```

### 3. Test Vault Connection
```bash
# Test Vault
curl -X GET http://localhost:8888/proxy/vault/secrets?user_id=test&include_values=true&name=string
```

## 📝 Examples

### 1. Complete Database Query
```bash
curl -X POST http://localhost:8888/proxy/database/query \
  -H "Content-Type: application/json" \
  -H "X-User-UUID: user-123" \
  -d '{
    "sql": "SELECT u.*, p.name as profile_name FROM users u LEFT JOIN profiles p ON u.id = p.user_id WHERE u.status = ?",
    "params": ["active"]
  }'
```

### 2. Search with Filters
```bash
curl -X POST http://localhost:8888/proxy/search/query \
  -H "Content-Type: application/json" \
  -H "X-User-UUID: user-123" \
  -d '{
    "query": "machine learning",
    "filters": {
      "category": "technology",
      "date_range": "2024-01-01,2024-12-31",
      "language": "en"
    },
    "limit": 10,
    "offset": 0
  }'
```

### 3. Health Check
```bash
curl -X GET http://localhost:8888/proxy/database/health \
  -H "X-User-UUID: user-123"
```

## 🚨 Error Handling

### Common Errors
- **400 Bad Request**: Missing required parameters
- **404 Not Found**: API endpoint not found
- **500 Internal Server Error**: Vault connection failed or processing error
- **502 Bad Gateway**: API service unavailable
- **504 Gateway Timeout**: API service timeout

### Error Response Format
```json
{
  "error": "Detailed error message",
  "timestamp": "2024-01-01T00:00:00",
  "status": "failed",
  "error_code": "VAULT_CONNECTION_FAILED"
}
```

## 🔒 Security

### Headers Security
- `X-User-UUID`: Optional for Vault integration
- `X-Connection-String`: Automatically added by proxy
- `X-Database-Type`: Automatically added by proxy

### Vault Integration
- Automatic DB config retrieval (if UUID provided)
- Secure connection string generation
- Environment-based configuration

## 📈 Performance

### Connection Pooling
- HTTP client with connection pooling
- Timeout configuration (30s default)
- Retry mechanism for failed requests

### Monitoring
- Request/response logging
- Performance metrics
- Error tracking

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

MIT License - See LICENSE file for details.