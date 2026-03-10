"""APScheduler setup for background tasks.

Uses an asyncio.Lock to prevent concurrent sync/poll executions, avoiding
race conditions on shared DB tables (pipelines, airflow_run_statuses,
pipeline_run_history).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Prevents concurrent sync/poll from overlapping (startup vs catch-up vs interval)
_sync_lock = asyncio.Lock()


async def _guarded_sync() -> None:
    """Run pipeline sync + poll under a lock so they never overlap."""
    if _sync_lock.locked():
        logger.info("Skipping sync — another sync is already running")
        return
    async with _sync_lock:
        from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
        from app.tasks.airflow_poll_task import poll_airflow_statuses
        try:
            await sync_pipelines_from_airflow()
            await poll_airflow_statuses()
        except Exception:
            logger.exception("Scheduled sync/poll cycle failed")
        finally:
            from app.cache import clear_all
            clear_all()


async def _guarded_poll() -> None:
    """Run poll under a lock so it doesn't overlap with sync."""
    if _sync_lock.locked():
        logger.info("Skipping poll — a sync is already running")
        return
    async with _sync_lock:
        from app.tasks.airflow_poll_task import poll_airflow_statuses
        try:
            await poll_airflow_statuses()
        except Exception:
            logger.exception("Scheduled poll failed")
        finally:
            from app.cache import clear_all
            clear_all()


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the scheduler with all background tasks.

    Jobs start after their first interval, NOT immediately — the initial
    sync is handled by _startup_sync in main.py to ensure correct ordering.
    Sync and poll are guarded by _sync_lock to prevent concurrent DB mutations.
    """
    from app.tasks.catalog_sync_task import sync_from_catalog

    now = datetime.now(timezone.utc)

    # Airflow pipeline discovery + poll (guarded against overlap)
    scheduler.add_job(
        _guarded_sync,
        "interval",
        minutes=settings.airflow_poll_interval_minutes,
        id="airflow_pipeline_sync",
        name="Airflow Pipeline Discovery + Poll",
        replace_existing=True,
        next_run_time=now + timedelta(minutes=settings.airflow_poll_interval_minutes),
    )

    # One-shot catch-up sync 5 minutes after startup (Airflow may not be ready at boot)
    scheduler.add_job(
        _guarded_sync,
        "date",
        run_date=now + timedelta(minutes=5),
        id="airflow_catchup_sync",
        name="Airflow Catch-up Sync (5min)",
        replace_existing=True,
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
        "Scheduler configured: catchup=5min, airflow_sync_poll=%dmin, catalog_sync=2h",
        settings.airflow_poll_interval_minutes,
    )
    return scheduler
