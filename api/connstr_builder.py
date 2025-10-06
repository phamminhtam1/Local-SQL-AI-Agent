from typing import Dict, Any
from models import DatabaseType
import logging
from fastapi import HTTPException
from sqlalchemy import create_engine, URL
from sqlalchemy.engine import Engine
from datetime import datetime
from urllib.parse import quote_plus
logger = logging.getLogger(__name__)

class ConnectionStringBuilder:
    """Class to create connection strings for various database types"""
    
    def __init__(self):
        self.db_connection_generators = {
            DatabaseType.MYSQL: self._generate_mysql_connection,
            DatabaseType.POSTGRESQL: self._generate_postgresql_connection,
            DatabaseType.MONGODB: self._generate_mongodb_connection,
            DatabaseType.REDIS: self._generate_redis_connection,
            DatabaseType.SQLITE: self._generate_sqlite_connection,
            DatabaseType.ORACLE: self._generate_oracle_connection,
            DatabaseType.SQLSERVER: self._generate_sqlserver_connection,
        }
    
    def generate_connection_string(self, db_config: Dict[str, Any]) -> str:
        """Create connection string based on DB config"""
        try:
            db_type = db_config.get("type", "mysql").lower()
            
            if db_type in [db.value for db in DatabaseType]:
                db_enum = DatabaseType(db_type)
                return self.db_connection_generators[db_enum](db_config)
            else:
                logger.warning(f"Unknown database type '{db_type}', using MySQL")
                return self._generate_mysql_connection(db_config)
                
        except Exception as e:
            logger.error(f"Error generating connection string: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate connection string")
    
    def create_engine_from_config(self, db_config: Dict[str, Any]) -> Engine:
        """Create SQLAlchemy Engine from config"""
        try:
            connection_string = self.generate_connection_string(db_config)
            return create_engine(connection_string, echo=False)
        except Exception as e:
            logger.error(f"Error creating engine: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to create database engine")
    
    def _generate_mysql_connection(self, config: Dict[str, Any]) -> str:
        """Create MySQL connection string using SQLAlchemy URL"""
        logger.info(f"MySQL config received: {config}")

        try:
            password = config.get("password", "")
            encoded_password = quote_plus(password)
            logger.info("encoded_password" + encoded_password)

            username=quote_plus(config.get("username", "root"))
            host=config.get("host", "localhost")
            port=config.get("port", 3306)
            database=quote_plus(config.get("database", "default"))
            logger.info(f"Generated connection string:"+ f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{database}")
            return f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{database}"
        except Exception as e:
            logger.error(f"Error generating MySQL connection: {str(e)}")
            # fallback to manual string
            host = config.get("host", "localhost")
            port = config.get("port", "3306") or 3306
            database = quote_plus(config.get("database", "default"))
            username = quote_plus(config.get("username", "root"))
            password = quote_plus(config.get("password", ""))
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    
    def _generate_postgresql_connection(self, config: Dict[str, Any]) -> str:
        """Create PostgreSQL connection string using SQLAlchemy URL"""
        try:
            url = URL.create(
                drivername="postgresql",
                username=config.get("username", "postgres"),
                password=config.get("password", ""),
                host=config.get("host", "localhost"),
                port=config.get("port", 5432),
                database=config.get("database", "default")
            )
            return str(url)
        except Exception as e:
            logger.error(f"Error generating PostgreSQL connection: {str(e)}")
            # fallback to manual string
            host = config.get("host", "localhost")
            port = config.get("port", "5432")
            database = config.get("database", "default")
            username = config.get("username", "postgres")
            password = config.get("password", "")
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    def _generate_mongodb_connection(self, config: Dict[str, Any]) -> str:
        """Create MongoDB connection string"""
        host = config.get("host", "localhost")
        port = config.get("port", "27017")
        database = config.get("database", "default")
        username = config.get("username", "")
        password = config.get("password", "")
        
        if username and password:
            return f"mongodb://{username}:{password}@{host}:{port}/{database}"
        else:
            return f"mongodb://{host}:{port}/{database}"
    
    def _generate_redis_connection(self, config: Dict[str, Any]) -> str:
        """Create Redis connection string"""
        host = config.get("host", "localhost")
        port = config.get("port", "6379")
        database = config.get("database", "0")
        password = config.get("password", "")
        
        if password:
            return f"redis://:{password}@{host}:{port}/{database}"
        else:
            return f"redis://{host}:{port}/{database}"
    
    def _generate_sqlite_connection(self, config: Dict[str, Any]) -> str:
        """Create SQLite connection string using SQLAlchemy URL"""
        try:
            database = config.get("database", "default.db")
            url = URL.create(
                drivername="sqlite",
                database=database
            )
            return str(url)
        except Exception as e:
            logger.error(f"Error generating SQLite connection: {str(e)}")
            # fallback to manual string
            database = config.get("database", "default.db")
            return f"sqlite:///{database}"
    
    def _generate_oracle_connection(self, config: Dict[str, Any]) -> str:
        """Create Oracle connection string using SQLAlchemy URL"""
        try:
            url = URL.create(
                drivername="oracle",
                username=config.get("username", "system"),
                password=config.get("password", ""),
                host=config.get("host", "localhost"),
                port=config.get("port", 1521),
                database=config.get("database", "default")
            )
            return str(url)
        except Exception as e:
            logger.error(f"Error generating Oracle connection: {str(e)}")
            # fallback to manual string
            host = config.get("host", "localhost")
            port = config.get("port", "1521")
            database = config.get("database", "default")
            username = config.get("username", "system")
            password = config.get("password", "")
            return f"oracle://{username}:{password}@{host}:{port}/{database}"
    
    def _generate_sqlserver_connection(self, config: Dict[str, Any]) -> str:
        """Create SQL Server connection string using SQLAlchemy URL"""
        try:
            url = URL.create(
                drivername="mssql+pyodbc",
                username=config.get("username", "sa"),
                password=config.get("password", ""),
                host=config.get("host", "localhost"),
                port=config.get("port", 1433),
                database=config.get("database", "default"),
                query={"driver": "ODBC Driver 17 for SQL Server"}
            )
            return str(url)
        except Exception as e:
            logger.error(f"Error generating SQL Server connection: {str(e)}")
            # fallback to manual string
            host = config.get("host", "localhost")
            port = config.get("port", "1433")
            database = config.get("database", "default")
            username = config.get("username", "sa")
            password = config.get("password", "")
            return f"mssql+pyodbc://{username}:{password}@{host}:{port}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
        
    def validate_connection(self, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate connection string and test connection"""
        try:
            engine = self.create_engine_from_config(db_config)
            
            # test connection
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            
            return {
                "status": "valid",
                "connection_string": self.generate_connection_string(db_config),
                "database_type": db_config.get("type", "mysql"),
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "invalid",
                "error": str(e),
                "database_type": db_config.get("type", "mysql"),
                "timestamp": datetime.now().isoformat()
            }