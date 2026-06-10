"""Background task: Poll Airflow DAG run statuses every 20 minutes."""

import logging

from app.database import async_session_factory
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.bouncer_repo import BouncerRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.services.airflow_service import AirflowService

logger = logging.getLogger(__name__)


async def poll_airflow_statuses() -> None:
    """Poll Airflow for latest DAG run statuses."""
    logger.info("Starting scheduled Airflow status poll")
    try:
        async with async_session_factory() as session:
            service = AirflowService(
                session,
                airflow_repo=AirflowRepository(session),
                pipeline_repo=PipelineRepository(session),
                resource_repo=ResourceRepository(session),
                bouncer_repo=BouncerRepository(session),
            )
            count = await service.poll_all_statuses()
            logger.info("Airflow poll completed: %d pipelines updated", count)
    except Exception:
        logger.exception("Airflow poll task failed")
