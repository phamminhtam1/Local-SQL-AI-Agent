# LangGraph SQL Agent - Client/Server Architecture

This project has been restructured to separate client and server components with their own Docker containers.

## Project Structure

```
├── client/                 # Client application (Streamlit UI + LangGraph)
│   ├── Dockerfile         # Client Docker configuration
│   ├── requirements.txt   # Client dependencies
│   ├── ui.py             # Streamlit UI
│   ├── app.py            # LangGraph application
│   ├── mcp_client.py     # MCP client
│   └── agent/            # Agent logic
│       ├── node.py
│       ├── routers.py
│       └── state.py
├── server/               # Server application (MCP Server)
│   └── sever_db/        # Database server components
│       ├── Dockerfile   # Server Docker configuration
│       ├── requirements.txt  # Server dependencies
│       └── mcp_server.py    # MCP server
├── docker-compose.yml    # Multi-container orchestration
├── init.sql             # Database initialization
└── env.example          # Environment variables template
```

## Services

### Client Service

- **Container**: `langgraph_client`
- **Port**: 8501 (Streamlit UI)
- **Components**: Streamlit UI, LangGraph agent, MCP client
- **Dependencies**: MySQL, MCP Server

### Server Service

- **Container**: `mcp_server`
- **Port**: 8000 (MCP Server)
- **Components**: MCP server with database tools
- **Dependencies**: MySQL

### Database Service

- **Container**: `mysql_db`
- **Port**: 3306 (MySQL)
- **Database**: `be_laravel`

## Running the Application

1. **Copy environment file**:

   ```bash
   cp env.example .env
   ```

2. **Set your OpenAI API key in `.env`**:

   ```
   OPENAI_API_KEY=your_api_key_here
   ```

3. **Start all services**:

   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Streamlit UI: http://localhost:8501
   - MCP Server: http://localhost:8000

## Development

### Building individual services

**Client only**:

```bash
docker build -t langgraph-client ./client
```

**Server only**:

```bash
docker build -t mcp-server ./server
```

### Running individual services

**Client**:

```bash
docker run -p 8501:8501 -e OPENAI_API_KEY=your_key langgraph-client
```

**Server**:

```bash
docker run -p 8000:8000 -e DB_URI=your_db_uri mcp-server
```

## Architecture Benefits

- **Separation of Concerns**: Client and server have distinct responsibilities
- **Independent Scaling**: Scale client and server independently
- **Simplified Development**: Work on client or server in isolation
- **Clean Dependencies**: Each service has only the dependencies it needs
- **Better Security**: Server can be deployed with restricted access
