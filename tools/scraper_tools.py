"""
Page scraping tools with Firecrawl integration.
Uses Firecrawl API for LLM-ready markdown when available,
falls back to httpx + basic HTML extraction.
"""

import os
import re
import httpx
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

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


def _strip_html(html: str) -> str:
    """Naive HTML tag stripper — fallback when Firecrawl is unavailable."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def scrape_page_firecrawl(url: str) -> dict | None:
    """Scrape a page using Firecrawl API. Returns None if unavailable."""
    if not FIRECRAWL_API_KEY:
        return None
    try:
        client = await _get_client()
        resp = await client.post(
            f"{FIRECRAWL_BASE}/scrape",
            json={"url": url, "formats": ["markdown"]},
            headers={
                "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=25.0,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            return None

        page_data = data.get("data", {})
        markdown = page_data.get("markdown", "")
        metadata = page_data.get("metadata", {})

        return {
            "url": url,
            "title": metadata.get("title", ""),
            "text": markdown[:8000],
            "description": metadata.get("description", ""),
            "status": metadata.get("statusCode", 200),
            "source": "firecrawl",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        return None


async def scrape_page_httpx(url: str) -> dict:
    """Fallback: fetch a URL with httpx and return cleaned text."""
    try:
        client = await _get_client()
        resp = await client.get(url)
        resp.raise_for_status()
        html = resp.text

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        text = _strip_html(html)

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
            "error": str(e),
            "source": "httpx",
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }


async def scrape_page(url: str) -> dict:
    """Scrape a page — tries Firecrawl first, falls back to httpx."""
    firecrawl_result = await scrape_page_firecrawl(url)
    if firecrawl_result and firecrawl_result.get("text"):
        return firecrawl_result
    return await scrape_page_httpx(url)


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
        "body": " ".join(words[third : third * 2]),
        "footer": " ".join(words[third * 2 :]),
    }
    return {**page, "sections": sections}
