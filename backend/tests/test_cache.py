"""Tests for app.cache — TTLCache in-memory caching and invalidation bus."""


from app.cache import CacheInvalidationBus, TTLCache, _clear_local, clear_all


class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache(ttl=10)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key_returns_none(self):
        cache = TTLCache(ttl=10)
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none(self):
        cache = TTLCache(ttl=1)
        cache.set("key1", "value1")

        # Advance time past TTL
        stored_ts = cache._store["key1"][0]
        cache._store["key1"] = (stored_ts - 2, "value1")

        assert cache.get("key1") is None
        # Expired entries are lazily evicted in set(), not on read

    def test_non_expired_entry_returns_value(self):
        cache = TTLCache(ttl=60)
        cache.set("key1", "data")
        assert cache.get("key1") == "data"

    def test_clear_removes_all_entries(self):
        cache = TTLCache(ttl=60)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
        assert cache.get("c") is None

    def test_overwrite_existing_key(self):
        cache = TTLCache(ttl=60)
        cache.set("key", "old")
        cache.set("key", "new")
        assert cache.get("key") == "new"

    def test_stores_various_types(self):
        cache = TTLCache(ttl=60)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1})
        cache.set("none", None)
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1}
        # None is stored as a valid value — the cache returns None for misses,
        # but internally stores (ts, None). On retrieval, the entry is found,
        # but value is None. This is actually an edge case the cache does not
        # distinguish from a miss. Documenting current behavior:
        result = cache.get("none")
        # The cache returns None for the stored None value — same as a miss.
        assert result is None

    def test_multiple_independent_keys(self):
        cache = TTLCache(ttl=60)
        cache.set("x", 10)
        cache.set("y", 20)
        assert cache.get("x") == 10
        assert cache.get("y") == 20


# ── Helpers shared between TestClearLocal and TestClearAll ────────────────────

def _all_caches():
    from app.cache import (
        bouncer_cache,
        bouncer_topology_cache,
        dag_summary_cache,
        grant_level_cache,
        join_suggestions_cache,
        pipeline_list_cache,
        schema_matrix_cache,
        task_id_map_cache,
        topology_cache,
    )
    return [
        pipeline_list_cache,
        schema_matrix_cache,
        topology_cache,
        dag_summary_cache,
        bouncer_cache,
        bouncer_topology_cache,
        grant_level_cache,
        join_suggestions_cache,
        task_id_map_cache,
    ]


class TestClearLocal:
    def test_clears_all_nine_caches(self):
        """_clear_local() resets every module-level cache singleton."""
        caches = _all_caches()
        for c in caches:
            c.set("test_key", "test_value")

        _clear_local()

        for c in caches:
            assert c.get("test_key") is None


class TestClearAll:
    def test_clear_all_resets_every_module_cache(self):
        """clear_all() clears local caches (bus not started — no Redis publish)."""
        caches = _all_caches()
        for c in caches:
            c.set("test_key", "test_value")

        # Bus is not started in unit tests so publish() is a no-op.
        clear_all()

        for c in caches:
            assert c.get("test_key") is None

    def test_clear_all_publishes_when_bus_started(self, monkeypatch):
        """clear_all() schedules a Redis publish when the bus has a live connection."""
        import asyncio

        import unittest.mock as mock

        published: list[str] = []

        bus = CacheInvalidationBus()
        # Use AsyncMock so self is not injected as a positional argument.
        fake_redis = mock.AsyncMock()
        fake_redis.publish.side_effect = lambda ch, _msg: published.append(ch)
        bus._redis = fake_redis

        # Run inside a real event loop so create_task works.
        async def run():
            monkeypatch.setattr("app.cache.invalidation_bus", bus)
            clear_all()
            # Allow the created task to execute.
            await asyncio.sleep(0)

        asyncio.run(run())

        assert published == ["etlnexus:cache:invalidate"]


class TestCacheInvalidationBus:
    def test_publish_noop_when_not_started(self):
        """publish() must not raise and must be a no-op before start() is called."""
        bus = CacheInvalidationBus()
        assert bus._redis is None
        # Should return without error — no running loop, no Redis connection.
        bus.publish()

    def test_publish_noop_outside_event_loop(self):
        """publish() is silently skipped when called outside an async context."""
        import asyncio

        bus = CacheInvalidationBus()
        # Give it a fake redis so the _redis is None check is bypassed,
        # but there is no running loop — RuntimeError must be swallowed.
        fake_redis = object()
        bus._redis = fake_redis

        # This call must not raise even without a running loop.
        bus.publish()

    def test_start_and_stop(self):
        """start() sets _running=True and stop() tears everything down cleanly."""
        import asyncio

        async def run():
            import unittest.mock as mock

            fake_redis = mock.AsyncMock()
            fake_pubsub = mock.AsyncMock()
            fake_pubsub.get_message = mock.AsyncMock(return_value=None)
            fake_redis.pubsub.return_value = fake_pubsub

            bus = CacheInvalidationBus()

            with mock.patch("redis.asyncio.from_url", return_value=fake_redis):
                await bus.start("redis://localhost:6379")

            assert bus._running is True
            assert bus._subscriber_task is not None

            await bus.stop()

            assert bus._running is False
            assert bus._redis is None

        asyncio.run(run())
