"""Airflow sync service — discovers pipelines and lineage from Airflow task metadata.

Replaces the git-based code parsing pipeline. All pipeline metadata (name, category,
schedule, lineage) is now sourced from Airflow task op_kwargs.
"""

import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.airflow_client import airflow_client
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.services.airflow_service import TASK_STATE_MAP

logger = logging.getLogger(__name__)


class AirflowSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.pipeline_repo = PipelineRepository(session)
        self.lineage_repo = LineageRepository(session)
        self.resource_repo = ResourceRepository(session)
        self.airflow_repo = AirflowRepository(session)
        self.dag_task_repo = DagTaskRepository(session)

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
        # Resource configs per task per DAG (collected before dedup — need all occurrences)
        resource_by_dag: dict[str, dict[str, dict]] = {}
        # DAG task graph data: (dag_id, task_id) -> {downstream_task_ids, needs, prefers}
        dag_task_graph: list[dict] = []

        for dag_info in all_dags:
            dag_id = dag_info["dag_id"]

            # Fetch task definitions for downstream_task_ids and params fallback
            tasks_def = await airflow_client.get_dag_tasks(dag_id)
            downstream_map = {
                t["task_id"]: t.get("downstream_task_ids", []) for t in tasks_def
            }
            # params from task definitions — always available, even for upstream_failed tasks
            # Airflow wraps param values in Param objects: {"key": {"__class": "...", "value": X}}
            params_by_task = {
                t["task_id"]: self._unwrap_params(t.get("params", {}))
                for t in tasks_def
            }

            runs = await airflow_client.get_dag_runs(dag_id, limit=1)
            if not runs:
                continue

            run = runs[0]
            dag_run_id = run.get("dag_run_id")
            if not dag_run_id:
                continue

            instances = await airflow_client.get_task_instances(dag_id, dag_run_id)
            op_kwargs_by_task: dict[str, dict] = {}

            for inst in instances:
                task_id = inst.get("task_id", "")

                rendered = inst.get("rendered_fields", {}) or {}
                op_kwargs = rendered.get("op_kwargs", {}) or {}

                # Fall back to task definition params for upstream_failed tasks
                if not op_kwargs.get("etl_name"):
                    params = params_by_task.get(task_id, {})
                    if params.get("etl_name"):
                        logger.debug(
                            "Using params fallback for task %s in DAG %s (state=%s)",
                            task_id, dag_id, inst.get("state", "?"),
                        )
                        op_kwargs = params

                op_kwargs_by_task[task_id] = op_kwargs

                if not op_kwargs.get("etl_name"):
                    if task_id not in seen_tasks:
                        logger.debug(
                            "Skipping task %s in DAG %s — no etl_name in op_kwargs or params (keys: %s)",
                            task_id,
                            dag_id,
                            list(op_kwargs.keys()) if op_kwargs else "empty",
                        )
                    continue

                # Collect resource config for every DAG occurrence (before dedup skip)
                raw_resources = op_kwargs.get("resources")
                if raw_resources and isinstance(raw_resources, dict):
                    resource_by_dag.setdefault(task_id, {})[dag_id] = raw_resources

                if task_id in seen_tasks:
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

            # Build dag_task_graph entries for all ETL tasks in this DAG
            for task_id, op_kwargs in op_kwargs_by_task.items():
                if not op_kwargs.get("etl_name"):
                    continue
                dag_task_graph.append({
                    "dag_id": dag_id,
                    "task_id": task_id,
                    "downstream_task_ids": downstream_map.get(task_id, []),
                    "needs": op_kwargs.get("needs", []),
                    "prefers": op_kwargs.get("prefers", []),
                })

        logger.info("Collected %d ETL tasks from %d DAGs", len(seen_tasks), len(all_dags))

        if not seen_tasks:
            logger.info("No tasks with etl metadata found in Airflow")
            return 0

        # Pass 1: Upsert pipelines and lineage
        synced = 0
        task_id_to_pipeline_id: dict[str, uuid.UUID] = {}

        for task_id, meta in seen_tasks.items():
            display_name = self._task_id_to_display_name(task_id)

            pipeline = await self.pipeline_repo.upsert({
                "name": display_name,
                "task_id": task_id,
                "description": meta["description"],
                "category": meta["category"],
                "schedule": meta["schedule"],
            })
            task_id_to_pipeline_id[task_id] = pipeline.id

            # Primary table = task_id (naming convention)
            primary_table = task_id

            # Build edge data before deleting old edges
            edges_to_create: list[dict] = []

            for upstream_task_id in meta["needs"]:
                edges_to_create.append({
                    "target_pipeline_id": pipeline.id,
                    "source_table": upstream_task_id,
                    "target_table": primary_table,
                    "edge_type": "reads_from",
                })

            if "api" not in meta["category"].lower():
                for dest in meta["destination_tables"]:
                    edges_to_create.append({
                        "source_pipeline_id": pipeline.id,
                        "source_table": primary_table,
                        "target_table": dest,
                        "edge_type": "writes_to",
                    })

            # Atomic delete + recreate within a savepoint
            try:
                async with self.session.begin_nested():
                    await self.lineage_repo.delete_by_pipeline_id(pipeline.id)
                    for edge_data in edges_to_create:
                        await self.lineage_repo.upsert_edge(edge_data)
                synced += 1
            except Exception:
                logger.exception("Failed to sync lineage for pipeline %s", display_name)

        # Pass 2: Resolve source_pipeline_id on reads_from edges
        for task_id, meta in seen_tasks.items():
            pipeline_id = task_id_to_pipeline_id.get(task_id)
            if not pipeline_id:
                continue
            for upstream_task_id in meta["needs"]:
                source_pid = task_id_to_pipeline_id.get(upstream_task_id)
                if source_pid:
                    await self.lineage_repo.upsert_edge({
                        "target_pipeline_id": pipeline_id,
                        "source_pipeline_id": source_pid,
                        "source_table": upstream_task_id,
                        "target_table": task_id,
                        "edge_type": "reads_from",
                    })

        # Pass 3: Sync resource configs (per pipeline per DAG)
        resource_count = 0
        for task_id, dag_map in resource_by_dag.items():
            pipeline_id = task_id_to_pipeline_id.get(task_id)
            if not pipeline_id:
                continue

            # All DAG copies carry the same full resources dict
            raw = next(iter(dag_map.values()))
            default_cfg = raw.get("default", {})

            for dag_id in dag_map:
                override = raw.get(dag_id, {})
                effective = {**default_cfg, **override}
                if not effective:
                    continue
                try:
                    await self.resource_repo.upsert_config({
                        "pipeline_id": pipeline_id,
                        "dag_id": dag_id,
                        "spark_driver_memory": effective.get("spark_driver_memory"),
                        "spark_executor_memory": effective.get("spark_executor_memory"),
                        "spark_executor_cores": effective.get("spark_executor_cores"),
                        "spark_num_executors": effective.get("spark_num_executors"),
                        "is_dag_override": bool(override),
                        "synced_at": datetime.now(timezone.utc).replace(tzinfo=None),
                    })
                    resource_count += 1
                except Exception:
                    logger.exception(
                        "Failed to sync resource config for %s in %s", task_id, dag_id
                    )

        # Pass 4: Sync DAG task graph (membership + downstream edges)
        current_pairs: set[tuple[str, str]] = set()
        for entry in dag_task_graph:
            entry["pipeline_id"] = task_id_to_pipeline_id.get(entry["task_id"])
            await self.dag_task_repo.upsert(entry)
            current_pairs.add((entry["dag_id"], entry["task_id"]))

        stale_deleted = await self.dag_task_repo.delete_stale(current_pairs)
        if stale_deleted:
            logger.info("Deleted %d stale dag_task entries", stale_deleted)

        await self.session.commit()
        logger.info(
            "Synced %d pipelines, %d resource configs, %d dag_task entries from Airflow",
            synced,
            resource_count,
            len(dag_task_graph),
        )
        return synced

    async def sync_single_pipeline(self, pipeline_id: uuid.UUID) -> dict:
        """Re-sync a single pipeline's metadata, lineage, resources, and status from Airflow."""
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        task_id = pipeline.task_id or pipeline.name.lower().replace(" ", "_")
        display_name = pipeline.name
        logger.info("Manual sync started for pipeline %s (task_id=%s)", display_name, task_id)

        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            raise ValueError("No DAGs found in Airflow")

        # Scan all DAGs for this task
        meta: dict | None = None
        resource_by_dag: dict[str, dict] = {}
        found_dags: set[str] = set()
        best_status: str | None = None
        best_dag_id: str | None = None
        best_exec_date: datetime | None = None

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
                if inst.get("task_id") != task_id:
                    continue

                found_dags.add(dag_id)

                rendered = inst.get("rendered_fields", {}) or {}
                op_kwargs = rendered.get("op_kwargs", {}) or {}

                # Collect resource config for every DAG occurrence
                raw_resources = op_kwargs.get("resources")
                if raw_resources and isinstance(raw_resources, dict):
                    resource_by_dag[dag_id] = raw_resources

                # Track best status across DAGs
                state = inst.get("state", "")
                status = TASK_STATE_MAP.get(state, "unknown")
                exec_date = run.get("execution_date") or run.get("logical_date")
                if best_status is None or status == "running" or (
                    status == "success" and best_status != "running"
                ):
                    best_status = status
                    best_dag_id = dag_id
                    best_exec_date = exec_date

                # Only parse metadata from first occurrence
                if meta is not None:
                    break

                log_content = await airflow_client.get_task_log(dag_id, dag_run_id, task_id)
                destination_tables = self._parse_writes(log_content, task_id)
                description = self._parse_description(log_content, task_id)

                meta = {
                    "category": op_kwargs.get("category", ""),
                    "schedule": op_kwargs.get("schedule"),
                    "destination_tables": destination_tables,
                    "description": description,
                    "needs": op_kwargs.get("needs", []),
                }

        if meta is None:
            raise ValueError(f"Task {task_id} not found in any Airflow DAG")

        # Upsert pipeline metadata
        await self.pipeline_repo.upsert({
            "name": display_name,
            "task_id": task_id,
            "description": meta["description"],
            "category": meta["category"],
            "schedule": meta["schedule"],
        })

        # Rebuild lineage edges
        primary_table = task_id
        edges_to_create: list[dict] = []

        for upstream_task_id in meta["needs"]:
            edge: dict = {
                "target_pipeline_id": pipeline_id,
                "source_table": upstream_task_id,
                "target_table": primary_table,
                "edge_type": "reads_from",
            }
            # Resolve source_pipeline_id from DB
            upstream = await self.pipeline_repo.get_by_task_id(upstream_task_id)
            if upstream:
                edge["source_pipeline_id"] = upstream.id
            edges_to_create.append(edge)

        if "api" not in meta["category"].lower():
            for dest in meta["destination_tables"]:
                edges_to_create.append({
                    "source_pipeline_id": pipeline_id,
                    "source_table": primary_table,
                    "target_table": dest,
                    "edge_type": "writes_to",
                })

        try:
            async with self.session.begin_nested():
                await self.lineage_repo.delete_by_pipeline_id(pipeline_id)
                for edge_data in edges_to_create:
                    await self.lineage_repo.upsert_edge(edge_data)
        except Exception:
            logger.exception("Failed to sync lineage for pipeline %s", display_name)

        # Sync resource configs
        for dag_id, raw in resource_by_dag.items():
            default_cfg = raw.get("default", {})
            override = raw.get(dag_id, {})
            effective = {**default_cfg, **override}
            if not effective:
                continue
            try:
                await self.resource_repo.upsert_config({
                    "pipeline_id": pipeline_id,
                    "dag_id": dag_id,
                    "spark_driver_memory": effective.get("spark_driver_memory"),
                    "spark_executor_memory": effective.get("spark_executor_memory"),
                    "spark_executor_cores": effective.get("spark_executor_cores"),
                    "spark_num_executors": effective.get("spark_num_executors"),
                    "is_dag_override": bool(override),
                    "synced_at": datetime.now(timezone.utc).replace(tzinfo=None),
                })
            except Exception:
                logger.exception(
                    "Failed to sync resource config for %s in %s", task_id, dag_id
                )

        # Record run history + actual resource usage (last 5 runs per DAG)
        history_count = 0
        for dag_id in found_dags:
            runs = await airflow_client.get_dag_runs(dag_id, limit=5)
            for run in runs:
                dag_run_id = run.get("dag_run_id")
                if not dag_run_id:
                    continue
                instances = await airflow_client.get_task_instances(dag_id, dag_run_id)
                for inst in instances:
                    if inst.get("task_id") != task_id:
                        continue

                    state = inst.get("state", "unknown")
                    status = TASK_STATE_MAP.get(state, "unknown")
                    duration = inst.get("duration")
                    if duration is None:
                        break

                    start_date = self._parse_datetime(inst.get("start_date"))
                    end_date = self._parse_datetime(inst.get("end_date"))

                    is_new = await self.resource_repo.insert_run_if_new({
                        "pipeline_id": pipeline_id,
                        "dag_id": dag_id,
                        "dag_run_id": dag_run_id,
                        "duration_seconds": duration,
                        "start_date": start_date.replace(tzinfo=None) if start_date else None,
                        "end_date": end_date.replace(tzinfo=None) if end_date else None,
                        "status": status,
                    })
                    if is_new:
                        history_count += 1

                    # Parse actual resource usage for successful runs
                    needs_actuals = False
                    if is_new and status == "success":
                        needs_actuals = True
                    elif not is_new and status == "success":
                        needs_actuals = await self.resource_repo.has_null_actuals(
                            pipeline_id, dag_id, dag_run_id
                        )

                    if needs_actuals:
                        try:
                            log = await airflow_client.get_task_log(dag_id, dag_run_id, task_id)
                            actuals = self._parse_resource_actual(log)
                            if actuals:
                                await self.resource_repo.update_run_actuals(
                                    pipeline_id, dag_id, dag_run_id, actuals
                                )
                        except Exception:
                            logger.debug(
                                "Could not parse resource actuals for %s/%s/%s",
                                dag_id, dag_run_id, task_id,
                            )
                    break  # Found our task in this run, move to next run

        logger.info("Recorded %d new run history entries for %s", history_count, display_name)

        # Upsert Airflow status
        if best_status and best_dag_id:
            clean_exec_date = None
            if best_exec_date:
                if isinstance(best_exec_date, str):
                    try:
                        dt = datetime.fromisoformat(best_exec_date.replace("Z", "+00:00"))
                        clean_exec_date = dt.replace(tzinfo=None)
                    except ValueError:
                        pass
                elif isinstance(best_exec_date, datetime):
                    clean_exec_date = best_exec_date.replace(tzinfo=None)

            await self.airflow_repo.upsert({
                "pipeline_id": pipeline_id,
                "dag_id": best_dag_id,
                "status": best_status,
                "execution_date": clean_exec_date,
                "last_checked_at": datetime.now(timezone.utc).replace(tzinfo=None),
            })

        await self.session.commit()
        logger.info("Manual sync completed for pipeline %s", display_name)
        return {"synced": True, "pipeline_name": display_name}

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
        return task_id.replace("-", "_").replace("_", " ").title()

    @staticmethod
    def _task_id_to_display_name(task_id: str) -> str:
        """Convert task_id to display name, normalizing hyphens.

        E.g., "shopify_sales_sync" -> "Shopify Sales Sync"
             "shopify-sales-sync" -> "Shopify Sales Sync"
             "customer_360_enrichment" -> "Customer 360 Enrichment"
        """
        return task_id.replace("-", "_").replace("_", " ").title()

    @staticmethod
    def _parse_datetime(date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _unwrap_params(raw_params: dict) -> dict:
        """Unwrap Airflow Param objects to plain values.

        Airflow REST API serialises params as:
          {"key": {"__class": "airflow.models.param.Param", "value": X}}
        This extracts the inner 'value' for each key.
        """
        if not raw_params:
            return {}
        result: dict = {}
        for key, val in raw_params.items():
            if isinstance(val, dict) and "value" in val:
                result[key] = val["value"]
            else:
                result[key] = val
        return result

    @staticmethod
    def _parse_resource_actual(log_content: str) -> dict | None:
        """Parse ETL_RESOURCE_ACTUAL JSON from task log."""
        if not log_content:
            return None
        for line in log_content.splitlines():
            if "ETL_RESOURCE_ACTUAL:" in line:
                json_str = line.split("ETL_RESOURCE_ACTUAL:", 1)[1].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
        return None
