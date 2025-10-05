# Local SQL AI Agent - Multi-Agent Orchestration System

A multi-agent AI system with Orchestrator architecture, supporting intelligent SQL query processing and information retrieval.

## 🏗️ System Architecture

### Orchestrator Pattern
The system uses an Orchestrator pattern to coordinate specialized agents:

```
Query → Intent Classification → Orchestrator → Specialized Agents → Aggregation → Verification → Response
```

### Key Components:

1. **Intent Classifier**: Classifies user intent (DB vs Non-DB)
2. **Orchestrator**: Coordinates and manages processing flow
3. **DB Agent**: Handles database queries
4. **Search Agent**: Handles search and information analysis
5. **Verification Engine**: Verifies and evaluates results
6. **LLM Tools**: Generates final responses

## 📁 Directory Structure

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
├── env.example                # Environment variables template
├── README.md                  # English version
└── READMEVI.md                # Vietnamese version
```

## 🚀 Getting Started

### 1. Environment Setup

```bash
# Clone repository
git clone <repository-url>
cd Local-SQL-AI-Agent

# Copy environment file
cp env.example .env
```

### 2. Environment Configuration

Edit the `.env` file:

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

### 3. Run the System

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the system
docker-compose down
```

### 4. Access the Application

- **Streamlit UI**: http://localhost:8501
- **MCP DB Server**: http://localhost:8001
- **MCP Search Server**: http://localhost:8002

## 🛠️ Development Guide

### Agent Structure

#### 1. Orchestrator (`client/orchestrator.py`)
- Coordinates processing flow
- Manages state between agents
- Handles async/await operations

#### 2. DB Agent
- Connects to MCP DB Server
- Executes SQL queries
- Checks database health

#### 3. Search Agent  
- Connects to MCP Search Server
- Searches and analyzes information
- Handles complex queries

#### 4. Verification Engine
- Verifies result accuracy
- Evaluates response quality
- Suggests improvements

### Processing Workflow

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

The system supports intelligent error handling:

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

1. **SQL Query Analysis**: Analyze and optimize SQL queries
2. **Database Health Monitoring**: Monitor database status
3. **Error Diagnosis**: Diagnose and resolve database errors
4. **Information Retrieval**: Intelligent information search
5. **Automated Troubleshooting**: Automatic issue resolution

## 🔒 Security

- MCP Server runs in isolated container
- Database credentials managed via environment variables
- Only SELECT queries allowed (data security)
- Network isolation between services

## 📈 Performance

- **Async Processing**: Asynchronous processing between agents
- **Parallel Execution**: Parallel execution of DB and Search agents
- **Caching**: Result caching for improved speed
- **Load Balancing**: Load balancing between services

## 🤝 Contributing

1. Fork repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## 📝 License

MIT License - See LICENSE file for more details.
