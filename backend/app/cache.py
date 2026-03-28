"""Shared in-memory TTL cache for read-heavy data.

Pipeline data changes only every 20-min sync cycle, so short-lived caches
(30-60 s) eliminate redundant DB queries between syncs.  All caches are
cleared after each sync/poll cycle completes.

NOTE: This cache is process-local. In multi-instance deployments, each
process has its own cache. clear_all() broadcasts an invalidation message via
Redis pub/sub so that all running instances clear their local caches as well.
When Redis is unavailable the bus is simply not started and clear_all() falls
back to local-only behaviour — identical to the previous single-process design.
See docs/adr/001-in-memory-cache-design.md for further notes.
"""

import asyncio
import contextlib
import logging
import threading
import time
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 5000
_INVALIDATION_CHANNEL = "etlnexus:cache:invalidate"


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


def _clear_local() -> None:
    """Clear all 9 module-level caches in this process.

    Called both by :func:`clear_all` (which also publishes to Redis) and
    directly by :class:`CacheInvalidationBus` when it receives a remote
    invalidation message (to avoid re-publishing the same event).
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


class CacheInvalidationBus:
    """Redis pub/sub for cross-instance cache invalidation.

    Usage::

        # In application lifespan (startup):
        await invalidation_bus.start(settings.redis_url)

        # In application lifespan (shutdown):
        await invalidation_bus.stop()

    When :func:`clear_all` is called it publishes an ``"invalidate"`` message
    to :data:`_INVALIDATION_CHANNEL`.  Every running instance that has started
    this bus will receive the message and call :func:`_clear_local`, ensuring
    all processes stay in sync without requiring a shared cache store.

    If Redis is unavailable (bus never started, or connection fails) the
    publish call is silently skipped and caches still expire via TTL.
    """

    def __init__(self) -> None:
        self._redis: Any = None  # redis.asyncio.Redis — imported lazily
        self._subscriber_task: asyncio.Task[None] | None = None
        self._running: bool = False

    async def start(self, redis_url: str) -> None:
        """Connect to Redis and begin listening for invalidation messages.

        Args:
            redis_url: Redis connection URL, e.g. ``"redis://localhost:6379"``.
        """
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        await self._redis.ping()
        self._running = True
        self._subscriber_task = asyncio.create_task(
            self._subscribe_loop(), name="cache_invalidation_subscriber"
        )
        logger.info("Cache invalidation bus started (channel=%s)", _INVALIDATION_CHANNEL)

    async def stop(self) -> None:
        """Shut down the subscriber task and close the Redis connection."""
        self._running = False
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._subscriber_task
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        logger.info("Cache invalidation bus stopped")

    def publish(self) -> None:
        """Fire-and-forget publish of an invalidation message.

        Safe to call from synchronous code running inside an async event loop.
        If the bus has not been started (``_redis`` is ``None``) or no loop is
        running, the call is a no-op.
        """
        if self._redis is None:
            return
        try:
            loop = asyncio.get_running_loop()
            _task = loop.create_task(self._do_publish())  # noqa: RUF006 — fire-and-forget by design
        except RuntimeError:
            # No running event loop — skip silently.
            pass

    async def _do_publish(self) -> None:
        try:
            await self._redis.publish(_INVALIDATION_CHANNEL, "invalidate")
        except Exception:
            logger.warning("Failed to publish cache invalidation", exc_info=True)

    async def _subscribe_loop(self) -> None:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(_INVALIDATION_CHANNEL)
        try:
            while self._running:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=1.0
                )
                if message and message["type"] == "message":
                    logger.debug("Received cache invalidation from Redis")
                    _clear_local()
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(_INVALIDATION_CHANNEL)
            await pubsub.aclose()


# Module-level bus singleton.  Start it in the application lifespan handler
# by calling ``await invalidation_bus.start(settings.redis_url)``.
invalidation_bus = CacheInvalidationBus()


def clear_all() -> None:
    """Invalidate every application cache and broadcast to other instances.

    Clears all in-process caches immediately, then publishes an invalidation
    message to Redis (fire-and-forget) so that sibling processes also clear
    their local caches.  If the bus has not been started the Redis publish is
    skipped and only the local caches are cleared.
    """
    _clear_local()
    invalidation_bus.publish()
