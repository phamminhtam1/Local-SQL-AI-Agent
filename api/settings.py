import os

# Service registry / routing map
PROXY_TARGETS = {
    "self": os.getenv("SELF_API_URL"),
    "vault": os.getenv("VAULT_SERVICE_URL")
}