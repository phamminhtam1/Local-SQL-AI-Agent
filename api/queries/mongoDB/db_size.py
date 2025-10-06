from pymongo import MongoClient

def get_db_size_mongo(uri: str, db_name: str | None = None):
    client = MongoClient(uri)
    if db_name:
        stats = client[db_name].command("dbStats")
        return [{
            "DatabaseName": db_name,
            "DataSizeMB": round(stats.get("dataSize", 0) / 1024 / 1024, 2),
            "StorageSizeMB": round(stats.get("storageSize", 0) / 1024 / 1024, 2),
            "IndexSizeMB": round(stats.get("indexSize", 0) / 1024 / 1024, 2),
            "Collections": stats.get("collections", 0),
            "Indexes": stats.get("indexes", 0),
        }]
    else:
        dbs = client.admin.command("listDatabases")
        return [
            {
                "DatabaseName": d["name"],
                "SizeOnDiskMB": round(d.get("sizeOnDisk", 0)/1024/1024, 2),
                "Empty": d.get("empty", False),
            }
            for d in dbs["databases"]
        ]