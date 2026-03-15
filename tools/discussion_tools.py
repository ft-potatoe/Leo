"""
Discussion platform tools — real API integration for Reddit and Hacker News.
Reddit: uses public JSON endpoints (no OAuth required for read-only).
HN: uses the free Algolia Search API.
"""

import httpx
from datetime import datetime, timezone

_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Leo/1.0 (Growth Intelligence Agent)"},
        )
    return _client


async def search_reddit(query: str, subreddit: str = "", limit: int = 5) -> list[dict]:
    """
    Search Reddit using the public JSON API (no auth needed).
    Falls back to empty list on failure.
    """
    try:
        client = await _get_client()
        if subreddit:
            url = f"https://www.reddit.com/r/{subreddit}/search.json"
            params = {"q": query, "limit": limit, "sort": "relevance", "t": "year", "restrict_sr": "on"}
        else:
            url = "https://www.reddit.com/search.json"
            params = {"q": query, "limit": limit, "sort": "relevance", "t": "year"}

        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        posts = []
        for child in data.get("data", {}).get("children", [])[:limit]:
            post = child.get("data", {})
            posts.append({
                "title": post.get("title", ""),
                "url": f"https://reddit.com{post.get('permalink', '')}",
                "subreddit": post.get("subreddit", ""),
                "score": post.get("score", 0),
                "num_comments": post.get("num_comments", 0),
                "snippet": (post.get("selftext", "") or post.get("title", ""))[:400],
                "source_type": "reddit",
                "created_at": datetime.fromtimestamp(
                    post.get("created_utc", 0), tz=timezone.utc
                ).isoformat() if post.get("created_utc") else datetime.now(timezone.utc).isoformat(),
            })
        return posts
    except Exception:
        return []


async def search_hackernews(query: str, limit: int = 5) -> list[dict]:
    """
    Search Hacker News via the free Algolia API.
    Returns stories and comments matching the query.
    """
    try:
        client = await _get_client()
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "hitsPerPage": limit, "tags": "(story,show_hn,ask_hn)"},
        )
        resp.raise_for_status()
        data = resp.json()

        stories = []
        for hit in data.get("hits", [])[:limit]:
            stories.append({
                "title": hit.get("title") or hit.get("story_title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "score": hit.get("points", 0),
                "num_comments": hit.get("num_comments", 0),
                "snippet": (hit.get("story_text") or hit.get("comment_text") or hit.get("title", ""))[:400],
                "source_type": "hackernews",
                "created_at": hit.get("created_at", datetime.now(timezone.utc).isoformat()),
            })
        return stories
    except Exception:
        return []


async def get_hackernews_comments(story_id: str, limit: int = 10) -> list[dict]:
    """
    Fetch comments for a specific HN story via Algolia API.
    Useful for multi-hop deep research.
    """
    try:
        client = await _get_client()
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search",
            params={"tags": f"comment,story_{story_id}", "hitsPerPage": limit},
        )
        resp.raise_for_status()
        data = resp.json()

        comments = []
        for hit in data.get("hits", [])[:limit]:
            text = hit.get("comment_text", "")
            if text:
                comments.append({
                    "text": text[:500],
                    "author": hit.get("author", ""),
                    "source_type": "hackernews_comment",
                    "url": f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "created_at": hit.get("created_at", ""),
                })
        return comments
    except Exception:
        return []
