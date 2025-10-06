from pymongo import MongoClient

def get_log_space_mongo(uri: str):
    client = MongoClient(uri)
    dbs = client.admin.command("listDatabases")
    return [
        {
            "DatabaseName": d["name"],
            "SizeOnDiskMB": round(d.get("sizeOnDisk", 0)/1024/1024, 2),
            "Empty": d.get("empty", False),
        }
        for d in dbs["databases"]
    ]