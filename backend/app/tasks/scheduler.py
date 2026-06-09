"""APScheduler setup for background tasks.

Uses an asyncio.Lock to prevent overlapping catalog-mirror refreshes, avoiding
race conditions on shared DB tables (catalog_columns, pipeline_fields).
"""

import asyncio
import logging

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

# Guards the catalog mirror so a slow refresh can't overlap the next tick.
_mirror_lock = asyncio.Lock()


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
    """Run the initial seed + catalog-mirror refresh at startup.

    Seeds bouncer volumes and usage data, then refreshes the catalog mirror
    (under _mirror_lock to avoid overlapping the scheduled refresh). Each step
    has its own error handling so one failure doesn't block the others.
    """
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

    from app.cache import clear_all
    clear_all()


async def setup_scheduler() -> AsyncScheduler:
    """Configure and return the scheduler with all background tasks.

    Jobs start after their first interval, NOT immediately — the initial
    seed + catalog refresh is handled by run_startup_sync().
    """
    scheduler = AsyncScheduler()
    # APScheduler 4.x requires entering the context manager before adding schedules
    await scheduler.__aenter__()

    # Spark Connect catalog mirror — refreshes the Postgres mirror + projects
    # pipeline fields every CATALOG_MIRROR_INTERVAL_SECONDS.
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
        "Scheduler configured: catalog_mirror=%ds, retention=%dd",
        mirror_interval,
        settings.run_history_retention_days,
    )
    return scheduler
