"""Background task: Git pull + ETL code re-parse."""

import logging

from app.database import async_session_factory
from app.services.git_service import GitService

logger = logging.getLogger(__name__)


async def sync_from_git() -> None:
    """Pull latest Git changes and re-parse ETL files."""
    logger.info("Starting scheduled Git sync")
    try:
        async with async_session_factory() as session:
            service = GitService(session)
            count = await service.sync_from_git()
            logger.info("Git sync completed: %d pipelines synced", count)
    except Exception:
        logger.exception("Git sync task failed")
