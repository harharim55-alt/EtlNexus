"""Background task: Delete old pipeline run history records."""

import logging

from sqlalchemy import delete, func, select

from app.config import settings
from app.database import async_session_factory
from app.models.run_history import PipelineRunHistory

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


async def cleanup_run_history() -> None:
    """Delete pipeline_run_history rows older than the configured retention period.

    Deletes in batches to avoid long-held locks.
    """
    retention_days = settings.run_history_retention_days
    if retention_days <= 0:
        return

    logger.info("Starting run history cleanup (retention: %d days)", retention_days)
    total_deleted = 0

    try:
        async with async_session_factory() as session:
            cutoff = func.now() - func.make_interval(0, 0, 0, retention_days)

            while True:
                # Select a batch of IDs to delete
                batch_ids_stmt = (
                    select(PipelineRunHistory.id)
                    .where(PipelineRunHistory.recorded_at < cutoff)
                    .limit(_BATCH_SIZE)
                )
                batch_result = await session.execute(batch_ids_stmt)
                ids_to_delete = [row[0] for row in batch_result.all()]

                if not ids_to_delete:
                    break

                await session.execute(
                    delete(PipelineRunHistory).where(
                        PipelineRunHistory.id.in_(ids_to_delete)
                    )
                )
                await session.commit()
                total_deleted += len(ids_to_delete)
                logger.debug("Deleted batch of %d run history rows", len(ids_to_delete))

    except Exception:
        logger.exception("Run history cleanup failed")
        return

    logger.info("Run history cleanup completed: %d rows deleted", total_deleted)
