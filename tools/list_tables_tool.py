from langchain.tools import BaseTool
from langchain_community.utilities.sql_database import SQLDatabase
from typing import Optional

class ListTablesTool(BaseTool):
    name: str = "list_tables"
    description: str = (
        "List all tables in the database with their schema and sample rows."
    )
    db: Optional[SQLDatabase] = None

    def __init__(self, db: SQLDatabase):
        super().__init__(db=db)

    def _run(self, query: str = "") -> str:
        """List all tables with their schema information"""
        try:
            # Get table names
            table_names = self.db.get_usable_table_names()
            
            if not table_names:
                return "No tables found in the database."
            
            result = "Available tables:\n\n"
            
            for table_name in table_names:
                result += f"Table: {table_name}\n"
                result += "-" * 50 + "\n"
                
                # Get table info (schema + sample rows)
                table_info = self.db.get_table_info([table_name])
                result += table_info + "\n\n"
            
            return result
            
        except Exception as e:
            return f"Error listing tables: {e}"

    async def _arun(self, query: str = "") -> str:
        return self._run(query)