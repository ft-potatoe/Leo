"""
Page scraping tools.

Priority:
1. Firecrawl API (FIRECRAWL_API_KEY) — clean markdown extraction
2. httpx + naive HTML stripper — always-available fallback
"""

import os
import re
import logging
import httpx
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"

_client: httpx.AsyncClient | None = None


async def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LeoBot/1.0)"},
        )
    return _client


# ── Firecrawl ─────────────────────────────────────────────────────────────────

async def _firecrawl_scrape(url: str) -> dict | None:
    """
    Use Firecrawl to extract clean markdown from a URL.
    Returns None if Firecrawl is unavailable or the call fails.
    """
    if not FIRECRAWL_API_KEY:
        return None
    try:
        client = await _get_client()
        resp = await client.post(
            f"{FIRECRAWL_BASE}/scrape",
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"url": url, "formats": ["markdown"]},
        )
        resp.raise_for_status()
        data = resp.json()
        md = data.get("data", {}).get("markdown", "") or ""
        meta = data.get("data", {}).get("metadata", {}) or {}
        return {
            "url": url,
            "title": meta.get("title", ""),
            "text": md[:6000],  # cap at 6k chars
            "status": 200,
            "source": "firecrawl",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.warning("Firecrawl scrape failed for %s: %s", url, e)
        return None


# ── httpx fallback ────────────────────────────────────────────────────────────

def _strip_html(html: str) -> str:
    """Naive HTML tag stripper — good enough for hackathon use."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _httpx_scrape(url: str) -> dict:
    """Fallback scraper using httpx + regex HTML stripping."""
    try:
        client = await _get_client()
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text
        text = _strip_html(html)

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""

        return {
            "url": str(resp.url),
            "title": title,
            "text": text[:5000],
            "status": resp.status_code,
            "source": "httpx",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "url": url,
            "title": "",
            "text": "",
            "status": 0,
            "source": "httpx",
            "error": str(e),
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }


# ── Public API ────────────────────────────────────────────────────────────────

async def scrape_page(url: str) -> dict:
    """
    Fetch and return cleaned text content from a URL.

    Tries Firecrawl first (richer markdown output), falls back to httpx.
    """
    if FIRECRAWL_API_KEY:
        result = await _firecrawl_scrape(url)
        if result and result.get("text"):
            return result
    return await _httpx_scrape(url)


async def extract_page_sections(url: str) -> dict:
    """Scrape a page and split into rough sections (hero, body, footer)."""
    page = await scrape_page(url)
    text = page.get("text", "")
    if not text:
        return {**page, "sections": {}}

    words = text.split()
    total = len(words)
    third = max(total // 3, 1)

    sections = {
        "hero": " ".join(words[:third]),
        "body": " ".join(words[third: third * 2]),
        "footer": " ".join(words[third * 2:]),
    }
    return {**page, "sections": sections}
