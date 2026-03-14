"""APScheduler setup for background tasks.

Uses an asyncio.Lock to prevent concurrent sync/poll executions, avoiding
race conditions on shared DB tables (pipelines, airflow_run_statuses,
pipeline_run_history).
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Separate locks allow sync and poll to run independently
_sync_lock = asyncio.Lock()
_poll_lock = asyncio.Lock()


async def _guarded_sync() -> None:
    """Run pipeline sync under its own lock."""
    if _sync_lock.locked():
        logger.info("Skipping sync — another sync is already running")
        return
    async with _sync_lock:
        from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
        try:
            await sync_pipelines_from_airflow()
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
        except Exception:
            logger.exception("Scheduled status poll failed")
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
        from app.tasks.catalog_sync_task import sync_from_catalog
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
            await sync_from_catalog()
        except Exception:
            logger.exception("Startup catalog sync failed")

        if pipeline_sync_ok:
            try:
                await poll_airflow_statuses()
            except Exception:
                logger.exception("Startup status poll failed")
        else:
            logger.warning("Skipping startup poll — pipeline sync did not succeed")

        from app.cache import clear_all
        clear_all()


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the scheduler with all background tasks.

    Jobs start after their first interval, NOT immediately — the initial
    sync is handled by run_startup_sync() which waits for Airflow readiness
    and runs under _sync_lock to prevent concurrent DB mutations.
    """
    from app.tasks.catalog_sync_task import sync_from_catalog

    now = datetime.now(UTC)

    # Airflow pipeline discovery (independent from poll)
    scheduler.add_job(
        _guarded_sync,
        "interval",
        minutes=settings.airflow_poll_interval_minutes,
        id="airflow_pipeline_sync",
        name="Airflow Pipeline Discovery",
        replace_existing=True,
        next_run_time=now + timedelta(minutes=settings.airflow_poll_interval_minutes),
    )

    # Airflow status poll (runs independently, offset by 2 min)
    scheduler.add_job(
        _guarded_poll,
        "interval",
        minutes=settings.airflow_poll_interval_minutes,
        id="airflow_status_poll",
        name="Airflow Status Poll",
        replace_existing=True,
        next_run_time=now + timedelta(minutes=settings.airflow_poll_interval_minutes, seconds=120),
    )

    # Catalog sync (every 2 hours)
    scheduler.add_job(
        sync_from_catalog,
        "interval",
        hours=2,
        id="catalog_sync",
        name="Iceberg Catalog Sync",
        replace_existing=True,
        next_run_time=now + timedelta(hours=1),
    )

    logger.info(
        "Scheduler configured: airflow_sync=%dmin, airflow_poll=%dmin, catalog_sync=2h",
        settings.airflow_poll_interval_minutes,
        settings.airflow_poll_interval_minutes,
    )
    return scheduler
