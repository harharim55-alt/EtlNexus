"""Airflow sync service — discovers pipelines and lineage from Airflow task metadata.

Replaces the git-based code parsing pipeline. All pipeline metadata (name, category,
schedule, lineage) is now sourced from Airflow task op_kwargs.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.airflow_client import airflow_client
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository

logger = logging.getLogger(__name__)


class AirflowSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.pipeline_repo = PipelineRepository(session)
        self.lineage_repo = LineageRepository(session)

    async def sync_pipelines_from_airflow(self) -> int:
        """Discover all tasks across all DAGs and register as pipelines + lineage.

        Each Airflow task's op_kwargs carries:
          - etl_name, needs, prefers, category, schedule

        Destination tables are discovered from task logs:
          - ETL_WRITES_TO: {table_name} lines logged by run_etl
          - Primary table = task_id (naming convention)

        Returns the number of pipelines synced.
        """
        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            logger.warning("No DAGs found in Airflow — skipping pipeline sync")
            return 0

        # Collect unique task metadata across all DAGs.
        # A task can appear in multiple DAGs — we take the first occurrence's metadata.
        seen_tasks: dict[str, dict] = {}

        for dag_info in all_dags:
            dag_id = dag_info["dag_id"]

            runs = await airflow_client.get_dag_runs(dag_id, limit=1)
            if not runs:
                continue

            run = runs[0]
            dag_run_id = run.get("dag_run_id")
            if not dag_run_id:
                continue

            instances = await airflow_client.get_task_instances(dag_id, dag_run_id)
            for inst in instances:
                task_id = inst.get("task_id", "")
                if task_id in seen_tasks:
                    continue

                rendered = inst.get("rendered_fields", {}) or {}
                op_kwargs = rendered.get("op_kwargs", {}) or {}

                if not op_kwargs.get("etl_name"):
                    continue

                # Parse destination tables from task logs
                log_content = await airflow_client.get_task_log(
                    dag_id, dag_run_id, task_id
                )
                destination_tables = self._parse_writes(log_content, task_id)
                description = self._parse_description(log_content, task_id)

                seen_tasks[task_id] = {
                    "task_id": task_id,
                    "category": op_kwargs.get("category", ""),
                    "schedule": op_kwargs.get("schedule"),
                    "destination_tables": destination_tables,
                    "description": description,
                    "needs": op_kwargs.get("needs", []),
                }

        if not seen_tasks:
            logger.info("No tasks with etl metadata found in Airflow")
            return 0

        # Upsert pipelines and lineage
        synced = 0
        for task_id, meta in seen_tasks.items():
            display_name = self._task_id_to_display_name(task_id)

            pipeline = await self.pipeline_repo.upsert({
                "name": display_name,
                "description": meta["description"],
                "category": meta["category"],
                "schedule": meta["schedule"],
            })

            # Clear existing lineage for this pipeline
            await self.lineage_repo.delete_by_pipeline_id(pipeline.id)

            # Primary table = task_id (naming convention)
            primary_table = task_id

            # Create "reads_from" edges from needs (upstream dependencies)
            for upstream_task_id in meta["needs"]:
                await self.lineage_repo.upsert_edge({
                    "target_pipeline_id": pipeline.id,
                    "source_table": upstream_task_id,
                    "target_table": primary_table,
                    "edge_type": "reads_from",
                })

            # Create "writes_to" edges from log-discovered tables (skip APIs)
            if meta["category"] != "API":
                for dest in meta["destination_tables"]:
                    await self.lineage_repo.upsert_edge({
                        "source_pipeline_id": pipeline.id,
                        "source_table": primary_table,
                        "target_table": dest,
                        "edge_type": "writes_to",
                    })

            synced += 1

        await self.session.commit()
        logger.info("Synced %d pipelines from Airflow", synced)
        return synced

    @staticmethod
    def _parse_writes(log_content: str, task_id: str) -> list[str]:
        """Parse ETL_WRITES_TO lines from a task's log output."""
        if not log_content:
            return [task_id]
        tables = []
        for line in log_content.splitlines():
            if "ETL_WRITES_TO:" in line:
                parts = line.split("ETL_WRITES_TO:", 1)
                if len(parts) == 2:
                    table = parts[1].strip()
                    if table:
                        tables.append(table)
        return tables if tables else [task_id]

    @staticmethod
    def _parse_description(log_content: str, task_id: str) -> str:
        """Parse ETL_DESCRIPTION line from a task's log output."""
        if log_content:
            for line in log_content.splitlines():
                if "ETL_DESCRIPTION:" in line:
                    parts = line.split("ETL_DESCRIPTION:", 1)
                    if len(parts) == 2:
                        desc = parts[1].strip()
                        if desc:
                            return desc
        return task_id.replace("_", " ").title()

    @staticmethod
    def _task_id_to_display_name(task_id: str) -> str:
        """Convert snake_case task_id to display name.

        E.g., "shopify_sales_sync" -> "Shopify Sales Sync"
             "customer_360_enrichment" -> "Customer 360 Enrichment"
        """
        return task_id.replace("_", " ").title()
