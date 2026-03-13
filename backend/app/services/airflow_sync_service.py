"""Airflow sync service — discovers pipelines and lineage from Airflow task metadata.

Auto-discovers all tasks from Airflow using task_id as the canonical name.
Pipeline metadata (category, schedule, lineage) is derived from TaskGroups,
DAG schedules, and params. Resources come from op_kwargs.
"""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.airflow_client import airflow_client, strip_group_prefix
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.sensor_repo import BouncerRepository
from app.repositories.team_repo import TeamRepository
from app.services.airflow_service import KNOWN_AIRFLOW_STATES, _STATUS_PRIORITY

logger = logging.getLogger(__name__)

# Limits concurrent Airflow API calls — leaves headroom below httpx max_connections=10
_AIRFLOW_SEMAPHORE = asyncio.Semaphore(6)

# Operator types to skip during auto-discovery (infrastructure tasks)
_EXCLUDE_OPERATOR_TYPES: set[str] = {
    t.strip()
    for t in settings.airflow_exclude_operator_types.split(",")
    if t.strip()
}


class AirflowSyncService:
    def __init__(
        self,
        session: AsyncSession,
        pipeline_repo: PipelineRepository | None = None,
        lineage_repo: LineageRepository | None = None,
        resource_repo: ResourceRepository | None = None,
        airflow_repo: AirflowRepository | None = None,
        dag_task_repo: DagTaskRepository | None = None,
        sensor_repo: BouncerRepository | None = None,
        team_repo: TeamRepository | None = None,
    ):
        self.session = session
        self.pipeline_repo = pipeline_repo or PipelineRepository(session)
        self.lineage_repo = lineage_repo or LineageRepository(session)
        self.resource_repo = resource_repo or ResourceRepository(session)
        self.airflow_repo = airflow_repo or AirflowRepository(session)
        self.dag_task_repo = dag_task_repo or DagTaskRepository(session)
        self.sensor_repo = sensor_repo or BouncerRepository(session)
        self.team_repo = team_repo or TeamRepository(session)

    async def sync_pipelines_from_airflow(self) -> int:
        """Discover all tasks across all DAGs and register as pipelines + lineage.

        Auto-discovers tasks using task_id — no etl_name/sensor_name gate.
        - Category: from TaskGroup (second part after dash)
        - Schedule: from DAG native (timetable_description or schedule_interval)
        - Lineage: from params (needs/prefers)
        - Resources: from op_kwargs
        - Bouncer detection: "Bouncer" in task_id
        - API detection: "Api" or "API" in task_id

        Returns the number of pipelines synced.
        """
        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            logger.warning("No DAGs found in Airflow — skipping pipeline sync")
            return 0

        # Collect unique task metadata across all DAGs.
        # A task can appear in multiple DAGs — we take the first occurrence's metadata.
        seen_tasks: dict[str, dict] = {}
        # Bouncer metadata (keyed by bouncer name)
        seen_bouncers: dict[str, dict] = {}
        # Resource configs per task per DAG (collected before dedup — need all occurrences)
        resource_by_dag: dict[str, dict[str, dict]] = {}
        # DAG task graph data: (dag_id, task_id) -> {downstream_task_ids, needs, prefers}
        dag_task_graph: list[dict] = []

        # ── Phased parallel fetch of Airflow API data ──
        async def _limited(coro):
            async with _AIRFLOW_SEMAPHORE:
                return await coro

        all_dag_ids = [d["dag_id"] for d in all_dags]
        # Build DAG defs lookup for schedule extraction
        dag_defs_by_id = {d["dag_id"]: d for d in all_dags}

        # Phase A: Parallel fetch task definitions + task group maps + dag runs
        tasks_results, tg_results, runs_results = await asyncio.gather(
            asyncio.gather(*[_limited(airflow_client.get_dag_tasks(did)) for did in all_dag_ids]),
            asyncio.gather(*[_limited(airflow_client.get_task_group_map(did)) for did in all_dag_ids]),
            asyncio.gather(*[_limited(airflow_client.get_dag_runs(did, limit=1)) for did in all_dag_ids]),
        )

        # Build operator type lookup from task definitions: {dag_id: {task_id: class_name}}
        operator_by_dag: dict[str, dict[str, str]] = {}
        for i, dag_id in enumerate(all_dag_ids):
            op_map: dict[str, str] = {}
            for t in tasks_results[i]:
                class_ref = t.get("class_ref", {}) or {}
                class_name = class_ref.get("class_name", "")
                op_map[t["task_id"]] = class_name
            operator_by_dag[dag_id] = op_map

        # Phase B: Identify DAGs with runs, parallel fetch task instances
        dags_with_runs: list[tuple[str, str, list, dict]] = []  # (dag_id, run_id, tasks_def, tg_map)
        for i, dag_id in enumerate(all_dag_ids):
            runs = runs_results[i]
            if runs and runs[0].get("dag_run_id"):
                dags_with_runs.append((dag_id, runs[0]["dag_run_id"], tasks_results[i], tg_results[i]))

        if dags_with_runs:
            instances_results = await asyncio.gather(*[
                _limited(airflow_client.get_task_instances(dag_id, run_id))
                for dag_id, run_id, _, _ in dags_with_runs
            ])
        else:
            instances_results = []

        # Phase C: Process instances — auto-discover all tasks by task_id
        dag_processed: list[dict] = []  # parallel to dags_with_runs
        log_requests: list[tuple[str, str, str, str, str]] = []  # (dag_id, run_id, airflow_tid, kind, key)

        for idx, (dag_id, dag_run_id, tasks_def, task_group_map) in enumerate(dags_with_runs):
            downstream_map = {
                t["task_id"]: t.get("downstream_task_ids", []) for t in tasks_def
            }
            params_by_task = {
                t["task_id"]: self._unwrap_params(t.get("params", {}))
                for t in tasks_def
            }
            instances = instances_results[idx]
            canonical_by_airflow_tid: dict[str, str] = {}

            for inst in instances:
                airflow_task_id = inst.get("task_id", "")
                canonical_tid = strip_group_prefix(airflow_task_id)

                # Skip infrastructure operators
                op_class = operator_by_dag.get(dag_id, {}).get(airflow_task_id, "")
                if op_class in _EXCLUDE_OPERATOR_TYPES:
                    continue

                rendered = inst.get("rendered_fields", {}) or {}
                op_kwargs = rendered.get("op_kwargs", {}) or {}
                params = params_by_task.get(airflow_task_id, {})

                canonical_by_airflow_tid[airflow_task_id] = canonical_tid

                if self._is_bouncer(canonical_tid):
                    # ── Bouncer task ──
                    if canonical_tid not in seen_bouncers:
                        description = op_kwargs.get("description")
                        log_requests.append((dag_id, dag_run_id, airflow_task_id, "bouncer", canonical_tid))
                        seen_bouncers[canonical_tid] = {
                            "sensor_name": canonical_tid,
                            "description": description,
                            "dag_ids": [dag_id],
                            "task_group": task_group_map.get(canonical_tid) or None,
                        }
                    else:
                        if dag_id not in seen_bouncers[canonical_tid]["dag_ids"]:
                            seen_bouncers[canonical_tid]["dag_ids"].append(dag_id)
                else:
                    # ── Pipeline task ──
                    raw_resources = op_kwargs.get("resources")
                    if raw_resources and isinstance(raw_resources, dict):
                        resource_by_dag.setdefault(canonical_tid, {})[dag_id] = raw_resources

                    if canonical_tid not in seen_tasks:
                        log_requests.append((dag_id, dag_run_id, airflow_task_id, "etl", canonical_tid))
                        task_group = task_group_map.get(canonical_tid) or None
                        seen_tasks[canonical_tid] = {
                            "task_id": canonical_tid,
                            "category": self._extract_category_from_task_group(task_group),
                            "schedule": self._extract_dag_schedule(dag_defs_by_id.get(dag_id, {})),
                            "destination_tables": [],
                            "description": "",
                            "needs": params.get("needs", []),
                            "prefers": params.get("prefers", []),
                            "task_group": task_group,
                        }

            dag_processed.append({
                "dag_id": dag_id,
                "task_group_map": task_group_map,
                "downstream_map": downstream_map,
                "params_by_task": params_by_task,
                "canonical_by_airflow_tid": canonical_by_airflow_tid,
            })

        # Phase D: Parallel fetch all needed logs
        if log_requests:
            log_results = await asyncio.gather(*[
                _limited(airflow_client.get_task_log(dag_id, run_id, tid))
                for dag_id, run_id, tid, _, _ in log_requests
            ])
        else:
            log_results = []

        # Phase E: Process log results
        for (dag_id, _, _, kind, key), log_content in zip(log_requests, log_results):
            if kind == "bouncer":
                meta = seen_bouncers[key]
                # Use op_kwargs description if available, otherwise parse from logs
                if not meta.get("description"):
                    meta["description"] = self._parse_bouncer_description(log_content, key)
            elif kind == "etl":
                meta = seen_tasks[key]
                meta["destination_tables"] = self._parse_writes(log_content, key)
                meta["description"] = self._parse_description(log_content, key)

        # Build dag_task_graph from all discovered tasks
        for proc in dag_processed:
            dag_id = proc["dag_id"]
            task_group_map = proc["task_group_map"]
            downstream_map = proc["downstream_map"]
            params_by_task = proc["params_by_task"]
            for airflow_tid, canonical_tid in proc["canonical_by_airflow_tid"].items():
                is_bouncer = self._is_bouncer(canonical_tid)
                raw_downstream = downstream_map.get(airflow_tid, [])
                params = params_by_task.get(airflow_tid, {})
                dag_task_graph.append({
                    "dag_id": dag_id,
                    "task_id": canonical_tid,
                    "downstream_task_ids": [strip_group_prefix(d) for d in raw_downstream],
                    "needs": params.get("needs", []),
                    "prefers": params.get("prefers", []),
                    "task_group_id": task_group_map.get(canonical_tid) or None,
                    "sensor_name": canonical_tid if is_bouncer else None,
                })

        logger.info(
            "Collected %d pipeline tasks and %d bouncers from %d DAGs",
            len(seen_tasks), len(seen_bouncers), len(all_dags),
        )

        if not seen_tasks and not seen_bouncers:
            logger.info("No tasks discovered in Airflow")
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

            if not self._is_api(task_id):
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
                        "synced_at": datetime.now(timezone.utc),
                    })
                    resource_count += 1
                except Exception:
                    logger.exception(
                        "Failed to sync resource config for %s in %s", task_id, dag_id
                    )

        # Pass 4: Upsert bouncers (volume_per_day preserved in DB — not overwritten)
        bouncer_name_to_id: dict[str, uuid.UUID] = {}
        for bouncer_name, meta in seen_bouncers.items():
            display_name = self._task_id_to_display_name(bouncer_name)
            task_group = meta.get("task_group")
            team_name = self._extract_team_from_task_group(task_group, known_teams)
            bouncer = await self.sensor_repo.upsert({
                "sensor_name": bouncer_name,
                "display_name": display_name,
                "description": meta.get("description") or display_name,
                "team": team_name or "",
                "dag_ids": meta["dag_ids"],
            })
            bouncer_name_to_id[bouncer_name] = bouncer.id

        logger.info("Synced %d bouncers from Airflow", len(seen_bouncers))

        # Pass 5: Sync DAG task graph (membership + downstream edges)
        current_pairs: set[tuple[str, str]] = set()
        for entry in dag_task_graph:
            entry["pipeline_id"] = task_id_to_pipeline_id.get(entry["task_id"])
            # Link bouncer entries to bouncer records
            s_name = entry.get("sensor_name")
            if s_name:
                entry["sensor_id"] = bouncer_name_to_id.get(s_name)
            await self.dag_task_repo.upsert(entry)
            current_pairs.add((entry["dag_id"], entry["task_id"]))

        stale_deleted = await self.dag_task_repo.delete_stale(current_pairs)
        if stale_deleted:
            logger.info("Deleted %d stale dag_task entries", stale_deleted)

        await self.session.commit()
        logger.info(
            "Synced %d pipelines, %d bouncers, %d resource configs, %d dag_task entries from Airflow",
            synced,
            len(seen_bouncers),
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
                if any(strip_group_prefix(t.get("task_id", "")) == task_id for t in tasks_def):
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

        # Also fetch task definitions + task group maps for target DAGs (for params + category)
        run_dag_ids = list(dag_latest_run.keys())
        instances_results, tg_results_single, tasks_def_results = await asyncio.gather(
            asyncio.gather(*[
                _limited(airflow_client.get_task_instances(
                    dag_id, dag_latest_run[dag_id]["dag_run_id"]
                ))
                for dag_id in run_dag_ids
            ]),
            asyncio.gather(*[
                _limited(airflow_client.get_task_group_map(dag_id))
                for dag_id in run_dag_ids
            ]),
            asyncio.gather(*[
                _limited(airflow_client.get_dag_tasks(dag_id))
                for dag_id in run_dag_ids
            ]),
        )

        # Build DAG defs lookup for schedule
        dag_defs_by_id = {d["dag_id"]: d for d in all_dags}

        # Extract metadata, resources, and status from pre-fetched results
        meta: dict | None = None
        resource_by_dag: dict[str, dict] = {}
        found_dags: set[str] = set()
        best_status: str | None = None
        best_dag_id: str | None = None
        best_exec_date: datetime | None = None

        for i, dag_id in enumerate(run_dag_ids):
            instances = instances_results[i]
            run = dag_latest_run[dag_id]
            task_group_map = tg_results_single[i]
            params_by_task = {
                t["task_id"]: self._unwrap_params(t.get("params", {}))
                for t in tasks_def_results[i]
            }
            for inst in instances:
                airflow_task_id = inst.get("task_id", "")
                if strip_group_prefix(airflow_task_id) != task_id:
                    continue

                found_dags.add(dag_id)

                rendered = inst.get("rendered_fields", {}) or {}
                op_kwargs = rendered.get("op_kwargs", {}) or {}

                raw_resources = op_kwargs.get("resources")
                if raw_resources and isinstance(raw_resources, dict):
                    resource_by_dag[dag_id] = raw_resources

                state = inst.get("state", "")
                status = state if state in KNOWN_AIRFLOW_STATES else "unknown"
                exec_date = run.get("execution_date") or run.get("logical_date")
                if best_status is None or _STATUS_PRIORITY.get(status, 13) < _STATUS_PRIORITY.get(best_status, 13):
                    best_status = status
                    best_dag_id = dag_id
                    best_exec_date = exec_date

                if meta is None:
                    log_content = await airflow_client.get_task_log(
                        dag_id, run["dag_run_id"], airflow_task_id
                    )
                    destination_tables = self._parse_writes(log_content, task_id)
                    description = self._parse_description(log_content, task_id)
                    task_group = task_group_map.get(task_id) or None
                    params = params_by_task.get(airflow_task_id, {})

                    meta = {
                        "category": self._extract_category_from_task_group(task_group),
                        "schedule": self._extract_dag_schedule(dag_defs_by_id.get(dag_id, {})),
                        "destination_tables": destination_tables,
                        "description": description,
                        "needs": params.get("needs", []),
                    }
                break

        if meta is None:
            raise ValueError(f"Task {task_id} not found in any Airflow DAG")

        # ── Phase 3: DB writes ──

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

        if not self._is_api(task_id):
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
                    "synced_at": datetime.now(timezone.utc),
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

        # Determine the full Airflow task_id (with group prefix) for this pipeline
        airflow_task_id = task_id  # fallback for unprefixed
        for _, instances in zip(run_dag_ids, instances_results):
            for inst in instances:
                if strip_group_prefix(inst.get("task_id", "")) == task_id:
                    airflow_task_id = inst["task_id"]
                    break
            if airflow_task_id != task_id:
                break

        # Process instances sequentially (DB operations) and collect log-fetch needs
        needs_log_fetch: list[tuple[str, str]] = []
        for (dag_id, dag_run_id), instances in zip(all_run_pairs, all_instances_results):
            for inst in instances:
                if strip_group_prefix(inst.get("task_id", "")) != task_id:
                    continue

                state = inst.get("state", "unknown")
                status = state if state in KNOWN_AIRFLOW_STATES else "unknown"
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
                    "start_date": start_date,
                    "end_date": end_date,
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
                _limited(airflow_client.get_task_log(dag_id, dag_run_id, airflow_task_id))
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
                        clean_exec_date = datetime.fromisoformat(best_exec_date.replace("Z", "+00:00"))
                    except ValueError:
                        pass
                elif isinstance(best_exec_date, datetime):
                    clean_exec_date = best_exec_date

            await self.airflow_repo.upsert({
                "pipeline_id": pipeline_id,
                "dag_id": best_dag_id,
                "status": best_status,
                "execution_date": clean_exec_date,
                "last_checked_at": datetime.now(timezone.utc),
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
        """Extract team name from task_group.

        Supports:
          'Dagger-Collection' -> 'Dagger'  (split on first '-')
          'Relay'             -> 'Relay'   (exact match)
        """
        if not task_group:
            return None
        if "-" in task_group:
            team_part = task_group.split("-", 1)[0]
            if team_part in known_teams:
                return team_part
            return None
        if task_group in known_teams:
            return task_group
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
    def _is_bouncer(task_id: str) -> bool:
        """Check if a task_id represents a bouncer (data ingestion root task)."""
        return "Bouncer" in task_id

    @staticmethod
    def _is_api(task_id: str) -> bool:
        """Check if a task_id represents an API task (skip writes_to lineage)."""
        return "Api" in task_id or "API" in task_id

    @staticmethod
    def _extract_category_from_task_group(task_group: str | None) -> str:
        """Extract category from TaskGroup name.

        'Dagger-Collection' -> 'Collection'
        'Relay'             -> 'Relay'
        None                -> 'Uncategorized'
        """
        if not task_group:
            return "Uncategorized"
        if "-" in task_group:
            return task_group.split("-", 1)[1]
        return task_group

    @staticmethod
    def _extract_dag_schedule(dag_def: dict) -> str | None:
        """Extract schedule from DAG definition.

        Prefers timetable_description, falls back to schedule_interval.
        """
        schedule = dag_def.get("timetable_description")
        if schedule and schedule != "Never":
            return schedule
        return dag_def.get("schedule_interval") or None

    @staticmethod
    def _parse_bouncer_description(log_content: str, task_id: str) -> str:
        """Parse BOUNCER_DESCRIPTION line from a bouncer task's log output."""
        if log_content:
            for line in log_content.splitlines():
                if "BOUNCER_DESCRIPTION:" in line:
                    parts = line.split("BOUNCER_DESCRIPTION:", 1)
                    if len(parts) == 2:
                        desc = parts[1].strip()
                        if desc:
                            return desc
        return AirflowSyncService._task_id_to_display_name(task_id)
