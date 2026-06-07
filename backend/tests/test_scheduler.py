"""Tests for app.tasks.scheduler — lock guards and startup sync.

Tests the asyncio.Lock-based guards that prevent concurrent sync/poll
executions, and the retry logic in run_startup_sync.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# _guarded_sync
# ---------------------------------------------------------------------------


class TestGuardedSync:
    async def test_skips_when_lock_held(self):
        """When the sync lock is already held, _guarded_sync returns immediately."""
        from app.tasks import scheduler

        lock = asyncio.Lock()
        sync_fn = AsyncMock()

        with patch.object(scheduler, "_sync_lock", lock):
            # Acquire the lock before calling _guarded_sync
            await lock.acquire()
            try:
                with patch(
                    "app.tasks.airflow_sync_task.sync_pipelines_from_airflow",
                    sync_fn,
                ):
                    await scheduler._guarded_sync()
                sync_fn.assert_not_awaited()
            finally:
                lock.release()

    async def test_runs_when_lock_free(self):
        """When the sync lock is free, the sync function is called."""
        from app.tasks import scheduler

        sync_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.airflow_sync_task.sync_pipelines_from_airflow",
                sync_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler._guarded_sync()

        sync_fn.assert_awaited_once()

    async def test_clears_cache_after_sync(self):
        """Cache is cleared in the finally block after successful sync."""
        from app.tasks import scheduler

        sync_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.airflow_sync_task.sync_pipelines_from_airflow",
                sync_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler._guarded_sync()

        clear_fn.assert_called_once()

    async def test_clears_cache_even_on_sync_failure(self):
        """Cache is cleared even when the sync function raises."""
        from app.tasks import scheduler

        sync_fn = AsyncMock(side_effect=RuntimeError("sync exploded"))
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.airflow_sync_task.sync_pipelines_from_airflow",
                sync_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            # Should not propagate the exception (caught by except)
            await scheduler._guarded_sync()

        clear_fn.assert_called_once()


# ---------------------------------------------------------------------------
# _guarded_poll
# ---------------------------------------------------------------------------


class TestGuardedPoll:
    async def test_skips_when_lock_held(self):
        """When the poll lock is already held, _guarded_poll returns immediately."""
        from app.tasks import scheduler

        lock = asyncio.Lock()
        poll_fn = AsyncMock()

        with patch.object(scheduler, "_poll_lock", lock):
            await lock.acquire()
            try:
                with patch(
                    "app.tasks.airflow_poll_task.poll_airflow_statuses",
                    poll_fn,
                ):
                    await scheduler._guarded_poll()
                poll_fn.assert_not_awaited()
            finally:
                lock.release()

    async def test_runs_when_lock_free(self):
        """When the poll lock is free, the poll function is called."""
        from app.tasks import scheduler

        poll_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.airflow_poll_task.poll_airflow_statuses",
                poll_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler._guarded_poll()

        poll_fn.assert_awaited_once()

    async def test_clears_cache_after_poll(self):
        """Cache is cleared in the finally block after successful poll."""
        from app.tasks import scheduler

        poll_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.airflow_poll_task.poll_airflow_statuses",
                poll_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler._guarded_poll()

        clear_fn.assert_called_once()

    async def test_clears_cache_even_on_poll_failure(self):
        """Cache is cleared even when the poll function raises."""
        from app.tasks import scheduler

        poll_fn = AsyncMock(side_effect=RuntimeError("poll exploded"))
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.airflow_poll_task.poll_airflow_statuses",
                poll_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler._guarded_poll()

        clear_fn.assert_called_once()


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
            patch(
                "app.tasks.catalog_mirror_task.refresh_catalog_mirror",
                mirror_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler._guarded_mirror()

        mirror_fn.assert_awaited_once()

    async def test_clears_cache_after_mirror(self):
        """Cache is cleared in the finally block after a successful refresh."""
        from app.tasks import scheduler

        mirror_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.catalog_mirror_task.refresh_catalog_mirror",
                mirror_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            await scheduler._guarded_mirror()

        clear_fn.assert_called_once()

    async def test_clears_cache_even_on_mirror_failure(self):
        """Cache is cleared even when the refresh function raises."""
        from app.tasks import scheduler

        mirror_fn = AsyncMock(side_effect=RuntimeError("mirror exploded"))
        clear_fn = MagicMock()

        with (
            patch(
                "app.tasks.catalog_mirror_task.refresh_catalog_mirror",
                mirror_fn,
            ),
            patch("app.cache.clear_all", clear_fn),
        ):
            # Should not propagate the exception (caught by except)
            await scheduler._guarded_mirror()

        clear_fn.assert_called_once()


# ---------------------------------------------------------------------------
# run_startup_sync
# ---------------------------------------------------------------------------


class TestRunStartupSync:
    @patch("app.tasks.scheduler.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.tasks.scheduler.settings")
    async def test_retries_when_airflow_unavailable(self, mock_settings, mock_sleep):
        """When Airflow is never healthy, run_startup_sync retries and gives up."""
        mock_settings.airflow_startup_max_attempts = 3
        mock_settings.airflow_startup_retry_seconds = 1

        from app.tasks import scheduler

        health_check = AsyncMock(return_value=False)

        with patch(
            "app.integrations.airflow_client.airflow_client"
        ) as mock_client:
            mock_client.check_health = health_check
            await scheduler.run_startup_sync()

        # Should have been called max_attempts times
        assert health_check.await_count == 3
        # Should have slept between retries (max_attempts - 1 times)
        assert mock_sleep.await_count == 2

    @patch("app.tasks.scheduler.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.tasks.scheduler.settings")
    async def test_succeeds_when_airflow_becomes_available(self, mock_settings, mock_sleep):
        """run_startup_sync succeeds when Airflow becomes available on the Nth attempt."""
        mock_settings.airflow_startup_max_attempts = 5
        mock_settings.airflow_startup_retry_seconds = 1

        from app.tasks import scheduler

        # Fail twice, succeed on 3rd attempt
        health_check = AsyncMock(side_effect=[False, False, True])
        sync_fn = AsyncMock()
        poll_fn = AsyncMock()
        catalog_fn = AsyncMock()
        bouncer_fn = AsyncMock()
        usage_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch("app.integrations.airflow_client.airflow_client") as mock_client,
            patch("app.tasks.airflow_sync_task.sync_pipelines_from_airflow", sync_fn),
            patch("app.tasks.airflow_poll_task.poll_airflow_statuses", poll_fn),
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", catalog_fn),
            patch("app.tasks.seed_bouncer_volumes.seed_bouncer_volumes", bouncer_fn),
            patch("app.tasks.seed_usage_data.seed_usage_data", usage_fn),
            patch("app.cache.clear_all", clear_fn),
        ):
            mock_client.check_health = health_check
            await scheduler.run_startup_sync()

        assert health_check.await_count == 3
        sync_fn.assert_awaited_once()
        # poll runs only if sync succeeded
        poll_fn.assert_awaited_once()
        clear_fn.assert_called()

    @patch("app.tasks.scheduler.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.tasks.scheduler.settings")
    async def test_succeeds_first_try(self, mock_settings, mock_sleep):
        """When Airflow is immediately healthy, all tasks run without retries."""
        mock_settings.airflow_startup_max_attempts = 5
        mock_settings.airflow_startup_retry_seconds = 1

        from app.tasks import scheduler

        health_check = AsyncMock(return_value=True)
        sync_fn = AsyncMock()
        poll_fn = AsyncMock()
        catalog_fn = AsyncMock()
        bouncer_fn = AsyncMock()
        usage_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch("app.integrations.airflow_client.airflow_client") as mock_client,
            patch("app.tasks.airflow_sync_task.sync_pipelines_from_airflow", sync_fn),
            patch("app.tasks.airflow_poll_task.poll_airflow_statuses", poll_fn),
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", catalog_fn),
            patch("app.tasks.seed_bouncer_volumes.seed_bouncer_volumes", bouncer_fn),
            patch("app.tasks.seed_usage_data.seed_usage_data", usage_fn),
            patch("app.cache.clear_all", clear_fn),
        ):
            mock_client.check_health = health_check
            await scheduler.run_startup_sync()

        assert health_check.await_count == 1
        mock_sleep.assert_not_awaited()
        sync_fn.assert_awaited_once()

    @patch("app.tasks.scheduler.asyncio.sleep", new_callable=AsyncMock)
    @patch("app.tasks.scheduler.settings")
    async def test_poll_skipped_when_sync_fails(self, mock_settings, mock_sleep):
        """When pipeline sync fails, the poll step is skipped."""
        mock_settings.airflow_startup_max_attempts = 1
        mock_settings.airflow_startup_retry_seconds = 1

        from app.tasks import scheduler

        health_check = AsyncMock(return_value=True)
        sync_fn = AsyncMock(side_effect=RuntimeError("sync failed"))
        poll_fn = AsyncMock()
        catalog_fn = AsyncMock()
        bouncer_fn = AsyncMock()
        usage_fn = AsyncMock()
        clear_fn = MagicMock()

        with (
            patch("app.integrations.airflow_client.airflow_client") as mock_client,
            patch("app.tasks.airflow_sync_task.sync_pipelines_from_airflow", sync_fn),
            patch("app.tasks.airflow_poll_task.poll_airflow_statuses", poll_fn),
            patch("app.tasks.catalog_mirror_task.refresh_catalog_mirror", catalog_fn),
            patch("app.tasks.seed_bouncer_volumes.seed_bouncer_volumes", bouncer_fn),
            patch("app.tasks.seed_usage_data.seed_usage_data", usage_fn),
            patch("app.cache.clear_all", clear_fn),
        ):
            mock_client.check_health = health_check
            await scheduler.run_startup_sync()

        sync_fn.assert_awaited_once()
        poll_fn.assert_not_awaited()
        # Other tasks still run independently
        catalog_fn.assert_awaited_once()
