from sqlalchemy import text
from fastapi import FastAPI, Request
from sqlalchemy import create_engine

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

db_api = FastAPI()



@db_api.post('/health_check')
async def check_health(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open("queries/health_check.sql").read())
            result = conn.execute(query)

            logger.info("Health check query executed successfully")
            return [row for row in result]
    except Exception as e:
        logger.error(f"Error checking health: {e}")


@db_api.post("/db_size")
async def check_db_size(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")
        db_name = data.get("db_name")
        
        if not connection_string:
            return {"error": "Missing connection_string in payload"}
        
        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open("queries/db_size.sql").read())
            result = conn.execute(query, {"db_name": db_name})

            logger.info("DB Size query executed successfully")
            return [row for row in result]
    except Exception as e:
        logger.error(f"Error checking database size: {e}")


@db_api.post("/log_space")
async def check_log_space(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        engine = create_engine(connection_string)
        with engine.connect() as conn:
            query = text(open("queries/log_space.sql").read())
            result = conn.execute(query)
            
            # Chuyển đổi kết quả thành list of dicts
            columns = result.keys()
            rows = []
            for row in result:
                row_dict = {}
                for i, value in enumerate(row):
                    row_dict[columns[i]] = value
                rows.append(row_dict)
            
            logger.info("Log Space query executed successfully")
            return rows  # Trả về list of dicts thay vì raw result
            
    except Exception as e:
        logger.error(f"Error checking log space: {e}")
        return {"error": str(e)}


@db_api.post("/blocking_sessions")
async def check_blocking_sessions(request: Request):
    try:
        data = await request.json()
        connection_string = data.get("connection_string")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}
            
        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open("queries/blocking_sessions.sql").read())
            result = conn.execute(query)

            logger.info("Blocking Sessions query executed successfully")
            return [row for row in result]
    except Exception as e:
        logger.error(f"Error checking blocking sessions: {e}")


@db_api.post("/index_frag")
async def check_index_fragmentation(request: Request):

    try:
        data = await request.json()
        connection_string = data.get("connection_string")
        db_name = data.get("db_name")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open("queries/index_frag.sql").read())
            result = conn.execute(query, {"db_name": db_name})

            logger.info("Index Fragmentation query executed successfully")
            return [row for row in result]
    except Exception as e:
        logger.error(f"Error checking index frag: {e}")

        
@db_api.post("/change_pwd")
async def change_password(request: Request):

    try:
        data = await request.json()
        connection_string = data.get("connection_string")
        login_name = data.get("login_name")
        new_password = data.get("new_password")

        if not connection_string:
            return {"error": "Missing connection_string in payload"}

        engine = create_engine(connection_string)
        with engine.connect() as conn:

            query = text(open("queries/change_pwd.sql").read())
            result = conn.execute(query, {"login_name": login_name, "password": new_password})

            logger.info("Change Password query executed successfully")
            return [row for row in result]
    except Exception as e:
        logger.error(f"Error changing password: {e}")