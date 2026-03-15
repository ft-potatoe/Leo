"""
Agent result cache with TTL.

Caches OrchestratorResponse-compatible dicts keyed by (product + question hash).
Default TTL: 1 hour (3600 seconds).

Usage:
    from tools.cache import get_cache
    cache = get_cache()
    cached = cache.get(product, question)
    if cached:
        return cached
    result = await run_pipeline(...)
    cache.set(product, question, result)
"""

import hashlib
import time
from typing import Any


class AgentCache:
    """In-memory cache with per-entry TTL expiry."""

    DEFAULT_TTL: int = 3600  # 1 hour

    def __init__(self, ttl: int = DEFAULT_TTL) -> None:
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl

    # ── Key construction ──────────────────────────────────────────────────────

    def _make_key(self, product: str, question: str) -> str:
        """SHA-256 hash of normalised product + question string."""
        raw = f"{product.lower().strip()}::{question.lower().strip()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    # ── Public API ────────────────────────────────────────────────────────────

    def get(self, product: str, question: str) -> Any | None:
        """
        Return cached value or None if missing / expired.
        Evicts expired entries on access.
        """
        key = self._make_key(product, question)
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, product: str, question: str, value: Any) -> None:
        """Store value with TTL expiry."""
        key = self._make_key(product, question)
        self._store[key] = (value, time.monotonic() + self._ttl)

    def invalidate(self, product: str, question: str) -> None:
        """Explicitly remove a cache entry."""
        key = self._make_key(product, question)
        self._store.pop(key, None)

    def clear_all(self) -> None:
        """Flush entire cache."""
        self._store.clear()

    def evict_expired(self) -> int:
        """Remove all expired entries. Returns count removed."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]
        return len(expired)

    @property
    def size(self) -> int:
        """Number of entries currently in cache (including possibly stale ones)."""
        return len(self._store)

    def stats(self) -> dict:
        """Return cache statistics."""
        now = time.monotonic()
        live = sum(1 for _, (_, exp) in self._store.items() if now <= exp)
        return {
            "total_entries": len(self._store),
            "live_entries": live,
            "expired_entries": len(self._store) - live,
            "ttl_seconds": self._ttl,
        }


# ── Module-level singleton ────────────────────────────────────────────────────

_cache: AgentCache = AgentCache()


def get_cache() -> AgentCache:
    """Return the module-level cache singleton."""
    return _cache
