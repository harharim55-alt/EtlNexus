"""Shared in-memory TTL cache for read-heavy data.

Pipeline data changes only every 20-min sync cycle, so short-lived caches
(30–60 s) eliminate redundant DB queries between syncs.  All caches are
cleared after each sync/poll cycle completes.
"""

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class TTLCache:
    """Simple TTL cache backed by a plain dict."""

    def __init__(self, ttl: int = 30):
        self._ttl = ttl
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._store.clear()


# ── Module-level singletons ──────────────────────────────────────────
pipeline_list_cache = TTLCache(ttl=30)       # list_pipelines (no query)
schema_matrix_cache = TTLCache(ttl=60)       # schema matrix response
topology_cache = TTLCache(ttl=30)            # topology per pipeline+dag
dag_summary_cache = TTLCache(ttl=60)         # dag summary/statistics
bouncer_cache = TTLCache(ttl=60)             # bouncer list
bouncer_topology_cache = TTLCache(ttl=30)    # bouncer topology
grant_level_cache = TTLCache(ttl=30)         # per-user grant level for pipeline
join_suggestions_cache = TTLCache(ttl=60)    # join suggestions per pipeline


def clear_all() -> None:
    """Invalidate every application cache (called after sync/poll)."""
    pipeline_list_cache.clear()
    schema_matrix_cache.clear()
    topology_cache.clear()
    dag_summary_cache.clear()
    bouncer_cache.clear()
    bouncer_topology_cache.clear()
    grant_level_cache.clear()
    join_suggestions_cache.clear()
    logger.debug("All application caches cleared")
