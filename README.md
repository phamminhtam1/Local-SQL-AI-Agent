# MySQL AI Agent

A Streamlit application that provides an AI-powered interface for querying MySQL databases using natural language.

## Features

- Natural language to SQL conversion using OpenAI GPT models
- Safe SQL execution (SELECT queries only)
- Database schema exploration
- Interactive Streamlit web interface

## Prerequisites

- Docker and Docker Compose
- OpenAI API key

## Quick Start with Docker

### 1. Clone and Setup

```bash
git clone <your-repo>
cd <your-repo>
```

### 2. Environment Configuration

Copy the example environment file and add your OpenAI API key:

```bash
cp env.example .env
```

Edit `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. Run with Docker Compose

```bash
# Start the application with MySQL database
docker-compose up -d

# View logs
docker-compose logs -f app
```

### 4. Access the Application

Open your browser and go to: http://localhost:8501

## Manual Docker Build

If you prefer to build manually:

```bash
# Build the Docker image
docker build -t mysql-ai-agent .

# Run the container (make sure MySQL is running separately)
docker run -p 8501:8501 \
  -e OPENAI_API_KEY=your_api_key \
  -e DB_URI=mysql+pymysql://user:password@host:3306/database \
  mysql-ai-agent
```

## Development

### Local Development Setup

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
cp env.example .env
# Edit .env with your actual values
```

3. Run the application:

```bash
streamlit run app.py
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-4o-mini)
- `DB_URI`: MySQL database connection string

### Database Connection

The application expects a MySQL database. You can:

1. Use the included MySQL container in docker-compose.yml
2. Connect to an existing MySQL instance
3. Use a cloud MySQL service

## Usage

1. Open the web interface at http://localhost:8501
2. Ask questions about your database in natural language
3. The AI will convert your questions to SQL and execute them safely

Example queries:

- "Show me all tables in the database"
- "List the top 10 users by registration date"
- "What are the most common product categories?"

## Security

- Only SELECT queries are allowed
- No write operations (INSERT, UPDATE, DELETE) are permitted
- Database credentials should be kept secure

## Troubleshooting

### Common Issues

1. **Database Connection Error**: Check your DB_URI and ensure MySQL is running
2. **OpenAI API Error**: Verify your API key is correct and has sufficient credits
3. **Port Already in Use**: Change the port in docker-compose.yml or stop other services

### Logs

```bash
# View application logs
docker-compose logs app

# View database logs
docker-compose logs mysql
```

## Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: This will delete your database data)
docker-compose down -v
```
