# Vault Service - Hướng dẫn sử dụng

## 📋 Tổng quan

Vault service cung cấp khả năng lưu trữ và quản lý secrets (mật khẩu, API keys, database configurations) một cách an toàn. Vault hoạt động độc lập và cung cấp REST API để:

- **Lưu trữ database configurations** cho từng user
- **Quản lý secrets** một cách tập trung
- **Cung cấp API endpoints** để truy cập secrets
- **Bảo mật cao** với encryption và access control

## 🏗️ Kiến trúc

```
Client → Vault API → Encrypted Storage → Response
```

### Flow hoạt động:
1. **Client gửi request** với token authentication
2. **Vault xác thực** token và kiểm tra permissions
3. **Vault truy xuất** secret từ encrypted storage
4. **Vault trả về** secret data cho client

## 🚀 Cài đặt và chạy

### 1. Environment Variables
```bash
# .env file (thư mục gốc)
VAULT_TOKEN=your-vault-token
VAULT_PORT=8200
VAULT_API_PORT=8000
```

### 2. Chạy Vault Service
```bash
# Chạy từ thư mục vault/
cd vault/
docker-compose up --build -d

# Hoặc chạy từ thư mục gốc
docker-compose -f vault/docker-compose.yml up --build -d
```

### 3. Kiểm tra Vault hoạt động
```bash
# Health check
curl http://localhost:8200/v1/sys/health

# Kiểm tra token
curl -H "X-Vault-Token: your-vault-token" http://localhost:8200/v1/auth/token/lookup-self
```

## 📡 Vault API Endpoints

### 1. Health Check
```bash
GET /v1/sys/health
```

**Response:**
```json
{
  "initialized": true,
  "sealed": false,
  "standby": false,
  "performance_standby": false,
  "replication_performance_mode": "disabled",
  "replication_dr_mode": "disabled",
  "server_time_utc": 1640995200,
  "version": "1.13.3",
  "cluster_name": "vault-cluster-abc123",
  "cluster_id": "cluster-abc123"
}
```

### 2. Token Lookup
```bash
GET /v1/auth/token/lookup-self
```

**Headers:**
```
X-Vault-Token: your-vault-token
```

**Response:**
```json
{
  "data": {
    "accessor": "accessor-abc123",
    "creation_time": 1640995200,
    "creation_ttl": 0,
    "display_name": "token",
    "entity_id": "entity-abc123",
    "expire_time": null,
    "explicit_max_ttl": 0,
    "id": "your-vault-token",
    "issue_time": "2024-01-01T00:00:00Z",
    "meta": null,
    "num_uses": 0,
    "orphan": true,
    "path": "auth/token/create",
    "policies": ["root"],
    "renewable": true,
    "ttl": 0,
    "type": "service"
  }
}
```

