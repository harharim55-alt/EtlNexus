"""APScheduler setup for background tasks.

The catalog mirror (Spark Connect -> Postgres) always runs. When
``settings.activate_airflow`` is set, the Airflow pipeline-sync and status-poll
jobs run too, gated behind their own locks to avoid concurrent DB mutations.
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
    """Run Airflow pipeline sync under its own lock."""
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
    """Run Airflow status poll under its own lock."""
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
            from app.routers.health import report_sync_completed
            report_sync_completed()
        except Exception:
            logger.exception("Scheduled catalog mirror refresh failed")
        finally:
            from app.cache import clear_all
            clear_all()


async def run_startup_sync() -> None:
    """Initial startup work: seed data + catalog mirror, and (if enabled) Airflow.

    When ``activate_airflow`` is set, waits for Airflow health, then runs pipeline
    discovery before seeding so bouncer volumes attach to discovered pipelines,
    and runs the status poll at the end. The catalog mirror + seeds always run.
    """
    pipeline_sync_ok = False

    if settings.activate_airflow:
        from app.integrations.airflow_client import airflow_client

        # Wait for Airflow to become available
        max_attempts = settings.airflow_startup_max_attempts
        retry_seconds = settings.airflow_startup_retry_seconds
        airflow_ready = False
        for attempt in range(1, max_attempts + 1):
            if await airflow_client.check_health():
                logger.info("Airflow is ready (attempt %d)", attempt)
                airflow_ready = True
                break
            if attempt < max_attempts:
                logger.info(
                    "Airflow not ready (attempt %d/%d), retrying in %ds",
                    attempt, max_attempts, retry_seconds,
                )
                await asyncio.sleep(retry_seconds)

        if airflow_ready:
            async with _sync_lock:
                from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
                try:
                    await sync_pipelines_from_airflow()
                    pipeline_sync_ok = True
                except Exception:
                    logger.exception("Startup pipeline sync failed")
        else:
            logger.warning(
                "Airflow not available after %d attempts — sync will retry at next interval",
                max_attempts,
            )

    # Always: seed bouncer volumes + usage, then refresh the catalog mirror
    from app.tasks.seed_bouncer_volumes import seed_bouncer_volumes
    from app.tasks.seed_usage_data import seed_usage_data

    try:
        await seed_bouncer_volumes()
    except Exception:
        logger.exception("Startup seed bouncer volumes failed")

    try:
        await seed_usage_data()
    except Exception:
        logger.exception("Startup seed usage data failed")

    async with _mirror_lock:
        from app.tasks.catalog_mirror_task import refresh_catalog_mirror
        try:
            await refresh_catalog_mirror()
        except Exception:
            logger.exception("Startup catalog mirror refresh failed")

    # Airflow status poll runs only after a successful discovery
    if settings.activate_airflow and pipeline_sync_ok:
        from app.tasks.airflow_poll_task import poll_airflow_statuses
        try:
            await poll_airflow_statuses()
        except Exception:
            logger.exception("Startup status poll failed")

    from app.cache import clear_all
    clear_all()


async def setup_scheduler() -> AsyncScheduler:
    """Configure and return the scheduler with all background tasks.

    Jobs start after their first interval, NOT immediately — the initial
    seed + catalog refresh (+ Airflow sync when enabled) is handled by
    run_startup_sync().
    """
    scheduler = AsyncScheduler()
    # APScheduler 4.x requires entering the context manager before adding schedules
    await scheduler.__aenter__()

    # Airflow discovery + status poll (only when enabled)
    if settings.activate_airflow:
        await scheduler.add_schedule(
            _guarded_sync,
            IntervalTrigger(minutes=settings.airflow_poll_interval_minutes),
            id="airflow_pipeline_sync",
        )
        await scheduler.add_schedule(
            _guarded_poll,
            IntervalTrigger(minutes=settings.airflow_poll_interval_minutes),
            id="airflow_status_poll",
        )

    # Spark Connect catalog mirror — always on. Refreshes the Postgres mirror +
    # projects pipeline fields every CATALOG_MIRROR_INTERVAL_SECONDS.
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
        "Scheduler configured: airflow=%s, catalog_mirror=%ds, retention=%dd",
        settings.activate_airflow,
        mirror_interval,
        settings.run_history_retention_days,
    )
    return scheduler
