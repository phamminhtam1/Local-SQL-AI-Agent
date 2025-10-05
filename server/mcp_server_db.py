import os
import re
from fastmcp import FastMCP
from langchain_community.utilities.sql_database import SQLDatabase
import logging

logger = logging.getLogger(__name__)

mcp = FastMCP("SQL Agent MCP Server")

DB_USER = os.environ.get('MYSQL_USER')
DB_PASSWORD = os.environ.get('MYSQL_PASSWORD')
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('MYSQL_DATABASE')
DB_DRIVER = os.environ.get('DB_DRIVER', 'pymysql')
DB_URI = f"mysql+{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

if DB_URI and "mysql" in DB_URI.lower():
    if "?" not in DB_URI:
        DB_URI += "?charset=utf8mb4"
    elif "charset" not in DB_URI:
        DB_URI += "&charset=utf8mb4"
logger.info(f"DB_URI: {DB_URI}")
db = SQLDatabase.from_uri(DB_URI)

@mcp.tool
def list_tables() -> str:
    """name:List all tables in the database with schema
       description:List all tables in the database with schema
    """
    return db.get_table_info()

@mcp.tool
def query_sql(sql: str) -> str:
    """name:Execute SQL SELECT queries to get specific data
       description:Execute SQL SELECT queries to get specific data
    """
    statements = [stmt.strip() for stmt in sql.split(';') if stmt.strip()]
    if not statements:
        return "No valid SQL statements found"
    
    results = []
    for i, statement in enumerate(statements):
        if not re.match(r"^\s*select", statement, re.IGNORECASE):
            results.append(f"Statement {i+1} refused: Only SELECT allowed")
            continue
        try:
            result = db.run(statement)
            if isinstance(result, str):
                try:
                    result_str = result.encode('utf-8', errors='replace').decode('utf-8')
                except:
                    result_str = str(result)
            else:
                result_str = str(result)
            results.append(f"Query {i+1}: {statement}\nResult: {result_str}")
        except Exception as e:
            try:
                error_msg = str(e).encode('utf-8', errors='replace').decode('utf-8')
            except:
                error_msg = "Encoding error occurred"
            results.append(f"Query {i+1} failed: {error_msg}")
    
    return "\n\n".join(results)

