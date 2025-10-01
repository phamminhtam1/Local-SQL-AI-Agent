import re
import os
from langchain.tools import BaseTool
from langchain_community.utilities.sql_database import SQLDatabase

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

list_tables_tool = ListTablesTool()
query_sql_tool = QuerySQLTool()

