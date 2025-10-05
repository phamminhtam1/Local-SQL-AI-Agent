import logging
from fastmcp import FastMCP
import requests

db_mcp = FastMCP("My DB MCP Server")
API_BASE = "http:/localhost:8000" 

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@db_mcp.tool()
def check_health(uuid:str):
    """
        Checking if server is ready
    """
    try:
        payload = {
            "uuid": uuid,
        }
        resp = requests.post(f"{API_BASE}/health_check", json=payload)
        logger.info("Health check query executed successfully")

        return resp
    except Exception as e:
        logger.error(f"Error checking health: {e}")

@db_mcp.tool()
def check_db_size(uuid:str, db_name: str):
    """
        Checking db size
        Arg:
            db_name: Name of wanted database
        Return:
            dict: A JSON object with the following structure:
                {
                    "db_name": str,                  # Name of the database
                    "files": [                       # List of database files
                        {
                            "DatabaseName": str,     # Database name (redundant)
                            "FileName": str,         # Logical file name
                            "FileType": str,         # Type (ROWS / LOG)
                            "SizeMB": float          # File size in MB
                        },
                        ...
                    ],
                    "total_size_MB": float           # Total size in MB (sum of all files)
                }
            
    """
    try:
        payload = {
            "uuid": uuid,
            "db_name":db_name
        }
        resp = requests.post(f"{API_BASE}/db_size",payload = payload)
        logger.info("DB Size query executed successfully")

        return resp
    except Exception as e:
        logger.error(f"Error checking database size: {e}")

@db_mcp.tool()
def check_log_space(uuid:str):
    """
    Checking log space usage for all databases.

    Returns:
        list[dict]: A list of log usage information with the following structure:
            {
                "DatabaseName": str,            # Database name
                "LogSizeMB": float,             # Log file size in MB
                "LogSpaceUsedPercent": float,   # Percentage of log space used
                "Status": int                   # Status (usually 0 = OK)
            }
    """

    try:
        payload = {
            "uuid": uuid,
        }
        resp = requests.post(f"{API_BASE}/log_space",payload = payload)
        logger.info("Log Space query executed successfully")

        return resp
    except Exception as e:
        logger.error(f"Error checking log space: {e}")

@db_mcp.tool()
def check_blocking_sessions(uuid:str):
    """
    Checking blocking sessions in the database.

    Returns:
        list[dict]: A list of blocking session information with the following structure:
            {
                "BlockingSessionID": int,    # ID of the blocking session
                "WaitType": str,             # Type of wait (e.g., LCK_M_S, PAGEIOLATCH_SH, etc.)
                "WaitTime": int,             # Wait time in milliseconds
                "WaitResource": str,         # The resource being waited on (table, page, key, etc.)
                "BlockedSessionID": int,     # ID of the blocked session
                "DatabaseName": str          # Name of the database where the blocking occurs
            }
    """

    try:
        payload = {
            "uuid": uuid,
        }
        resp = requests.post(f"{API_BASE}/blocking_sessions",payload = payload)
        logger.info("Blocking Sessions query executed successfully")

        return resp
    except Exception as e:
        logger.error(f"Error checking blocking sessions: {e}")

@db_mcp.tool()
def check_index_fragmentation(uuid:str, db_name: str):
    """
    Checking index fragmentation in the database.
    Args:
        "db_name":str  Wanted database name
    Returns:
        list[dict]: A list of index fragmentation information with the following structure:
            {
                "TableName": str,                      # Name of the table
                "IndexName": str,                      # Name of the index
                "IndexType": str,                      # Index type description (e.g., CLUSTERED INDEX, NONCLUSTERED INDEX)
                "AvgFragmentationPercent": float       # Average fragmentation percentage
            }
    """
    try:
        payload = {
            "uuid": uuid,
            "db_name":db_name
        }
        resp = requests.post(f"{API_BASE}/index_frag",payload = payload)
        logger.info("Index Fragmentation query executed successfully")

        return resp
    except Exception as e:
        logger.error(f"Error checking index frag: {e}")

@db_mcp.tool()
def change_password(uuid:str, login_name: str, new_password: str):
    """
    Allow user to change password.

    Args:
        login_name (str): User login name.
        new_password (str): User's new password.

    Returns:
        None
    """
    try:
        payload = {
            "uuid": uuid,
            "login_name":login_name,
            "new_password":new_password
        }
        resp = requests.post(f"{API_BASE}/change_pwd",payload = payload)
        logger.info("Change Password query executed successfully")

        return resp
    except Exception as e:
        logger.error(f"Error changing password: {e}")

if __name__ == "__main__":
    db_mcp.run(transport='http', host='0.0.0.0', port=8002)