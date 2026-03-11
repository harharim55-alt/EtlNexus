"""Airflow sync service — discovers pipelines and lineage from Airflow task metadata.

Replaces the git-based code parsing pipeline. All pipeline metadata (name, category,
schedule, lineage) is now sourced from Airflow task op_kwargs.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

import re

from app.integrations.airflow_client import airflow_client
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.sensor_repo import SensorRepository
from app.repositories.team_repo import TeamRepository
from app.services.airflow_service import TASK_STATE_MAP

logger = logging.getLogger(__name__)

# Limits concurrent Airflow API calls — leaves headroom below httpx max_connections=10
_AIRFLOW_SEMAPHORE = asyncio.Semaphore(6)


class AirflowSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.pipeline_repo = PipelineRepository(session)
        self.lineage_repo = LineageRepository(session)
        self.resource_repo = ResourceRepository(session)
        self.airflow_repo = AirflowRepository(session)
        self.dag_task_repo = DagTaskRepository(session)
        self.sensor_repo = SensorRepository(session)
        self.team_repo = TeamRepository(session)

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
        # Sensor metadata (keyed by sensor_name)
        seen_sensors: dict[str, dict] = {}
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
            # TaskGroup mapping from DAG source — fallback for task_group when
            # rendered op_kwargs is empty (upstream_failed tasks)
            task_group_map = await airflow_client.get_task_group_map(dag_id)

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
                if not op_kwargs.get("etl_name") and not op_kwargs.get("sensor_name"):
                    params = params_by_task.get(task_id, {})
                    if params.get("etl_name") or params.get("sensor_name"):
                        logger.debug(
                            "Using params fallback for task %s in DAG %s (state=%s)",
                            task_id, dag_id, inst.get("state", "?"),
                        )
                        op_kwargs = params

                op_kwargs_by_task[task_id] = op_kwargs

                # Detect sensor tasks (sensor_name in op_kwargs)
                sensor_name = op_kwargs.get("sensor_name")
                if sensor_name:
                    if sensor_name not in seen_sensors:
                        log_content = await airflow_client.get_task_log(
                            dag_id, dag_run_id, task_id
                        )
                        volume = self._parse_sensor_volume(log_content)
                        description = op_kwargs.get("description") or self._parse_sensor_description(log_content, task_id)
                        seen_sensors[sensor_name] = {
                            "sensor_name": sensor_name,
                            "team": op_kwargs.get("team", ""),
                            "description": description,
                            "volume_per_day": volume or op_kwargs.get("volume_per_day"),
                            "dag_ids": [dag_id],
                        }
                    else:
                        if dag_id not in seen_sensors[sensor_name]["dag_ids"]:
                            seen_sensors[sensor_name]["dag_ids"].append(dag_id)
                    continue

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
                    "task_group": task_group_map.get(task_id) or None,
                }

            # Build dag_task_graph entries for all tasks in this DAG (ETLs + sensors)
            for task_id, op_kwargs in op_kwargs_by_task.items():
                s_name = op_kwargs.get("sensor_name")
                e_name = op_kwargs.get("etl_name")
                if not s_name and not e_name:
                    continue
                dag_task_graph.append({
                    "dag_id": dag_id,
                    "task_id": task_id,
                    "downstream_task_ids": downstream_map.get(task_id, []),
                    "needs": op_kwargs.get("needs", []),
                    "prefers": op_kwargs.get("prefers", []),
                    "task_group_id": task_group_map.get(task_id) or None,
                    "sensor_name": s_name,
                })

        logger.info("Collected %d ETL tasks from %d DAGs", len(seen_tasks), len(all_dags))

        if not seen_tasks:
            logger.info("No tasks with etl metadata found in Airflow")
            return 0

        # Load known teams for task_group prefix matching
        known_teams = await self.team_repo.get_all_names()

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

            # Assign team from task_group prefix
            task_group = meta.get("task_group")
            team_name = self._extract_team_from_task_group(task_group, known_teams)
            if team_name:
                team = await self.team_repo.get_or_create(team_name, source="airflow")
                known_teams.add(team_name)
                await self.pipeline_repo.set_team(pipeline.id, team_name, team.id)

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

        # Pass 4: Upsert sensors
        sensor_name_to_id: dict[str, uuid.UUID] = {}
        for sensor_name, meta in seen_sensors.items():
            display_name = self._task_id_to_display_name(sensor_name)
            sensor = await self.sensor_repo.upsert({
                "sensor_name": sensor_name,
                "display_name": display_name,
                "description": meta["description"],
                "team": meta["team"],
                "volume_per_day": meta["volume_per_day"],
                "dag_ids": meta["dag_ids"],
            })
            sensor_name_to_id[sensor_name] = sensor.id

        logger.info("Synced %d sensors from Airflow", len(seen_sensors))

        # Pass 5: Sync DAG task graph (membership + downstream edges)
        current_pairs: set[tuple[str, str]] = set()
        for entry in dag_task_graph:
            entry["pipeline_id"] = task_id_to_pipeline_id.get(entry["task_id"])
            # Link sensor entries to sensor records
            s_name = entry.get("sensor_name")
            if s_name:
                entry["sensor_id"] = sensor_name_to_id.get(s_name)
            await self.dag_task_repo.upsert(entry)
            current_pairs.add((entry["dag_id"], entry["task_id"]))

        stale_deleted = await self.dag_task_repo.delete_stale(current_pairs)
        if stale_deleted:
            logger.info("Deleted %d stale dag_task entries", stale_deleted)

        await self.session.commit()
        logger.info(
            "Synced %d pipelines, %d sensors, %d resource configs, %d dag_task entries from Airflow",
            synced,
            len(seen_sensors),
            resource_count,
            len(dag_task_graph),
        )
        return synced

    async def sync_single_pipeline(self, pipeline_id: uuid.UUID) -> dict:
        """Re-sync a single pipeline's metadata, lineage, resources, and status from Airflow.

        Uses the dag_tasks DB cache to avoid scanning all DAGs, with a differential
        check to discover newly-added DAGs. Airflow API calls are parallelized via
        asyncio.gather with a semaphore to respect connection pool limits.
        """
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            raise ValueError(f"Pipeline {pipeline_id} not found")

        task_id = pipeline.task_id
        if not task_id:
            raise ValueError(f"Pipeline {pipeline_id} has no task_id")
        display_name = pipeline.name
        logger.info("Manual sync started for pipeline %s (task_id=%s)", display_name, task_id)

        async def _limited(coro):
            async with _AIRFLOW_SEMAPHORE:
                return await coro

        # ── Phase 1: Identify target DAGs via cache + differential check ──

        cached_dag_tasks = await self.dag_task_repo.get_dags_for_task(task_id)
        cached_dag_ids = {dt.dag_id for dt in cached_dag_tasks}

        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            raise ValueError("No DAGs found in Airflow")

        all_dag_ids = {d["dag_id"] for d in all_dags}
        uncached_dag_ids = all_dag_ids - cached_dag_ids

        # Check uncached DAGs for our task_id (handles new DAG edge case)
        new_dag_ids: set[str] = set()
        if uncached_dag_ids:
            uncached_list = list(uncached_dag_ids)
            check_results = await asyncio.gather(*[
                _limited(airflow_client.get_dag_tasks(dag_id))
                for dag_id in uncached_list
            ])
            for dag_id, tasks_def in zip(uncached_list, check_results):
                if any(t.get("task_id") == task_id for t in tasks_def):
                    new_dag_ids.add(dag_id)

        target_dag_ids = list(cached_dag_ids | new_dag_ids)
        if not target_dag_ids:
            raise ValueError(f"Task {task_id} not found in any Airflow DAG")

        # ── Phase 2: Fetch latest run + instances for all target DAGs in parallel ──

        dag_runs_results = await asyncio.gather(*[
            _limited(airflow_client.get_dag_runs(dag_id, limit=1))
            for dag_id in target_dag_ids
        ])

        dag_latest_run: dict[str, dict] = {}
        for dag_id, runs in zip(target_dag_ids, dag_runs_results):
            if runs and runs[0].get("dag_run_id"):
                dag_latest_run[dag_id] = runs[0]

        if not dag_latest_run:
            raise ValueError(f"Task {task_id} not found in any Airflow DAG (no runs)")

        run_dag_ids = list(dag_latest_run.keys())
        instances_results = await asyncio.gather(*[
            _limited(airflow_client.get_task_instances(
                dag_id, dag_latest_run[dag_id]["dag_run_id"]
            ))
            for dag_id in run_dag_ids
        ])

        # Extract metadata, resources, and status from pre-fetched results
        meta: dict | None = None
        resource_by_dag: dict[str, dict] = {}
        found_dags: set[str] = set()
        best_status: str | None = None
        best_dag_id: str | None = None
        best_exec_date: datetime | None = None

        for dag_id, instances in zip(run_dag_ids, instances_results):
            run = dag_latest_run[dag_id]
            for inst in instances:
                if inst.get("task_id") != task_id:
                    continue

                found_dags.add(dag_id)

                rendered = inst.get("rendered_fields", {}) or {}
                op_kwargs = rendered.get("op_kwargs", {}) or {}

                raw_resources = op_kwargs.get("resources")
                if raw_resources and isinstance(raw_resources, dict):
                    resource_by_dag[dag_id] = raw_resources

                state = inst.get("state", "")
                status = TASK_STATE_MAP.get(state, "unknown")
                exec_date = run.get("execution_date") or run.get("logical_date")
                if best_status is None or status == "running" or (
                    status == "success" and best_status != "running"
                ):
                    best_status = status
                    best_dag_id = dag_id
                    best_exec_date = exec_date

                if meta is None:
                    log_content = await airflow_client.get_task_log(
                        dag_id, run["dag_run_id"], task_id
                    )
                    destination_tables = self._parse_writes(log_content, task_id)
                    description = self._parse_description(log_content, task_id)

                    meta = {
                        "category": op_kwargs.get("category", ""),
                        "schedule": op_kwargs.get("schedule"),
                        "destination_tables": destination_tables,
                        "description": description,
                        "needs": op_kwargs.get("needs", []),
                    }
                break

        if meta is None:
            raise ValueError(f"Task {task_id} not found in any Airflow DAG")

        # ── Phase 3: DB writes (unchanged logic) ──

        await self.pipeline_repo.upsert({
            "name": display_name,
            "task_id": task_id,
            "description": meta["description"],
            "category": meta["category"],
            "schedule": meta["schedule"],
        })

        primary_table = task_id
        edges_to_create: list[dict] = []

        for upstream_task_id in meta["needs"]:
            edge: dict = {
                "target_pipeline_id": pipeline_id,
                "source_table": upstream_task_id,
                "target_table": primary_table,
                "edge_type": "reads_from",
            }
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

        # ── Phase 4: Run history — parallel fetch, sequential DB writes ──

        history_count = 0
        found_dag_list = list(found_dags)

        # Fetch 5 runs per DAG in parallel
        history_runs_results = await asyncio.gather(*[
            _limited(airflow_client.get_dag_runs(dag_id, limit=5))
            for dag_id in found_dag_list
        ])

        # Collect all (dag_id, dag_run_id) pairs
        all_run_pairs: list[tuple[str, str]] = []
        for dag_id, runs in zip(found_dag_list, history_runs_results):
            for run in runs:
                dag_run_id = run.get("dag_run_id")
                if dag_run_id:
                    all_run_pairs.append((dag_id, dag_run_id))

        # Fetch all task instances in parallel
        all_instances_results = await asyncio.gather(*[
            _limited(airflow_client.get_task_instances(dag_id, dag_run_id))
            for dag_id, dag_run_id in all_run_pairs
        ])

        # Process instances sequentially (DB operations) and collect log-fetch needs
        needs_log_fetch: list[tuple[str, str]] = []
        for (dag_id, dag_run_id), instances in zip(all_run_pairs, all_instances_results):
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

                needs_actuals = False
                if is_new and status == "success":
                    needs_actuals = True
                elif not is_new and status == "success":
                    needs_actuals = await self.resource_repo.has_null_actuals(
                        pipeline_id, dag_id, dag_run_id
                    )

                if needs_actuals:
                    needs_log_fetch.append((dag_id, dag_run_id))
                break

        # Fetch all needed logs in parallel, then update actuals sequentially
        if needs_log_fetch:
            log_results = await asyncio.gather(*[
                _limited(airflow_client.get_task_log(dag_id, dag_run_id, task_id))
                for dag_id, dag_run_id in needs_log_fetch
            ])
            for (dag_id, dag_run_id), log_content in zip(needs_log_fetch, log_results):
                try:
                    actuals = self._parse_resource_actual(log_content)
                    plan_json = self._parse_execution_plan(log_content)
                    if plan_json:
                        actuals = actuals or {}
                        actuals["execution_plan"] = plan_json
                    if actuals:
                        await self.resource_repo.update_run_actuals(
                            pipeline_id, dag_id, dag_run_id, actuals
                        )
                except Exception:
                    logger.debug(
                        "Could not parse resource actuals for %s/%s/%s",
                        dag_id, dag_run_id, task_id,
                    )

        logger.info("Recorded %d new run history entries for %s", history_count, display_name)

        # ── Phase 5: Status upsert + commit ──

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
        return AirflowSyncService._task_id_to_display_name(task_id)

    @staticmethod
    def _extract_team_from_task_group(
        task_group: str | None, known_teams: set[str]
    ) -> str | None:
        """Extract team name from PascalCase task_group prefix.

        Matches the longest known team name that is a prefix of the task_group.
        E.g., 'DaggerCollection' with known_teams={'Dagger','Vault'} → 'Dagger'.
        """
        if not task_group:
            return None
        for team in sorted(known_teams, key=len, reverse=True):
            if task_group.startswith(team) and len(task_group) > len(team):
                return team
        return None

    @staticmethod
    def _task_id_to_display_name(task_id: str) -> str:
        """Convert task_id to display name.

        Handles both PascalCase and snake_case:
          'SwitchPortCollector' -> 'Switch Port Collector'
          'switch_port_collector' -> 'Switch Port Collector'
        """
        # Insert space before each uppercase that follows a lowercase letter or digit
        spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", task_id)
        # Also handle any remaining snake_case or kebab-case
        return spaced.replace("_", " ").replace("-", " ").strip().title()

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

    @staticmethod
    def _parse_execution_plan(log: str) -> str | None:
        """Extract execution plan JSON from task log."""
        for line in log.splitlines():
            if "ETL_EXECUTION_PLAN:" in line:
                raw = line.split("ETL_EXECUTION_PLAN:", 1)[1].strip()
                try:
                    json.loads(raw)  # validate it's valid JSON
                    return raw
                except (json.JSONDecodeError, ValueError):
                    pass
        return None

    @staticmethod
    def _parse_sensor_volume(log_content: str) -> int | None:
        """Parse SENSOR_VOLUME line from a sensor task's log output."""
        if not log_content:
            return None
        for line in log_content.splitlines():
            if "SENSOR_VOLUME:" in line:
                parts = line.split("SENSOR_VOLUME:", 1)
                if len(parts) == 2:
                    try:
                        return int(parts[1].strip())
                    except ValueError:
                        pass
        return None

    @staticmethod
    def _parse_sensor_description(log_content: str, task_id: str) -> str:
        """Parse SENSOR_DESCRIPTION line from a sensor task's log output."""
        if log_content:
            for line in log_content.splitlines():
                if "SENSOR_DESCRIPTION:" in line:
                    parts = line.split("SENSOR_DESCRIPTION:", 1)
                    if len(parts) == 2:
                        desc = parts[1].strip()
                        if desc:
                            return desc
        return AirflowSyncService._task_id_to_display_name(task_id)
