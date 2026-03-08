"""Git integration service — clones/pulls repo and parses ETL code for lineage."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.git_client import git_client
from app.parsers.etl_code_parser import ParsedETL, etl_code_parser
from app.repositories.dag_network_repo import DagNetworkRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository

logger = logging.getLogger(__name__)


class GitService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.pipeline_repo = PipelineRepository(session)
        self.lineage_repo = LineageRepository(session)
        self.dag_network_repo = DagNetworkRepository(session)

    async def sync_from_git(self) -> int:
        """Clone/pull the Git repo, parse ETL files, and update pipelines + lineage.

        Returns the number of pipelines synced.
        """
        # Step 1: Clone or pull
        git_client.clone_or_pull()

        dagger_path = git_client.get_dagger_path()
        if not dagger_path.exists():
            logger.warning("Dagger path does not exist: %s", dagger_path)
            return 0

        # Step 2: Parse all ETL files
        parsed_etls = etl_code_parser.parse_directory(dagger_path)
        if not parsed_etls:
            logger.info("No ETL files found in %s", dagger_path)
            return 0

        # Step 3: Upsert pipelines and lineage
        synced = 0
        for etl in parsed_etls:
            await self._sync_single_etl(etl)
            synced += 1

        await self.session.commit()
        logger.info("Synced %d ETL pipelines from Git", synced)
        return synced

    async def _sync_single_etl(self, etl: ParsedETL) -> None:
        """Upsert a single ETL pipeline and its lineage edges."""
        # Convert class name to display name: "ShopifySalesSync" -> "Shopify Sales Sync"
        display_name = self._class_to_display_name(etl.class_name)

        # Upsert pipeline
        pipeline = await self.pipeline_repo.upsert({
            "name": display_name,
            "description": f"Auto-discovered from {etl.code_path}",
            "category": etl.category,
            "schedule": etl.schedule,
            "code_path": etl.code_path,
        })

        # Clear existing lineage
        await self.lineage_repo.delete_by_pipeline_id(pipeline.id)

        # Create "reads_from" edges for each source table
        for source in etl.source_tables:
            await self.lineage_repo.upsert_edge({
                "target_pipeline_id": pipeline.id,
                "source_table": source,
                "target_table": etl.target_table or display_name.lower().replace(" ", "_"),
                "edge_type": "reads_from",
            })

        # Create "writes_to" edges for destination tables
        for dest in etl.destination_tables:
            await self.lineage_repo.upsert_edge({
                "source_pipeline_id": pipeline.id,
                "source_table": etl.target_table or display_name.lower().replace(" ", "_"),
                "target_table": dest,
                "edge_type": "writes_to",
            })

        # Sync DAG networks
        if etl.networks:
            await self.dag_network_repo.replace_for_pipeline(pipeline.id, etl.networks)

    @staticmethod
    def _class_to_display_name(class_name: str) -> str:
        """Convert CamelCase class name to display name.

        E.g., "ShopifySalesSync" -> "Shopify Sales Sync"
        """
        result = []
        for i, char in enumerate(class_name):
            if char.isupper() and i > 0:
                result.append(" ")
            result.append(char)
        return "".join(result)
