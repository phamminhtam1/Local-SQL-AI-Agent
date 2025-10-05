import os

# Service registry / routing map
PROXY_TARGETS = {
    "database": "Database operations logic",
    "search": "Search operations logic",
    "vault": "http://host.docker.internal:8000"
}