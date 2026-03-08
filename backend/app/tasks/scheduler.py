"""APScheduler setup for background tasks."""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the scheduler with all background tasks.

    Jobs start after their first interval, NOT immediately — the initial
    sync is handled by _startup_sync in main.py to ensure correct ordering.
    """
    from app.tasks.airflow_poll_task import poll_airflow_statuses
    from app.tasks.airflow_sync_task import sync_pipelines_from_airflow
    from app.tasks.catalog_sync_task import sync_from_catalog

    now = datetime.now()

    # Airflow pipeline discovery (replaces git pull + code parsing)
    scheduler.add_job(
        sync_pipelines_from_airflow,
        "interval",
        minutes=settings.airflow_poll_interval_minutes,
        id="airflow_pipeline_sync",
        name="Airflow Pipeline Discovery",
        replace_existing=True,
        next_run_time=now + timedelta(minutes=settings.airflow_poll_interval_minutes),
    )

    # Airflow status poll
    scheduler.add_job(
        poll_airflow_statuses,
        "interval",
        minutes=settings.airflow_poll_interval_minutes,
        id="airflow_poll",
        name="Airflow Status Poll",
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
        "Scheduler configured: airflow_sync=%dmin, airflow_poll=%dmin, catalog_sync=2h",
        settings.airflow_poll_interval_minutes,
        settings.airflow_poll_interval_minutes,
    )
    return scheduler
