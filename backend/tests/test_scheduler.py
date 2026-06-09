"""Tests for app.tasks.scheduler — the catalog-mirror guard and startup sync.

Airflow has been removed; the scheduler now runs only the catalog mirror
(guarded against overlap) plus run-history retention, and startup seeds data +
refreshes the catalog mirror.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _guarded_mirror
# ---------------------------------------------------------------------------


class TestGuardedMirror:
    async def test_skips_when_lock_held(self):
        """When the mirror lock is already held, _guarded_mirror returns immediately."""
        from app.tasks import scheduler

        lock = asyncio.Lock()
        mirror_fn = AsyncMock()

        with patch.object(scheduler, "_mirror_lock", lock):
            await lock.acquire()
            try:
                with patch(
                    "app.tasks.catalog_mirror_task.refresh_catalog_mirror",
                    mirror_fn,
                ):
                    await scheduler._guarded_mirror()
                mirror_fn.assert_not_awaited()
            finally:
                lock.release()

    async def test_runs_when_lock_free(self):
        """When the mirror lock is free, the refresh function is called."""
        from app.tasks import scheduler

        mirror_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", mirror_fn),
            patch("app.cache.clear_all", clear_fn),
            patch("app.routers.health.report_sync_completed", MagicMock()),
        ):
            await scheduler._guarded_mirror()

        mirror_fn.assert_awaited_once()

    async def test_clears_cache_after_mirror(self):
        """Cache is cleared in the finally block after a successful refresh."""
        from app.tasks import scheduler

        mirror_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", mirror_fn),
            patch("app.cache.clear_all", clear_fn),
            patch("app.routers.health.report_sync_completed", MagicMock()),
        ):
            await scheduler._guarded_mirror()

        clear_fn.assert_called_once()

    async def test_clears_cache_even_on_mirror_failure(self):
        """Cache is cleared even when the refresh function raises."""
        from app.tasks import scheduler

        mirror_fn = AsyncMock(side_effect=RuntimeError("mirror exploded"))
        clear_fn = MagicMock()

        with (
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", mirror_fn),
            patch("app.cache.clear_all", clear_fn),
        ):
            # Should not propagate the exception (caught by except)
            await scheduler._guarded_mirror()

        clear_fn.assert_called_once()


# ---------------------------------------------------------------------------
# run_startup_sync
# ---------------------------------------------------------------------------


class TestRunStartupSync:
    async def test_runs_seeds_and_mirror(self):
        """Startup seeds bouncer volumes + usage, then refreshes the catalog mirror."""
        from app.tasks import scheduler

        bouncer_fn = AsyncMock()
        usage_fn = AsyncMock()
        mirror_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch("app.tasks.seed_bouncer_volumes.seed_bouncer_volumes", bouncer_fn),
            patch("app.tasks.seed_usage_data.seed_usage_data", usage_fn),
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", mirror_fn),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler.run_startup_sync()

        bouncer_fn.assert_awaited_once()
        usage_fn.assert_awaited_once()
        mirror_fn.assert_awaited_once()
        clear_fn.assert_called()

    async def test_continues_when_a_seed_fails(self):
        """A failing seed does not stop the remaining startup steps."""
        from app.tasks import scheduler

        bouncer_fn = AsyncMock(side_effect=RuntimeError("seed exploded"))
        usage_fn = AsyncMock()
        mirror_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch("app.tasks.seed_bouncer_volumes.seed_bouncer_volumes", bouncer_fn),
            patch("app.tasks.seed_usage_data.seed_usage_data", usage_fn),
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", mirror_fn),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler.run_startup_sync()

        # Independent steps still run despite the seed failure
        usage_fn.assert_awaited_once()
        mirror_fn.assert_awaited_once()
        clear_fn.assert_called()
