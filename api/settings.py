import os

# Service registry / routing map
PROXY_TARGETS = {
    "vault": os.getenv("VAULT_SERVICE_URL"),
    "self": os.getenv("SELF_API_URL"),
}