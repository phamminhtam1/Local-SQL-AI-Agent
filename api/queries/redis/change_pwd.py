import redis

def change_pwd_redis(redis_url: str, username: str | None, password: str):
    r = redis.from_url(redis_url)
    if username and username != "default":
        # Redis ACL user (Redis 6+)
        r.acl_setuser(username, "on", f">#{password}")  # or f">{password}" if not using hashed
    else:
        # Đổi password cho default user (cách đơn giản cho single-password)
        r.config_set("requirepass", password)
    return {"status": "ok"}