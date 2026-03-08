"""DAG network service — syncs DAG network associations for pipelines."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.etl_dags_client import etl_dags_client
from app.repositories.dag_network_repo import DagNetworkRepository
from app.repositories.pipeline_repo import PipelineRepository

logger = logging.getLogger(__name__)


class DagNetworkService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.pipeline_repo = PipelineRepository(session)
        self.dag_network_repo = DagNetworkRepository(session)

    async def sync_dag_networks(self) -> int:
        """Sync DAG network associations from the etl_dags module.

        Returns number of pipelines updated.
        """
        dag_mapping = etl_dags_client.get_etl_dags()
        if not dag_mapping:
            logger.info("No DAG network data available")
            return 0

        pipelines = await self.pipeline_repo.get_all()
        pipeline_by_name = {p.name.lower().replace(" ", "_"): p for p in pipelines}

        updated = 0
        for pipeline_key, networks in dag_mapping.items():
            pipeline = pipeline_by_name.get(pipeline_key.lower())
            if not pipeline:
                continue

            network_names = networks if isinstance(networks, list) else [str(networks)]
            await self.dag_network_repo.replace_for_pipeline(pipeline.id, network_names)
            updated += 1

        await self.session.commit()
        logger.info("Updated DAG networks for %d pipelines", updated)
        return updated
