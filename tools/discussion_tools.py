"""
Discussion platform tool wrappers for Reddit and Hacker News.
Delegates to search_tools for real API-backed results.
"""

from tools.search_tools import (
    search_web as _search_web,
    search_hackernews as _search_hackernews,
)


async def search_reddit(query: str, subreddit: str = "", limit: int = 5) -> list[dict]:
    """Search Reddit via SerpAPI site filter."""
    q = f"site:reddit.com/{subreddit} {query}" if subreddit else f"site:reddit.com {query}"
    results = await _search_web(q, num_results=limit)
    for r in results:
        r["source_type"] = "reddit"
    return results


async def search_hackernews(query: str, limit: int = 5) -> list[dict]:
    """Search Hacker News via Algolia API."""
    results = await _search_hackernews(query, num_results=limit)
    return results
