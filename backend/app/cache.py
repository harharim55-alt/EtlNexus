"""Shared in-memory TTL cache for read-heavy data.

Short-lived caches (30-60 s) cut redundant DB queries and repeated live Spark
schema reads. The cache is process-local and in-memory only — there is no
external cache store. In a multi-instance deployment each process keeps its own
cache; they converge through TTL expiry. See docs/adr/001-in-memory-cache-design.md.
"""

import logging
import threading
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 5000


class TTLCache[T]:
    """Simple generic TTL cache backed by a plain dict."""

    def __init__(self, ttl: int = 30):
        self._ttl = ttl
        self._store: dict[str, tuple[float, T]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            return None  # Expired; lazy eviction in set()
        return value

    def set(self, key: str, value: T) -> None:
        now = time.monotonic()
        with self._lock:
            # Lazy eviction when store grows large
            if len(self._store) >= _MAX_ENTRIES:
                self._store = {k: v for k, v in self._store.items() if now - v[0] <= self._ttl}
            self._store[key] = (now, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# ── Module-level singletons ──────────────────────────────────────────
product_list_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)  # list_products (no filters)
catalog_context_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)  # AI catalog summary string
table_schema_cache: TTLCache[Any] = TTLCache(
    ttl=settings.table_schema_cache_ttl
)  # one table's live schema, keyed by fqn


def clear_all() -> None:
    """Invalidate every application cache in this process."""
    product_list_cache.clear()
    catalog_context_cache.clear()
    table_schema_cache.clear()
    logger.debug("All application caches cleared")