### 3. Lưu trữ Database Config
```bash
POST /secrets
```

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "user_id": "user-123",
  "name": "string",
  "data": {
    "type": "mysql",
    "host": "mysql_db",
    "port": 3306,
    "database": "user_db",
    "username": "user",
    "password": "password",
    "additional_params": {
      "charset": "utf8mb4",
      "ssl": true,
      "timeout": 30
    }
  }
}
```

**Response:**
```json
{
  "id": "secret-123",
  "user_id": "user-123",
  "name": "string",
  "data": {
    "type": "mysql",
    "host": "mysql_db",
    "port": 3306,
    "database": "user_db",
    "username": "user",
    "password": "password"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### 4. Lấy Database Config
```bash
GET /secrets?user_id={uuid}&include_values=true&name={username}
```

**Headers:**
```
Content-Type: application/json
```

**Response:**
```json
[
  {
    "id": "secret-123",
    "user_id": "user-123",
    "name": "string",
    "data": {
      "type": "mysql",
      "host": "mysql_db",
      "port": 3306,
      "database": "user_db",
      "username": "user",
      "password": "password",
      "additional_params": {
        "charset": "utf8mb4",
        "ssl": true,
        "timeout": 30
      }
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### 5. List Secrets
```bash
GET /secrets?user_id={uuid}
```

**Headers:**
```
Content-Type: application/json
```

**Response:**
```json
[
  {
    "id": "secret-123",
    "user_id": "user-123",
    "name": "string",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  {
    "id": "secret-456",
    "user_id": "user-123",
    "name": "api-keys",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### 6. Delete Secret
```bash
DELETE /secrets/{secret_id}
```

**Headers:**
```
Content-Type: application/json
```

**Response:**
```json
{
  "message": "Secret deleted successfully",
  "deleted_at": "2024-01-01T00:00:00Z"
}
```

## 🎯 Cách sử dụng

## 📋 Phần 1: Sử dụng Vault riêng biệt

### 1. Khởi tạo Vault
```bash
# 1. Start Vault service
docker-compose -f vault/docker-compose.yml up -d

# 2. Kiểm tra Vault đã sẵn sàng
curl http://localhost:8200/v1/sys/health

# 3. Set Vault token (từ .env file)
export VAULT_TOKEN="your-vault-token"
```

### 2. Lưu trữ Database Config cho User
```bash
# Lưu config cho user-123
curl -X POST http://localhost:8000/secrets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "name": "string",
    "data": {
      "type": "mysql",
      "host": "mysql_db",
      "port": 3306,
      "database": "user_123_db",
      "username": "user_123",
      "password": "secure_password_123"
    }
  }'
```

### 3. Lấy Database Config
```bash
# Lấy config cho user-123
curl -X GET "http://localhost:8000/secrets?user_id=user-123&include_values=true&name=string" \
  -H "Content-Type: application/json"
```

### 4. List Secrets
```bash
# Liệt kê tất cả secrets cho user
curl -X GET "http://localhost:8000/secrets?user_id=user-123" \
  -H "Content-Type: application/json"
```

### 5. Delete Secret
```bash
# Xóa secret
curl -X DELETE http://localhost:8000/secrets/secret-123 \
  -H "Content-Type: application/json"
```

## 🔗 Phần 2: Kết hợp Vault với API Proxy

### 1. Kiến trúc tích hợp
```
Client → API Proxy → Vault API → DB Config → Connection String → Forward to API → Response
```

### 2. Setup tích hợp
```bash
# 1. Start cả Vault và API Proxy
docker-compose up --build -d

# 2. Kiểm tra Vault
curl http://localhost:8200/v1/sys/health

# 3. Kiểm tra API Proxy
curl http://localhost:8888/health
```

### 3. Lưu DB Config vào Vault (cho API Proxy sử dụng)
```bash
# Lưu config cho user-123 (API Proxy sẽ tự động lấy)
curl -X POST http://localhost:8000/secrets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "name": "string",
    "data": {
      "type": "mysql",
      "host": "mysql_db",
      "port": 3306,
      "database": "user_123_db",
      "username": "user_123",
      "password": "secure_password_123"
    }
  }'
```

### 4. Sử dụng API Proxy với Vault integration
```bash
# API Proxy tự động gọi Vault để lấy DB config (Proxy CHỈ nhận JSON body)
curl -X POST http://localhost:8888/proxy/database/query \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "name": "john-doe",
    "sql": "SELECT * FROM users WHERE id = ?",
    "params": [123]
  }'
```

### 5. Flow hoạt động tích hợp
1. **Client gửi request** với UUID đến API Proxy
2. **API Proxy gọi Vault** để lấy DB config cho UUID
3. **Vault trả về config** (host, port, database, credentials)
4. **API Proxy tạo connection string** từ config
5. **API Proxy forward request** tới API endpoint với connection string
6. **API Proxy trả về response** từ API cho client

### 6. API Proxy Endpoints với Vault integration

#### Health Check
```bash
GET http://localhost:8888/health
```

#### Database Query (qua Proxy)
```bash
POST http://localhost:8888/proxy/database/query
```

**Request (Proxy yêu cầu body):**
```json
{
  "uuid": "user-123",
  "name": "john-doe",
  "sql": "SELECT * FROM users WHERE status = ?",
  "params": ["active"]
}
```

**Headers:**
```
Content-Type: application/json
```

**Response:**
```json
{
  "uuid": "user-123",
  "connection_string": "mysql+pymysql://user_123:secure_password_123@mysql_db:3306/user_123_db",
  "result": {
    "sql": "SELECT * FROM users WHERE status = ?",
    "params": ["active"],
    "result": "Query executed successfully",
    "rows_affected": 5,
    "data": [...]
  },
  "timestamp": "2024-01-01T00:00:00",
  "status": "success"
}
```

#### Database Health Check (qua Proxy, Proxy chỉ nhận body)
```bash
curl -X GET http://localhost:8888/proxy/database/health \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "name": "john-doe"
  }'
```

#### Get Database Tables (qua Proxy, dùng body)
```bash
curl -X GET http://localhost:8888/proxy/database/tables \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "name": "john-doe"
  }'
```

### 7. Lợi ích của tích hợp
- **Tự động hóa**: API Proxy tự động lấy DB config từ Vault
- **Bảo mật**: Credentials được lưu trữ an toàn trong Vault
- **Linh hoạt**: Hỗ trợ nhiều loại database
- **Centralized**: Quản lý tập trung tất cả DB configs
- **Dynamic**: Không cần restart khi thay đổi config

## 🗄️ Database Configurations

### Supported Database Types
- **MySQL**: `mysql+pymysql://user:pass@host:port/db`
- **PostgreSQL**: `postgresql://user:pass@host:port/db`
- **MongoDB**: `mongodb://user:pass@host:port/db`
- **Redis**: `redis://:pass@host:port/db`
- **SQLite**: `sqlite:///path/to/db.db`
- **Oracle**: `oracle://user:pass@host:port/db`
- **SQL Server**: `mssql+pyodbc://user:pass@host:port/db`

### Config Format
```json
{
  "type": "mysql",
  "host": "database-server.com",
  "port": 3306,
  "database": "user_database",
  "username": "db_user",
  "password": "secure_password",
  "additional_params": {
    "charset": "utf8mb4",
    "ssl": true,
    "timeout": 30
  }
}
```

## 🔧 Configuration

### Environment Variables
```bash
# Vault Configuration
VAULT_TOKEN=your-secure-token
VAULT_PORT=8200
VAULT_API_PORT=8000

# Vault Service URLs
VAULT_SERVICE_URL=http://host.docker.internal:8000
```

### Docker Compose
```yaml
version: '3.8'

services:
  vault:
    image: vault:1.13.3
    container_name: vault
    cap_add:
      - IPC_LOCK
    env_file:
      - ../.env  # Trỏ đến .env ở thư mục gốc
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: ${VAULT_TOKEN}
      VAULT_DEV_LISTEN_ADDRESS: "0.0.0.0:8200"
    ports:
      - "${VAULT_PORT}:8200"
    command: server -dev
    restart: unless-stopped
    networks:
      - vault-network

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: vault-app
    env_file:
      - ../.env  # Trỏ đến .env ở thư mục gốc
    ports:
      - "${VAULT_API_PORT}:8000"
    depends_on:
      - vault
    restart: unless-stopped
    networks:
      - vault-network

volumes:
  vault-data:

networks:
  vault-network:
    driver: bridge
```

## 🐛 Debugging

### 1. Vault Logs
```bash
# Xem logs Vault
docker-compose -f vault/docker-compose.yml logs -f vault

# Hoặc
docker logs vault
```

### 2. Vault Status
```bash
# Kiểm tra Vault status
curl http://localhost:8200/v1/sys/health

# Kiểm tra token
curl -H "X-Vault-Token: your-token" http://localhost:8200/v1/auth/token/lookup-self
```

### 3. Test Secret Operations
```bash
# Test lưu secret
curl -X POST http://localhost:8000/secrets \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test",
    "name": "string",
    "data": {
      "type": "mysql",
      "host": "localhost",
      "port": 3306,
      "database": "test",
      "username": "test",
      "password": "test"
    }
  }'

# Test lấy secret
curl -X GET "http://localhost:8000/secrets?user_id=test&include_values=true&name=string" \
  -H "Content-Type: application/json"
```

## 📝 Examples

### 1. Setup Database Config cho User
```bash
#!/bin/bash

# User UUID
USER_UUID="user-12345"
VAULT_URL="http://localhost:8000"

# Database config
DB_CONFIG='{
  "user_id": "user-12345",
  "name": "string",
  "data": {
    "type": "mysql",
    "host": "mysql_db",
    "port": 3306,
    "database": "user_12345_db",
    "username": "user_12345",
    "password": "secure_password_12345",
    "additional_params": {
      "charset": "utf8mb4",
      "ssl": true,
      "timeout": 30
    }
  }
}'

# Lưu config vào Vault
curl -X POST "${VAULT_URL}/secrets" \
  -H "Content-Type: application/json" \
  -d "${DB_CONFIG}"

echo "Database config saved for user: ${USER_UUID}"
```

### 2. Test với API Proxy
```bash
#!/bin/bash

# Test API Proxy với Vault integration (body JSON)
curl -X GET http://localhost:8888/proxy/database/health \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-12345",
    "name": "john-doe"
  }'
```

### 3. Bulk Setup cho nhiều Users
```bash
#!/bin/bash

# Danh sách users
USERS=("user-001" "user-002" "user-003")
VAULT_URL="http://localhost:8000"

for user in "${USERS[@]}"; do
  echo "Setting up config for user: $user"
  
  # Tạo config cho mỗi user
  DB_CONFIG='{
    "user_id": "'${user}'",
    "name": "string",
    "data": {
      "type": "mysql",
      "host": "mysql_db",
      "port": 3306,
      "database": "'${user}'_db",
      "username": "'${user}'",
      "password": "password_'${user}'"
    }
  }'
  
  # Lưu vào Vault
  curl -X POST "${VAULT_URL}/secrets" \
    -H "Content-Type: application/json" \
    -d "${DB_CONFIG}"
  
  echo "Config saved for $user"
done
```

## 🚨 Error Handling

### Common Errors
- **403 Forbidden**: Invalid Vault token
- **404 Not Found**: Secret path not found
- **500 Internal Server Error**: Vault service error
- **503 Service Unavailable**: Vault sealed or unavailable

### Error Response Format
```json
{
  "errors": [
    "permission denied"
  ]
}
```

## 🔒 Security

### Token Management
- **Root Token**: Chỉ dùng cho development
- **Service Token**: Tạo token riêng cho production
- **Token Rotation**: Thay đổi token định kỳ

### Secret Management
- **Encryption**: Tất cả secrets được mã hóa
- **Access Control**: Kiểm soát quyền truy cập
- **Audit Logging**: Ghi log tất cả operations

## 📈 Performance

### Connection Pooling
- Vault client với connection pooling
- Timeout configuration (30s default)
- Retry mechanism cho failed requests

### Monitoring
- Request/response logging
- Performance metrics
- Error tracking

## 🤝 Best Practices

### 1. Secret Naming Convention
```
/v1/secret/data/{user-uuid}/db-config
/v1/secret/data/{user-uuid}/api-keys
/v1/secret/data/{user-uuid}/certificates
```

### 2. Token Management
```bash
# Tạo token mới
vault token create -policy=read-only

# Revoke token
vault token revoke <token>
```

### 3. Backup và Recovery
```bash
# Backup Vault data
docker exec vault vault operator raft snapshot save /tmp/vault-backup.snap

# Restore từ backup
docker exec vault vault operator raft snapshot restore /tmp/vault-backup.snap
```

## 📄 License

MIT License - See LICENSE file for details.
