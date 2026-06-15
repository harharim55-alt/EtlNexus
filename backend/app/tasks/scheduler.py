"""APScheduler setup for background tasks.

The only background job is the Spark Connect catalog mirror (Spark -> Postgres),
which refreshes the catalog mirror and projects schemas onto data products.
"""

import asyncio
import logging

from apscheduler import AsyncScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings

logger = logging.getLogger(__name__)

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
    """Initial startup work: ensure configured teams exist, then refresh the catalog mirror."""
    from app.tasks.seed_teams import seed_teams

    try:
        await seed_teams()
    except Exception:
        logger.exception("Startup seed teams failed")

    async with _mirror_lock:
        from app.tasks.catalog_mirror_task import refresh_catalog_mirror
        try:
            await refresh_catalog_mirror()
        except Exception:
            logger.exception("Startup catalog mirror refresh failed")

    from app.cache import clear_all
    clear_all()


async def setup_scheduler() -> AsyncScheduler:
    """Configure and return the scheduler with the catalog-mirror job.

    The job starts after its first interval, NOT immediately — the initial seed +
    catalog refresh is handled by run_startup_sync().
    """
    scheduler = AsyncScheduler()
    # APScheduler 4.x requires entering the context manager before adding schedules
    await scheduler.__aenter__()

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

    logger.info("Scheduler configured: catalog_mirror=%ds", mirror_interval)
    return scheduler
