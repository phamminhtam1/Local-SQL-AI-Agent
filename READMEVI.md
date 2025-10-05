# Local SQL AI Agent - Hệ thống Điều phối Đa Agent

Hệ thống AI Agent đa tác nhân với kiến trúc Orchestrator, hỗ trợ xử lý truy vấn SQL và tìm kiếm thông tin thông minh.

## 🏗️ Kiến trúc hệ thống

### Orchestrator Pattern
Hệ thống sử dụng mô hình Orchestrator để điều phối các agent chuyên biệt:

```
Query → Intent Classification → Orchestrator → Specialized Agents → Aggregation → Verification → Response
```

### Các thành phần chính:

1. **Intent Classifier**: Phân loại ý định người dùng (DB vs Non-DB)
2. **Orchestrator**: Điều phối và quản lý luồng xử lý
3. **DB Agent**: Xử lý các truy vấn cơ sở dữ liệu
4. **Search Agent**: Xử lý tìm kiếm và phân tích thông tin
5. **Verification Engine**: Xác minh và đánh giá kết quả
6. **LLM Tools**: Tạo câu trả lời cuối cùng

## 📁 Cấu trúc thư mục

```
Local-SQL-AI-Agent/
├── client/                    # Client application (Streamlit UI + LangGraph)
│   ├── Dockerfile             # Client Docker configuration
│   ├── requirements.txt       # Client dependencies
│   ├── ui.py                  # Streamlit UI interface
│   ├── app.py                 # LangGraph application
│   ├── orchestrator.py        # Orchestrator logic
│   ├── verify_answer.py       # Answer verification
│   ├── mcp_client.py          # MCP client communication
│   └── agent/                 # Agent implementations
│       ├── node.py            # Agent nodes
│       ├── routers.py         # Routing logic
│       └── state.py           # State management
├── server/                    # Server application (MCP Server)
│   ├── Dockerfile             # Server Docker configuration
│   ├── requirements.txt       # Server dependencies
│   └── mcp_server.py          # MCP server with DB tools
├── docker-compose.yml         # Multi-container orchestration
├── init.sql                   # Database initialization
├── README.md                  # English version
└── READMEVI.md                # Vietnamese version
```

## 🚀 Hướng dẫn chạy

### 1. Chuẩn bị môi trường

```bash
# Clone repository
git clone <repository-url>
cd Local-SQL-AI-Agent

# Copy file environment
cp env.example .env
```

### 2. Cấu hình biến môi trường

Chỉnh sửa file `.env`:

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
MYSQL_ROOT_PASSWORD=root_password
MYSQL_DATABASE=be_laravel
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password
DB_HOST=mysql
DB_PORT=3306
DB_DRIVER=mysql+pymysql

# Server Ports
STREAMLIT_SERVER_PORT=8501
MCP_DB_SERVER_PORT=8001
MCP_SEARCH_SERVER_PORT=8002
MCP_DB_SERVER_URL=http://mcp_server:8001
MCP_SEARCH_SERVER_URL=http://mcp_server:8002
```

### 3. Chạy hệ thống

```bash
# Khởi động tất cả services
docker-compose up -d

# Xem logs
docker-compose logs -f

# Dừng hệ thống
docker-compose down
```

### 4. Truy cập ứng dụng

- **Streamlit UI**: http://localhost:8501
- **MCP DB Server**: http://localhost:8001
- **MCP Search Server**: http://localhost:8002

## 🛠️ Hướng dẫn phát triển

### Cấu trúc Agent

#### 1. Orchestrator (`client/orchestrator.py`)
- Điều phối luồng xử lý
- Quản lý state giữa các agent
- Xử lý async/await operations

#### 2. DB Agent
- Kết nối với MCP DB Server
- Thực hiện truy vấn SQL
- Kiểm tra health database

#### 3. Search Agent  
- Kết nối với MCP Search Server
- Tìm kiếm và phân tích thông tin
- Xử lý các truy vấn phức tạp

#### 4. Verification Engine
- Xác minh tính chính xác của kết quả
- Đánh giá chất lượng response
- Đề xuất cải thiện

### Workflow xử lý

```python
# 1. Intent Classification
intent = classify_intent(user_query)

# 2. Orchestrator Decision
if intent == "DB":
    # Route to DB Agent
    db_result = await db_agent.process(query)
    # Route to Search Agent  
    search_result = await search_agent.process(query)
    
    # 3. Aggregate Results
    aggregated = aggregate_results(db_result, search_result)
    
    # 4. Verify Answer
    verified = verify_answer(aggregated)
    
    # 5. Generate Final Response
    response = llm_tools.generate_answer(verified)
```

### Error Handling

Hệ thống hỗ trợ xử lý lỗi thông minh:

```python
# Error Detection
error = detect_error(user_report)

# Orchestrator Error Handling
if error.type == "DB_BLOCK":
    # DB Agent: Check table health
    db_diagnosis = await db_agent.diagnose_table(error.table)
    
    # Search Agent: Find similar issues
    search_solution = await search_agent.find_solution(error.table)
    
    # Generate Solution
    solution = generate_solution(db_diagnosis, search_solution)
```

## 🔧 Development Commands

### Build individual services

```bash
# Build client
docker build -t langgraph-client ./client

# Build server  
docker build -t mcp-server ./server
```

### Run individual services

```bash
# Run client only
docker run -p 8501:8501 -e OPENAI_API_KEY=your_key langgraph-client

# Run server only
docker run -p 8001:8001 -e DB_URI=your_db_uri mcp-server
```

### Development mode

```bash
# Run with volume mounting for development
docker-compose -f docker-compose.dev.yml up
```

## 📊 Monitoring & Debugging

### Health Checks

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs client
docker-compose logs mcp_server
docker-compose logs mysql
```

### Database Connection

```bash
# Connect to MySQL
docker exec -it mysql_db mysql -u root -p

# Check database
SHOW DATABASES;
USE be_laravel;
SHOW TABLES;
```

## 🎯 Use Cases

1. **SQL Query Analysis**: Phân tích và tối ưu truy vấn SQL
2. **Database Health Monitoring**: Giám sát tình trạng database
3. **Error Diagnosis**: Chẩn đoán và giải quyết lỗi database
4. **Information Retrieval**: Tìm kiếm thông tin thông minh
5. **Automated Troubleshooting**: Tự động xử lý sự cố

## 🔒 Security

- MCP Server chạy trong container riêng biệt
- Database credentials được quản lý qua environment variables
- Chỉ cho phép SELECT queries (bảo mật dữ liệu)
- Network isolation giữa các services

## 📈 Performance

- **Async Processing**: Xử lý bất đồng bộ giữa các agent
- **Parallel Execution**: Chạy song song DB và Search agents
- **Caching**: Cache kết quả để tăng tốc độ
- **Load Balancing**: Cân bằng tải giữa các services

## 🤝 Contributing

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📝 License

MIT License - Xem file LICENSE để biết thêm chi tiết.
