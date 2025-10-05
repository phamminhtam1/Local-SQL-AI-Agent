from multiprocessing import Process
from mcp_server_db import mcp as db_mcp
from mcp_server_search import mcp as search_mcp

def run_db():
    db_mcp.run(transport='http', host='0.0.0.0', port=8001)

def run_search():
    search_mcp.run(transport='http', host='0.0.0.0', port=8002)

if __name__ == "__main__":
    p1 = Process(target=run_db)
    p2 = Process(target=run_search)
    p1.start()
    p2.start()
    p1.join()
    p2.join()