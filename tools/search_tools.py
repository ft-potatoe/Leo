"""
Lightweight search tool wrappers.
Priority: SerpAPI → NewsAPI → HN Algolia (free) → mock data
"""

import os
import logging
import httpx
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

SERP_API_KEY = os.getenv("SERP_API_KEY", "")
SERP_BASE = "https://serpapi.com/search"

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
NEWSAPI_BASE = "https://newsapi.org/v2/everything"

_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=15.0)
    return _client


# ── NewsAPI ───────────────────────────────────────────────────────────────────

async def _newsapi_search(query: str, num_results: int = 5) -> list[dict]:
    """Search news articles via NewsAPI. Returns [] on failure."""
    if not NEWSAPI_KEY:
        return []
    try:
        client = await _get_client()
        resp = await client.get(
            NEWSAPI_BASE,
            params={
                "q": query,
                "apiKey": NEWSAPI_KEY,
                "pageSize": num_results,
                "language": "en",
                "sortBy": "relevancy",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for article in data.get("articles", [])[:num_results]:
            results.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "snippet": article.get("description") or article.get("content", "")[:300],
                "source_type": "news",
                "source_name": article.get("source", {}).get("name", ""),
                "published_at": article.get("publishedAt", ""),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })
        return results
    except Exception as e:
        logger.warning("NewsAPI search failed for %r: %s", query, e)
        return []


# ── Web search (SerpAPI → NewsAPI fallback) ───────────────────────────────────

async def search_web(query: str, num_results: int = 5) -> list[dict]:
    """Search the web via SerpAPI. Falls back to NewsAPI, then mock."""
    if SERP_API_KEY:
        try:
            client = await _get_client()
            resp = await client.get(
                SERP_BASE,
                params={"q": query, "api_key": SERP_API_KEY, "num": num_results, "engine": "google"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for item in data.get("organic_results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source_type": "web_search",
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                })
            if results:
                return results
        except Exception as e:
            logger.warning("SerpAPI search failed for %r: %s", query, e)

    # Fallback: NewsAPI
    news_results = await _newsapi_search(query, num_results)
    if news_results:
        return news_results

    return _mock_web_results(query, num_results)


async def search_news(query: str, num_results: int = 5) -> list[dict]:
    """Search news articles directly via NewsAPI."""
    results = await _newsapi_search(query, num_results)
    if not results:
        logger.warning("NewsAPI returned no results for %r", query)
    return results


async def search_reddit(query: str, num_results: int = 5) -> list[dict]:
    """Search Reddit via web search with site filter."""
    return await search_web(f"site:reddit.com {query}", num_results)


async def search_hackernews(query: str, num_results: int = 5) -> list[dict]:
    """Search Hacker News via the Algolia HN API (free, no key required)."""
    try:
        client = await _get_client()
        resp = await client.get(
            "https://hn.algolia.com/api/v1/search",
            params={"query": query, "hitsPerPage": num_results},
        )
        resp.raise_for_status()
        data = resp.json()
        results = []
        for hit in data.get("hits", [])[:num_results]:
            results.append({
                "title": hit.get("title") or hit.get("story_title", ""),
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                "snippet": (hit.get("comment_text") or hit.get("story_text") or "")[:300],
                "source_type": "hackernews",
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })
        return results
    except Exception as e:
        logger.warning("HackerNews search failed for %r: %s", query, e)
        return []


async def search_job_postings(company: str, num_results: int = 5) -> list[dict]:
    """Search for job postings as a hiring/growth signal."""
    query = (
        f'"{company}" hiring OR jobs site:linkedin.com OR site:lever.co '
        f'OR site:greenhouse.io OR site:jobs.ashbyhq.com'
    )
    results = await search_web(query, num_results)
    for r in results:
        r["source_type"] = "job_posting"
    return results


async def search_funding_news(company: str, num_results: int = 5) -> list[dict]:
    """Search for funding, investment, and M&A news. Prefers NewsAPI."""
    query = (
        f'"{company}" funding OR "series A" OR "series B" OR raised OR '
        f'acquisition OR "venture capital" OR IPO'
    )
    # NewsAPI is ideal for news-oriented queries — try it first
    results = await _newsapi_search(query, num_results)
    if not results:
        results = await search_web(query, num_results)
    for r in results:
        r["source_type"] = "funding_news"
    return results


async def search_patent_activity(company: str, num_results: int = 3) -> list[dict]:
    """Search USPTO and Google Patents for pre-launch technical signals."""
    query = f'site:patents.google.com OR site:patents.justia.com "{company}"'
    results = await search_web(query, num_results)
    for r in results:
        r["source_type"] = "patent"
    return results


def _mock_web_results(query: str, num: int) -> list[dict]:
    """Last-resort mock results when all APIs are unavailable."""
    now = datetime.now(timezone.utc).isoformat()
    return [
        {
            "title": f"Result for: {query}",
            "url": f"https://example.com/search?q={query.replace(' ', '+')}",
            "snippet": f"Simulated search result snippet for '{query}'. Add a valid SERP_API_KEY for live web search.",
            "source_type": "web_search_mock",
            "collected_at": now,
        }
    ][:num]
