# Universal API Proxy - Hướng dẫn sử dụng

## 📋 Tổng quan

Universal API Proxy là một service proxy linh hoạt hỗ trợ:
- **Dual Mode**: Self-processing và External forwarding
- **Multi-Database**: MySQL, PostgreSQL, MongoDB, Redis, SQLite, Oracle, SQL Server
- **Vault Integration**: Tự động lấy database configuration
- **Flexible Arguments**: Hỗ trợ nhiều cách truyền dữ liệu

## 🏗️ Kiến trúc

```
Client Request → Universal Proxy → Vault (DB Config) → Processing/Forwarding → Response
```

### Flow xử lý:
1. **Nhận UUID và arguments** từ client
2. **Gọi Vault API** để lấy DB config
3. **Tạo connection string** từ DB config
4. **Quyết định mode** (self hoặc external)
5. **Xử lý và trả về kết quả**

## 🚀 Cài đặt và chạy

### 1. Environment Variables
```bash
# .env file
VAULT_SERVICE_URL=http://vault:8200
SELF_API_URL=http://localhost:8888
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
  "modes": ["self", "external"],
  "supported_arguments": ["uuid", "operation", "target", "path", "arguments", "metadata"]
}
```

### 2. Universal Proxy (Flexible)
```bash
POST /proxy/flexible
```

**Request Body:**
```json
{
  "uuid": "123e4567-e89b-12d3-a456-426614174000",
  "operation": "db",
  "target": "self",
  "path": "query",
  "arguments": {
    "sql": "SELECT * FROM users",
    "params": [123]
  },
  "metadata": {
    "user_id": "user123",
    "session_id": "session456"
  }
}
```

### 3. Traditional Proxy
```bash
GET /proxy/{target}/{path:path}
```

**Ví dụ:**
```bash
GET /proxy/self/db/query
GET /proxy/vault/v1/secret/data/test/db-config
```

## 🎯 Cách sử dụng

### 1. Self-Processing Mode

#### Database Operations
```bash
curl -X POST http://localhost:8888/proxy/flexible \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "operation": "db",
    "target": "self",
    "path": "query",
    "arguments": {
      "sql": "SELECT * FROM users WHERE id = ?",
      "params": [123]
    }
  }'
```

#### Search Operations
```bash
curl -X POST http://localhost:8888/proxy/flexible \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "operation": "search",
    "target": "self",
    "path": "query",
    "arguments": {
      "query": "search term",
      "filters": {"category": "tech"}
    }
  }'
```

#### Health Check
```bash
curl -X POST http://localhost:8888/proxy/flexible \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "123e4567-e89b-12d3-a456-426614174000",
    "operation": "health",
    "target": "self",
    "path": "status"
  }'
```

### 2. External Forwarding Mode

Hiện tại hệ thống chỉ còn 2 targets: `vault` và `self`. Vì vậy external forwarding chỉ áp dụng khi gọi trực tiếp tới Vault qua đường dẫn proxy (ví dụ ở phần Traditional Proxy).

### 3. Sử dụng Headers

```bash
curl -X GET http://localhost:8888/proxy/self/db/health \
  -H "X-User-UUID: 123e4567-e89b-12d3-a456-426614174000" \
  -H "X-Operation: health-check" \
  -H "X-Arguments: {\"timeout\": 30, \"retries\": 3}"
```

### 4. Sử dụng Query Parameters

```bash
curl -X GET "http://localhost:8888/proxy/self/db/health?uuid=123e4567-e89b-12d3-a456-426614174000&operation=health-check&timeout=30"
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
  "target": "self",
  "path": "query",
  "mode": "self",
  "arguments": {...},
  "metadata": {...},
  "db_config": {...},
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
VAULT_SERVICE_URL=http://vault:8200

# Self Configuration
SELF_API_URL=http://localhost:8888

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
    - VAULT_SERVICE_URL=http://vault:8200
    - SELF_API_URL=http://localhost:8888
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

# Kiểm tra targets
curl http://localhost:8888/targets

# Kiểm tra databases
curl http://localhost:8888/databases
```

### 3. Test Vault Connection
```bash
# Test Vault
curl -X GET http://localhost:8888/proxy/vault/v1/secret/data/test/db-config
```

## 📝 Examples

### 1. Complete Database Query
```bash
curl -X POST http://localhost:8888/proxy/flexible \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "operation": "db",
    "target": "self",
    "path": "query",
    "arguments": {
      "sql": "SELECT u.*, p.name as profile_name FROM users u LEFT JOIN profiles p ON u.id = p.user_id WHERE u.status = ?",
      "params": ["active"]
    },
    "metadata": {
      "user_id": "user-123",
      "request_id": "req-456",
      "source": "web"
    }
  }'
```

### 2. Search with Filters
```bash
curl -X POST http://localhost:8888/proxy/flexible \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "operation": "search",
    "target": "self",
    "path": "query",
    "arguments": {
      "query": "machine learning",
      "filters": {
        "category": "technology",
        "date_range": "2024-01-01,2024-12-31",
        "language": "en"
      },
      "limit": 10,
      "offset": 0
    },
    "metadata": {
      "user_id": "user-123",
      "search_session": "session-789"
    }
  }'
```

### 3. Health Check with Custom Arguments
```bash
curl -X POST http://localhost:8888/proxy/flexible \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "operation": "health",
    "target": "self",
    "path": "status",
    "arguments": {
      "check_database": true,
      "check_services": true,
      "timeout": 30
    },
    "metadata": {
      "user_id": "user-123",
      "check_type": "comprehensive"
    }
  }'
```

## 🚨 Error Handling

### Common Errors
- **400 Bad Request**: Missing UUID or invalid arguments
- **404 Not Found**: Target service not found
- **500 Internal Server Error**: Vault connection failed or processing error
- **502 Bad Gateway**: External service unavailable
- **504 Gateway Timeout**: External service timeout

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
- `X-User-UUID`: Required for authentication
- `X-Connection-String`: Automatically added by proxy
- `X-Database-Type`: Automatically added by proxy
- `X-Arguments`: JSON-encoded arguments
- `X-Metadata`: JSON-encoded metadata

### Vault Integration
- Automatic DB config retrieval
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
