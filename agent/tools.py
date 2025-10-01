import re
import os
from langchain.tools import BaseTool
from langchain_community.utilities.sql_database import SQLDatabase

# DB connection (MySQL/Postgres tuỳ URI trong .env)
DB_URI = os.getenv("DB_URI")
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
        if not re.match(r"^\s*select", query, re.IGNORECASE):
            return "❌ Refused: Only SELECT allowed"
        return db.run(query)
    async def _arun(self, query: str) -> str:
        return self._run(query)

list_tables_tool = ListTablesTool()
query_sql_tool = QuerySQLTool()

