"""APScheduler setup for background tasks.

Uses an asyncio.Lock to prevent concurrent sync/poll executions, avoiding
race conditions on shared DB tables (pipelines, airflow_run_statuses,
pipeline_run_history).
"""

import asyncio
import logging

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Separate locks allow sync, poll, and catalog mirror to run independently
_sync_lock = asyncio.Lock()
_poll_lock = asyncio.Lock()
_mirror_lock = asyncio.Lock()


async def _guarded_sync() -> None:
    """Run pipeline sync under its own lock."""
    if _sync_lock.locked():
        logger.info("Skipping sync — another sync is already running")
        return
    async with _sync_lock:
        from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
        try:
            await sync_pipelines_from_airflow()
            from app.routers.health import report_sync_completed
            report_sync_completed()
        except Exception:
            logger.exception("Scheduled pipeline sync failed")
        finally:
            from app.cache import clear_all
            clear_all()


async def _guarded_poll() -> None:
    """Run status poll under its own lock."""
    if _poll_lock.locked():
        logger.info("Skipping poll — another poll is already running")
        return
    async with _poll_lock:
        from app.tasks.airflow_poll_task import poll_airflow_statuses
        try:
            await poll_airflow_statuses()
            from app.routers.health import report_sync_completed
            report_sync_completed()
        except Exception:
            logger.exception("Scheduled status poll failed")
        finally:
            from app.cache import clear_all
            clear_all()


async def _guarded_mirror() -> None:
    """Refresh the Spark Connect catalog mirror under its own lock.

    Skips this tick if the previous refresh is still running — important at the
    30-second cadence, where a slow Spark read could otherwise overlap the next.
    """
    if _mirror_lock.locked():
        logger.info("Skipping catalog mirror — previous refresh still running")
        return
    async with _mirror_lock:
        from app.tasks.catalog_mirror_task import refresh_catalog_mirror
        try:
            await refresh_catalog_mirror()
        except Exception:
            logger.exception("Scheduled catalog mirror refresh failed")
        finally:
            from app.cache import clear_all
            clear_all()


async def run_startup_sync() -> None:
    """Run the initial sync at startup, waiting for Airflow to be ready.

    Waits for Airflow health (up to 5 min), then runs all sync tasks under
    _sync_lock to prevent overlap with scheduled jobs.  Each task has its own
    error handling so independent tasks proceed even if others fail.
    """
    from app.integrations.airflow_client import airflow_client

    # Wait for Airflow to become available
    max_attempts = settings.airflow_startup_max_attempts
    retry_seconds = settings.airflow_startup_retry_seconds
    for attempt in range(1, max_attempts + 1):
        if await airflow_client.check_health():
            logger.info("Airflow is ready (attempt %d)", attempt)
            break
        if attempt < max_attempts:
            logger.info(
                "Airflow not ready (attempt %d/%d), retrying in %ds",
                attempt, max_attempts, retry_seconds,
            )
            await asyncio.sleep(retry_seconds)
    else:
        logger.warning(
            "Airflow not available after %d attempts — scheduler will retry at next interval",
            max_attempts,
        )
        return

    async with _sync_lock:
        from app.tasks.airflow_poll_task import poll_airflow_statuses
        from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
        from app.tasks.catalog_mirror_task import refresh_catalog_mirror
        from app.tasks.seed_bouncer_volumes import seed_bouncer_volumes
        from app.tasks.seed_usage_data import seed_usage_data

        pipeline_sync_ok = False
        try:
            await sync_pipelines_from_airflow()
            pipeline_sync_ok = True
        except Exception:
            logger.exception("Startup pipeline sync failed")

        try:
            await seed_bouncer_volumes()
        except Exception:
            logger.exception("Startup seed bouncer volumes failed")

        try:
            await seed_usage_data()
        except Exception:
            logger.exception("Startup seed usage data failed")

        try:
            await refresh_catalog_mirror()
        except Exception:
            logger.exception("Startup catalog mirror refresh failed")

        if pipeline_sync_ok:
            try:
                await poll_airflow_statuses()
            except Exception:
                logger.exception("Startup status poll failed")
        else:
            logger.warning("Skipping startup poll — pipeline sync did not succeed")

        from app.cache import clear_all
        clear_all()


async def setup_scheduler() -> AsyncScheduler:
    """Configure and return the scheduler with all background tasks.

    Jobs start after their first interval, NOT immediately — the initial
    sync is handled by run_startup_sync() which waits for Airflow readiness
    and runs under _sync_lock to prevent concurrent DB mutations.
    """
    scheduler = AsyncScheduler()
    # APScheduler 4.x requires entering the context manager before adding schedules
    await scheduler.__aenter__()

    # Airflow pipeline discovery (independent from poll)
    await scheduler.add_schedule(
        _guarded_sync,
        IntervalTrigger(minutes=settings.airflow_poll_interval_minutes),
        id="airflow_pipeline_sync",
    )

    # Airflow status poll (runs independently)
    await scheduler.add_schedule(
        _guarded_poll,
        IntervalTrigger(minutes=settings.airflow_poll_interval_minutes),
        id="airflow_status_poll",
    )

    # Spark Connect catalog mirror — the only live Spark reader. Refreshes the
    # Postgres mirror + projects pipeline fields every CATALOG_MIRROR_INTERVAL_SECONDS.
    mirror_interval = settings.catalog_mirror_interval_seconds
    if mirror_interval < 1:
        logger.warning(
            "catalog_mirror_interval_seconds=%s is invalid — defaulting to 30s",
            mirror_interval,
        )
        mirror_interval = 30
    await scheduler.add_schedule(
        _guarded_mirror,
        IntervalTrigger(seconds=mirror_interval),
        id="spark_catalog_mirror",
    )

    # Run history retention (daily)
    if settings.run_history_retention_days > 0:
        from app.tasks.run_history_retention import cleanup_run_history

        await scheduler.add_schedule(
            cleanup_run_history,
            IntervalTrigger(hours=24),
            id="run_history_retention",
        )

    logger.info(
        "Scheduler configured: airflow_sync=%dmin, airflow_poll=%dmin, catalog_mirror=%ds, retention=%dd",
        settings.airflow_poll_interval_minutes,
        settings.airflow_poll_interval_minutes,
        mirror_interval,
        settings.run_history_retention_days,
    )
    return scheduler
