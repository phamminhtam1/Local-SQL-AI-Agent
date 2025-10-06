import redis
from datetime import datetime

def get_health_check_redis(redis_url: str):
    r = redis.from_url(redis_url)
    try:
        info = r.info()
        return {
            "DatabaseType": "Redis",
            "Version": info.get("redis_version"),
            "Hostname": info.get("tcp_port", "localhost"),
            "Port": info.get("tcp_port", 6379),
            "CurrentDatabase": f"db{info.get('db', 0)}",
            "CurrentTime": datetime.now().isoformat(),
            "MaxConnections": info.get("maxclients", 0),
            "CurrentConnections": info.get("connected_clients", 0),
            "UsedMemoryMB": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "MaxMemoryMB": round(info.get("maxmemory", 0) / 1024 / 1024, 2),
            "KeysCount": info.get("db0", {}).get("keys", 0) if "db0" in info.get("keyspace", {}) else 0,
            "UptimeSeconds": info.get("uptime_in_seconds", 0)
        }
    except Exception as e:
        return {"error": str(e)}