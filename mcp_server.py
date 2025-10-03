import os
import re
from fastmcp import FastMCP
from langchain_community.utilities.sql_database import SQLDatabase

mcp = FastMCP("SQL Agent MCP Server")

DB_URI = os.getenv("DB_URI")
if DB_URI and "mysql" in DB_URI.lower():
    if "?" not in DB_URI:
        DB_URI += "?charset=utf8mb4"
    elif "charset" not in DB_URI:
        DB_URI += "&charset=utf8mb4"

db = SQLDatabase.from_uri(DB_URI)

@mcp.tool()
def list_tables() -> str:
    return db.get_table_info()

@mcp.tool()
def query_sql(sql: str) -> str:
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
