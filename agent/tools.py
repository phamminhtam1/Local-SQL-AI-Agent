import re
import os
import json
from langchain.tools import BaseTool
from langchain_community.utilities.sql_database import SQLDatabase

TOOL_METADATA = {
    "list_tables": {
        "name": "list_tables",
        "description": "List all tables in the database with schema and sample rows",
        "use_case": "Use when user asks for general table information, schema, or structure"
    },
    "query_sql": {
        "name": "query_sql", 
        "description": "Execute SQL SELECT queries to get specific data",
        "use_case": "Use when user asks for specific data, calculations, rankings, or complex queries"
    },
    "list_tools": {
        "name": "list_tools",
        "description": "List all available tools with their descriptions and use case",
        "use_case": "Use when user asks for available tools or tool descriptions"
    }
}

DB_URI = os.getenv("DB_URI")
# Ensure UTF-8 encoding for MySQL connection
if DB_URI and "mysql" in DB_URI.lower():
    if "?" not in DB_URI:
        DB_URI += "?charset=utf8mb4"
    elif "charset" not in DB_URI:
        DB_URI += "&charset=utf8mb4"

db = SQLDatabase.from_uri(DB_URI)

class ListTablesTool(BaseTool):
    name: str = "list_tables"
    description: str = "List all tables in the DB with schema and sample rows"

    def _run(self, query: str = "") -> str:
        return db.get_table_info()

    async def _arun(self, query: str = "") -> str:
        return self._run(query)

class QuerySQLTool(BaseTool):
    name: str = "query_sql"
    description: str = "Run safe SELECT queries"

    def _run(self, query: str) -> str:
        statements = [stmt.strip() for stmt in query.split(';') if stmt.strip()]
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
    
    async def _arun(self, query: str) -> str:
        return self._run(query)

class ListToolsTool(BaseTool):
    name: str = "list_tools"
    description: str = "List all available tools with their descriptions and use case"

    def _run(self, query: str = "") -> str:
        return json.dumps(TOOL_METADATA, indent=2)

    async def _arun(self, query: str = "") -> str:
        return self._run(query)


list_tables_tool = ListTablesTool()
query_sql_tool = QuerySQLTool()
list_tools_tool = ListToolsTool()

