from pymongo import MongoClient

def change_pwd_mongo(uri: str, login_name: str, password: str, db_name: str = "admin"):
    client = MongoClient(uri)
    db = client[db_name]
    db.command("updateUser", login_name, pwd=password)
    return {"status": "ok"}