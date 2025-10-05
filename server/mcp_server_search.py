import asyncio
import logging
import os
from fastmcp import FastMCP
from duckduckgo_search import DDGS
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

mcp = FastMCP("Search MCP Server")

# --- 1️⃣ Web Search ---
@mcp.tool
def web_search(query: str) -> str:
    """name: Web Search
       description: Perform a general web search and return summarized results
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return f"No results found for '{query}'."
        formatted = "\n\n".join(
            [f"{r['title']}\n{r['href']}\n{r['body']}" for r in results]
        )
        return formatted
    except Exception as e:
        return f"Web search failed: {e}"

# --- 2️⃣ News Search ---
@mcp.tool
def news_search(query: str) -> str:
    """name: News Search
       description: Search for latest news and current events about the given topic
    """
    try:
        api_key = os.getenv("NEWS_API_KEY")
        if not api_key:
            return "Missing NEWS_API_KEY in environment variables."
        url = f"https://newsapi.org/v2/everything?q={query}&apiKey={api_key}&language=en&sortBy=publishedAt"
        res = requests.get(url)
        data = res.json()
        if "articles" not in data:
            return f"No news results found: {data}"
        articles = data["articles"][:5]
        formatted = "\n\n".join(
            [f"{a['title']} ({a['source']['name']})\n{a['url']}" for a in articles]
        )
        return formatted or "No news articles found."
    except Exception as e:
        return f"News search failed: {e}"

@mcp.tool
def document_search(query: str) -> str:
    """name: Document Search
       description: Search within internal or local documents
    """
    return f"Simulated document search for: '{query}'"

