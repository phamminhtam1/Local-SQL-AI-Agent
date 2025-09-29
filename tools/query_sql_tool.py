import re
from langchain.tools import BaseTool
from langchain_community.utilities.sql_database import SQLDatabase
from typing import Optional

class SafeQuerySQLTool(BaseTool):
    name: str = "query_sql_select_only"
    description: str = (
        "Execute a SQL query that MUST start with SELECT and return the results as text."
    )
    db: Optional[SQLDatabase] = None

    def __init__(self, db: SQLDatabase):
        super().__init__(db=db)

    def _run(self, query: str) -> str:
        if not re.match(r"^\s*select\b", query, re.IGNORECASE):
            return "Refused: Only SELECT statements are allowed."
        try:
            cleaned = query.strip().strip('"').strip("'")
            return self.db.run(cleaned)
        except Exception as e:
            return f"SQL error: {e}"

    async def _arun(self, query: str) -> str:
        return self._run(query)
