## Universal API Proxy - Hướng dẫn sử dụng

### Tổng quan

- Proxy chỉ nhận request qua JSON body cho TẤT CẢ method (GET/POST/PUT/PATCH/DELETE).
- Bắt buộc có các trường trong body: `uuid` và `name`.
- Tự động:
  - Lấy DB config từ Vault theo `uuid` (nếu tồn tại)
  - Tạo `connection_string` tương ứng DB và chèn vào body trước khi forward
  - Fallback khi downstream không chấp nhận GET/PUT/PATCH/DELETE có body: retry bằng POST + `X-HTTP-Method-Override`

### Kiến trúc

```
Client (JSON body) → Universal Proxy → Vault (DB Config) → Forward to API → Response
```

### Luồng xử lý
- Nhận body JSON (bắt buộc `uuid`, `name`)
- Gọi Vault để lấy DB config theo `uuid` (nếu có)
- Tạo `connection_string` và chèn vào body
- Forward request đến endpoint đích; fallback nếu bị từ chối body
- Trả về response từ service đích

## Cài đặt và chạy

### Environment Variables
```bash
# .env
VAULT_SERVICE_URL=http://host.docker.internal:8000
API_BASE_URL=http://localhost:8888
```

### Chạy development
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8888 --reload
```

## API Endpoints

### Health Check
- Method: GET
- URL: `/health`
- Không yêu cầu body.

### Supported Databases
- Method: GET
- URL: `/databases`
- Không yêu cầu body.

### Universal Proxy
- Method: GET/POST/PUT/PATCH/DELETE
- URL: `/proxy/{path:path}`
- Yêu cầu body JSON chứa tối thiểu:
```json
{
  "uuid": "user-uuid",
  "name": "user-name"
}
```
- Proxy sẽ tự chèn `connection_string` (nếu có) trước khi forward.

Ví dụ:
```bash
# GET với body (proxy sẽ forward body; nếu downstream không chấp nhận, proxy tự retry POST + override)
curl -X GET http://localhost:8888/proxy/log_space \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "name": "john-doe"
  }'

# POST với body cho truy vấn DB
curl -X POST http://localhost:8888/proxy/database/query \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "name": "john-doe",
    "sql": "SELECT * FROM users LIMIT 10",
    "params": []
  }'
```

### Headers và fallback
- Proxy chuẩn hóa:
  - `Content-Type: application/json`
  - `Accept: application/json`
- Khi fallback: thêm `X-HTTP-Method-Override: <ORIGINAL_METHOD>`

### Endpoint ví dụ nội bộ: Log Space
- Method: POST
- URL: `/log_space`
- Gọi trực tiếp endpoint này cần có body dạng:
```json
{
  "connection_string": "mysql+pymysql://user:pass@host:3306/db"
}
```
- Nếu gọi thông qua proxy (khuyến nghị):
```bash
curl -X GET http://localhost:8888/proxy/log_space \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "name": "john-doe"
  }'
```
Proxy sẽ tự chèn `connection_string` vào body trước khi forward đến `/log_space`.

## Vault Integration
- Dựa trên `uuid`, proxy gọi Vault để lấy DB config và xây `connection_string`.
- Ví dụ cấu hình từ Vault:
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

## Connection String (tham khảo)
- MySQL: `mysql+pymysql://user:pass@host:3306/db`
- PostgreSQL: `postgresql+psycopg2://user:pass@host:5432/db`
- MongoDB: `mongodb://user:pass@host:27017/db`
- Redis: `redis://:pass@host:6379/0`
- SQLite: `sqlite:///path/to/db.db`
- Oracle: `oracle+cx_oracle://user:pass@host:1521/db`
- SQL Server: `mssql+pyodbc://user:pass@host:1433/db?driver=ODBC+Driver+17+for+SQL+Server`

Ghi chú:
- Khi dùng `URL.create` của SQLAlchemy, không cần tự encode credentials; fallback string sẽ được encode bằng `quote_plus` khi cần.
- Với MySQL dùng `caching_sha2_password/sha256_password`, cần `cryptography` hoặc dùng driver `mysql+mysqlconnector`.

## Error Handling
- 400: Thiếu `uuid` hoặc `name` trong body
- 405/411/415/501: Fallback POST + `X-HTTP-Method-Override`
- 500: Lỗi nội bộ (Vault/DB hoặc xử lý)

## Ví dụ nhanh
```bash
curl -X PATCH http://localhost:8888/proxy/database/update \
  -H "Content-Type: application/json" \
  -d '{
    "uuid": "user-123",
    "name": "john-doe",
    "sql": "UPDATE users SET status = ? WHERE id = ?",
    "params": ["active", 1]
  }'
```

## Debugging
```bash
curl http://localhost:8888/health
```

## License
MIT License - See LICENSE