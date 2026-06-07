"""Shared in-memory TTL cache for read-heavy data.

Pipeline data changes only every sync cycle, so short-lived caches (30-60 s)
eliminate redundant DB queries between syncs. All caches are cleared after each
sync/poll cycle completes via :func:`clear_all`.

The cache is process-local and in-memory only — there is no external cache
store. In a multi-instance deployment each process keeps its own cache; they
converge through TTL expiry plus the post-sync ``clear_all()`` each process runs.
See docs/adr/001-in-memory-cache-design.md.
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
                self._store = {
                    k: v for k, v in self._store.items()
                    if now - v[0] <= self._ttl
                }
            self._store[key] = (now, value)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# ── Module-level singletons ──────────────────────────────────────────
pipeline_list_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)     # list_pipelines (no query)
schema_matrix_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_medium)    # schema matrix response
topology_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)          # topology per pipeline+dag
dag_summary_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_medium)      # dag summary/statistics
bouncer_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_medium)          # bouncer list
bouncer_topology_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)  # bouncer topology
grant_level_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)       # per-user grant level for pipeline
join_suggestions_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_medium) # join suggestions per pipeline
task_id_map_cache: TTLCache[Any] = TTLCache(ttl=settings.cache_ttl_short)       # lightweight {task_id: summary} lookup


def clear_all() -> None:
    """Invalidate every application cache in this process.

    Called after each sync/poll cycle. The cache is in-memory and process-local,
    so this clears only the calling process's caches.
    """
    pipeline_list_cache.clear()
    schema_matrix_cache.clear()
    topology_cache.clear()
    dag_summary_cache.clear()
    bouncer_cache.clear()
    bouncer_topology_cache.clear()
    grant_level_cache.clear()
    join_suggestions_cache.clear()
    task_id_map_cache.clear()
    logger.debug("All application caches cleared")
