"""Tests for app.cache — TTLCache in-memory caching."""


from app.cache import TTLCache, clear_all


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
        # Entry should be evicted on read
        assert "key1" not in cache._store

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


class TestClearAll:
    def test_clear_all_resets_every_module_cache(self):
        """Verify clear_all() touches all module-level cache singletons."""
        from app.cache import (
            bouncer_cache,
            bouncer_topology_cache,
            dag_summary_cache,
            grant_level_cache,
            join_suggestions_cache,
            pipeline_list_cache,
            schema_matrix_cache,
            topology_cache,
        )

        # Seed each cache
        caches = [
            pipeline_list_cache, schema_matrix_cache, topology_cache,
            dag_summary_cache, bouncer_cache, bouncer_topology_cache,
            grant_level_cache, join_suggestions_cache,
        ]
        for c in caches:
            c.set("test_key", "test_value")

        clear_all()

        for c in caches:
            assert c.get("test_key") is None
