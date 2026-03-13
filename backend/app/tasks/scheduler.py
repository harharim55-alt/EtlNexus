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


async def run_startup_sync() -> None:
    """Run the initial sync at startup, waiting for Airflow to be ready.

    Waits for Airflow health (up to 5 min), then runs all sync tasks under
    _sync_lock to prevent overlap with scheduled jobs.  Each task has its own
    error handling so independent tasks proceed even if others fail.
    """
    from app.integrations.airflow_client import airflow_client

    # Wait for Airflow to become available (up to 5 min, poll every 15s)
    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        if await airflow_client.check_health():
            logger.info("Airflow is ready (attempt %d)", attempt)
            break
        if attempt < max_attempts:
            logger.info(
                "Airflow not ready (attempt %d/%d), retrying in 15s",
                attempt, max_attempts,
            )
            await asyncio.sleep(15)
    else:
        logger.warning(
            "Airflow not available after %d attempts — scheduler will retry at next interval",
            max_attempts,
        )
        return

    async with _sync_lock:
        from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
        from app.tasks.airflow_poll_task import poll_airflow_statuses
        from app.tasks.catalog_sync_task import sync_from_catalog
        from app.tasks.seed_usage_data import seed_usage_data

        pipeline_sync_ok = False
        try:
            await sync_pipelines_from_airflow()
            pipeline_sync_ok = True
        except Exception:
            logger.exception("Startup pipeline sync failed")

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
        "Scheduler configured: airflow_sync_poll=%dmin, catalog_sync=2h",
        settings.airflow_poll_interval_minutes,
    )
    return scheduler
