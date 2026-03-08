"""APScheduler setup for background tasks."""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler() -> AsyncIOScheduler:
    """Configure and return the scheduler with all background tasks."""
    from app.tasks.airflow_poll_task import poll_airflow_statuses
    from app.tasks.git_pull_task import sync_from_git
    from app.tasks.catalog_sync_task import sync_from_catalog

    # Git pull + re-parse ETL code
    scheduler.add_job(
        sync_from_git,
        "interval",
        minutes=settings.git_pull_interval_minutes,
        id="git_pull",
        name="Git Pull & Parse ETLs",
        replace_existing=True,
    )

    # Airflow status poll
    scheduler.add_job(
        poll_airflow_statuses,
        "interval",
        minutes=settings.airflow_poll_interval_minutes,
        id="airflow_poll",
        name="Airflow Status Poll",
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
    )

    logger.info(
        "Scheduler configured: git_pull=%dmin, airflow_poll=%dmin, catalog_sync=2h",
        settings.git_pull_interval_minutes,
        settings.airflow_poll_interval_minutes,
    )
    return scheduler
