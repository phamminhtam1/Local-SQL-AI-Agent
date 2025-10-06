from pymongo import MongoClient
from datetime import datetime

def get_health_check_mongo(uri: str):
    client = MongoClient(uri)
    try:
        # Server info
        server_info = client.server_info()
        
        # Database stats
        db_stats = client.admin.command("dbStats")
        
        # Connection info
        conn_info = client.admin.command("connPoolStats")
        
        return {
            "DatabaseType": "MongoDB",
            "Version": server_info.get("version"),
            "Hostname": server_info.get("host"),
            "Port": server_info.get("port"),
            "CurrentDatabase": "admin",
            "CurrentTime": datetime.now().isoformat(),
            "MaxConnections": conn_info.get("totalCreated", 0),
            "CurrentConnections": conn_info.get("totalInUse", 0),
            "Collections": db_stats.get("collections", 0),
            "Indexes": db_stats.get("indexes", 0),
            "DataSizeMB": round(db_stats.get("dataSize", 0) / 1024 / 1024, 2),
            "StorageSizeMB": round(db_stats.get("storageSize", 0) / 1024 / 1024, 2)
        }
    except Exception as e:
        return {"error": str(e)}