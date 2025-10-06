import redis

def get_log_space_redis(redis_url: str):
    r = redis.from_url(redis_url)
    info = r.info()
    out = {
        "UsedMemoryBytes": info.get("used_memory", 0),
        "UsedMemoryHuman": info.get("used_memory_human", ""),
        "DBs": []
    }
    for db, meta in info.get("keyspace", {}).items():
        # meta dạng "keys=123,expires=10,avg_ttl=0"
        parts = dict(kv.split('=') for kv in meta.split(','))
        out["DBs"].append({
            "DB": db,
            "Keys": int(parts.get("keys", 0)),
            "Expires": int(parts.get("expires", 0)),
            "AvgTTL": int(parts.get("avg_ttl", 0)),
        })
    return out