"""Airflow sync service — discovers pipelines and lineage from Airflow task metadata.

Auto-discovers all tasks from Airflow using task_id as the canonical name.
Pipeline metadata (category, schedule, lineage) is derived from TaskGroups,
DAG schedules, and params. Resources come from op_kwargs.
"""

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AirflowSyncError, PipelineNotFoundError
from app.integrations.airflow_client import airflow_client, strip_group_prefix
from app.models.pipeline import Pipeline
from app.parsers.log_parser import (
    parse_bouncer_description,
    parse_description,
    parse_execution_plan,
    parse_resource_actual,
    parse_writes,
)
from app.repositories.airflow_repo import AirflowRepository
from app.repositories.bouncer_repo import BouncerRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.repositories.team_repo import TeamRepository
from app.services.airflow_service import _STATUS_PRIORITY, KNOWN_AIRFLOW_STATES
from app.services.sync.task_classifier import (
    extract_category_from_task_group,
    extract_dag_schedule,
    extract_team_from_dag_tags,
    extract_team_from_task_group,
    is_api,
    is_bouncer,
    parse_datetime,
    task_id_to_display_name,
    unwrap_params,
)

logger = logging.getLogger(__name__)

# Limits concurrent Airflow API calls — leaves headroom below httpx max_connections=10
_AIRFLOW_SEMAPHORE = asyncio.Semaphore(settings.airflow_semaphore_limit)


async def _limited(coro):
    """Run a coroutine with the Airflow concurrency semaphore."""
    async with _AIRFLOW_SEMAPHORE:
        return await coro


# Operator types to skip during auto-discovery (infrastructure tasks)
_EXCLUDE_OPERATOR_TYPES: set[str] = {
    t.strip()
    for t in settings.airflow_exclude_operator_types.split(",")
    if t.strip()
}


@dataclass
class _FullSyncFetchResult:
    """Intermediate state from Airflow API fetching (Phases A-B)."""

    all_dag_ids: list[str]
    dag_defs_by_id: dict[str, dict]
    tasks_results: list[list]
    tg_results: list[list]
    runs_results: list[list]
    operator_by_dag: dict[str, dict[str, str]]
    instances_results: list[list]
    dags_with_runs: list[tuple]


@dataclass
class _TaskDiscoveryResult:
    """Intermediate state from task classification (Phase C)."""

    seen_tasks: dict[str, dict] = field(default_factory=dict)
    seen_bouncers: dict[str, dict] = field(default_factory=dict)
    resource_by_dag: dict[str, dict] = field(default_factory=dict)
    dag_task_graph: list[dict] = field(default_factory=list)
    log_requests: list[tuple] = field(default_factory=list)
    # dag_processed is built alongside Phase C and consumed when building dag_task_graph
    dag_processed: list[dict] = field(default_factory=list)


@dataclass
class _SingleSyncTargets:
    """Target DAGs identified for single-pipeline sync."""

    target_dag_ids: list[str]
    cached_dag_ids: list[str]
    new_dag_ids: list[str]


class AirflowSyncService:
    def __init__(
        self,
        session: AsyncSession,
        pipeline_repo: PipelineRepository | None = None,
        lineage_repo: LineageRepository | None = None,
        resource_repo: ResourceRepository | None = None,
        airflow_repo: AirflowRepository | None = None,
        dag_task_repo: DagTaskRepository | None = None,
        bouncer_repo: BouncerRepository | None = None,
        team_repo: TeamRepository | None = None,
    ):
        self.session = session
        self.pipeline_repo = pipeline_repo or PipelineRepository(session)
        self.lineage_repo = lineage_repo or LineageRepository(session)
        self.resource_repo = resource_repo or ResourceRepository(session)
        self.airflow_repo = airflow_repo or AirflowRepository(session)
        self.dag_task_repo = dag_task_repo or DagTaskRepository(session)
        self.bouncer_repo = bouncer_repo or BouncerRepository(session)
        self.team_repo = team_repo or TeamRepository(session)

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    async def sync_pipelines_from_airflow(self) -> int:
        """Discover all tasks across all DAGs and register as pipelines + lineage.

        Auto-discovers tasks using task_id — no etl_name/bouncer_name gate.
        Processes DAGs in configurable chunks to bound memory usage.

        Returns the number of pipelines synced.
        """
        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            logger.warning("No DAGs found in Airflow — skipping pipeline sync")
            return 0

        dag_defs_by_id = {d["dag_id"]: d for d in all_dags}
        chunk_size = settings.airflow_sync_chunk_size
        discovery = _TaskDiscoveryResult()

        # Process DAGs in chunks to bound peak memory
        for i in range(0, len(all_dags), chunk_size):
            chunk = all_dags[i:i + chunk_size]
            fetch = await self._fetch_airflow_data(chunk)
            chunk_disc = await self._discover_tasks(fetch)
            # Merge chunk results into accumulated discovery
            discovery.seen_tasks.update(chunk_disc.seen_tasks)
            discovery.seen_bouncers.update(chunk_disc.seen_bouncers)
            discovery.resource_by_dag.update(chunk_disc.resource_by_dag)
            discovery.dag_task_graph.extend(chunk_disc.dag_task_graph)
            discovery.log_requests.extend(chunk_disc.log_requests)
            discovery.dag_processed.extend(chunk_disc.dag_processed)
            del fetch, chunk_disc  # Release chunk memory

        if not discovery.seen_tasks and not discovery.seen_bouncers:
            logger.info("No tasks discovered in Airflow")
            return 0

        await self._fetch_and_parse_logs(discovery)

        task_id_map, synced = await self._persist_pipelines_and_lineage(discovery, dag_defs_by_id)
        resource_count = await self._persist_resources(discovery, task_id_map)
        bouncer_id_map = await self._persist_bouncers(discovery)
        await self._persist_dag_tasks(discovery, task_id_map, bouncer_id_map)

        await self.session.commit()
        logger.info(
            "Synced %d pipelines, %d bouncers, %d resource configs, %d dag_task entries from Airflow",
            synced,
            len(discovery.seen_bouncers),
            resource_count,
            len(discovery.dag_task_graph),
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
            raise PipelineNotFoundError(f"Pipeline {pipeline_id} not found")

        task_id = pipeline.task_id
        if not task_id:
            raise PipelineNotFoundError(f"Pipeline {pipeline_id} has no task_id")
        display_name = pipeline.name
        logger.info("Manual sync started for pipeline %s (task_id=%s)", display_name, task_id)

        # Gather known DAG IDs from cache and full list from Airflow
        cached_dag_tasks = await self.dag_task_repo.get_dags_for_task(task_id)
        cached_dag_ids = list({dt.dag_id for dt in cached_dag_tasks})

        all_dags = await airflow_client.get_all_dags()
        if not all_dags:
            raise AirflowSyncError("No DAGs found in Airflow")

        all_dag_ids = list({d["dag_id"] for d in all_dags})

        targets = await self._identify_target_dags(task_id, cached_dag_ids, all_dag_ids)
        if not targets.target_dag_ids:
            raise AirflowSyncError(f"Task {task_id} not found in any Airflow DAG")

        meta = await self._fetch_single_pipeline_metadata(task_id, targets, all_dags)

        resource_by_dag: dict[str, dict] = meta.pop("_resource_by_dag")
        best_status: str | None = meta.pop("_best_status")
        best_dag_id: str | None = meta.pop("_best_dag_id")
        best_exec_date = meta.pop("_best_exec_date")
        found_dags: list[str] = meta.pop("_found_dags")
        run_dag_ids: list[str] = meta.pop("_run_dag_ids")
        instances_results: list[list] = meta.pop("_instances_results")

        await self._persist_single_pipeline_data(
            task_id, pipeline_id, display_name, meta, resource_by_dag
        )
        await self._sync_run_history(
            pipeline_id, task_id, found_dags, run_dag_ids, instances_results
        )

        # ── Phase 5: Status upsert + commit ──

        if best_status and best_dag_id:
            clean_exec_date = None
            if best_exec_date:
                if isinstance(best_exec_date, str):
                    with contextlib.suppress(ValueError):
                        clean_exec_date = datetime.fromisoformat(best_exec_date.replace("Z", "+00:00"))
                elif isinstance(best_exec_date, datetime):
                    clean_exec_date = best_exec_date

            await self.airflow_repo.upsert({
                "pipeline_id": pipeline_id,
                "dag_id": best_dag_id,
                "status": best_status,
                "execution_date": clean_exec_date,
                "last_checked_at": datetime.now(UTC),
            })

        await self.session.commit()
        logger.info("Manual sync completed for pipeline %s", display_name)
        return {"synced": True, "pipeline_name": display_name}

    # ──────────────────────────────────────────────────────────────────────────
    # sync_pipelines_from_airflow — private helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _fetch_airflow_data(self, all_dags: list[dict]) -> _FullSyncFetchResult:
        """Phase A + B: parallel fetch of task defs, task groups, runs, and instances.

        Returns a fully-populated _FullSyncFetchResult containing all raw API
        data needed for subsequent discovery and persistence phases.
        """
        all_dag_ids = [d["dag_id"] for d in all_dags]
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

        return _FullSyncFetchResult(
            all_dag_ids=all_dag_ids,
            dag_defs_by_id=dag_defs_by_id,
            tasks_results=tasks_results,
            tg_results=tg_results,
            runs_results=runs_results,
            operator_by_dag=operator_by_dag,
            instances_results=instances_results,
            dags_with_runs=dags_with_runs,
        )

    async def _discover_tasks(self, fetch: _FullSyncFetchResult) -> _TaskDiscoveryResult:
        """Phase C: iterate instances, classify tasks, build resource configs and dag task graph.

        Returns a _TaskDiscoveryResult containing all discovered tasks, bouncers,
        resource configs, and the dag_processed list consumed by _persist_dag_tasks.
        """
        discovery = _TaskDiscoveryResult()

        for idx, (dag_id, dag_run_id, tasks_def, task_group_map) in enumerate(fetch.dags_with_runs):
            downstream_map = {
                t["task_id"]: t.get("downstream_task_ids", []) for t in tasks_def
            }
            params_by_task = {
                t["task_id"]: unwrap_params(t.get("params", {}))
                for t in tasks_def
            }
            instances = fetch.instances_results[idx]
            canonical_by_airflow_tid: dict[str, str] = {}

            for inst in instances:
                airflow_task_id = inst.get("task_id", "")
                canonical_tid = strip_group_prefix(airflow_task_id)

                # Skip infrastructure operators
                op_class = fetch.operator_by_dag.get(dag_id, {}).get(airflow_task_id, "")
                if op_class in _EXCLUDE_OPERATOR_TYPES:
                    continue

                rendered = inst.get("rendered_fields", {}) or {}
                op_kwargs = rendered.get("op_kwargs", {}) or {}
                params = params_by_task.get(airflow_task_id, {})

                canonical_by_airflow_tid[airflow_task_id] = canonical_tid

                if is_bouncer(canonical_tid):
                    # ── Bouncer task ──
                    if canonical_tid not in discovery.seen_bouncers:
                        description = op_kwargs.get("description")
                        discovery.log_requests.append(
                            (dag_id, dag_run_id, airflow_task_id, "bouncer", canonical_tid)
                        )
                        discovery.seen_bouncers[canonical_tid] = {
                            "bouncer_name": canonical_tid,
                            "description": description,
                            "dag_ids": [dag_id],
                            "task_group": task_group_map.get(canonical_tid) or None,
                        }
                    else:
                        if dag_id not in discovery.seen_bouncers[canonical_tid]["dag_ids"]:
                            discovery.seen_bouncers[canonical_tid]["dag_ids"].append(dag_id)
                else:
                    # ── Pipeline task ──
                    raw_resources = op_kwargs.get("resources")
                    if raw_resources and isinstance(raw_resources, dict):
                        discovery.resource_by_dag.setdefault(canonical_tid, {})[dag_id] = raw_resources

                    if canonical_tid not in discovery.seen_tasks:
                        discovery.log_requests.append(
                            (dag_id, dag_run_id, airflow_task_id, "etl", canonical_tid)
                        )
                        task_group = task_group_map.get(canonical_tid) or None
                        discovery.seen_tasks[canonical_tid] = {
                            "task_id": canonical_tid,
                            "category": extract_category_from_task_group(task_group),
                            "schedule": extract_dag_schedule(fetch.dag_defs_by_id.get(dag_id, {})),
                            "destination_tables": [],
                            "description": "",
                            "needs": params.get("needs", []),
                            "prefers": params.get("prefers", []),
                            "task_group": task_group,
                        }

            discovery.dag_processed.append({
                "dag_id": dag_id,
                "task_group_map": task_group_map,
                "downstream_map": downstream_map,
                "params_by_task": params_by_task,
                "canonical_by_airflow_tid": canonical_by_airflow_tid,
            })

        logger.info(
            "Collected %d pipeline tasks and %d bouncers from %d DAGs",
            len(discovery.seen_tasks), len(discovery.seen_bouncers), len(fetch.all_dag_ids),
        )

        return discovery

    async def _fetch_and_parse_logs(
        self,
        discovery: _TaskDiscoveryResult,
    ) -> None:
        """Phase D + E: parallel log fetch and parse; also builds dag_task_graph.

        Mutates discovery in place — populates destination_tables and description on
        seen_tasks entries, description on seen_bouncers, and builds dag_task_graph.
        """
        # Phase D: Parallel fetch all needed logs
        if discovery.log_requests:
            log_results = await asyncio.gather(*[
                _limited(airflow_client.get_task_log(dag_id, run_id, tid))
                for dag_id, run_id, tid, _, _ in discovery.log_requests
            ])
        else:
            log_results = []

        # Phase E: Process log results
        for (_dag_id, _, _, kind, key), log_content in zip(discovery.log_requests, log_results):
            if kind == "bouncer":
                meta = discovery.seen_bouncers[key]
                # Use op_kwargs description if available, otherwise parse from logs
                if not meta.get("description"):
                    meta["description"] = parse_bouncer_description(log_content, task_id_to_display_name(key))
            elif kind == "etl":
                meta = discovery.seen_tasks[key]
                meta["destination_tables"] = parse_writes(log_content, key)
                meta["description"] = parse_description(log_content, task_id_to_display_name(key))

        # Build dag_task_graph from all discovered tasks
        for proc in discovery.dag_processed:
            dag_id = proc["dag_id"]
            task_group_map = proc["task_group_map"]
            downstream_map = proc["downstream_map"]
            params_by_task = proc["params_by_task"]
            for airflow_tid, canonical_tid in proc["canonical_by_airflow_tid"].items():
                task_is_bouncer = is_bouncer(canonical_tid)
                raw_downstream = downstream_map.get(airflow_tid, [])
                params = params_by_task.get(airflow_tid, {})
                discovery.dag_task_graph.append({
                    "dag_id": dag_id,
                    "task_id": canonical_tid,
                    "downstream_task_ids": [strip_group_prefix(d) for d in raw_downstream],
                    "needs": params.get("needs", []),
                    "prefers": params.get("prefers", []),
                    "task_group_id": task_group_map.get(canonical_tid) or None,
                    "bouncer_name": canonical_tid if task_is_bouncer else None,
                })

    async def _persist_pipelines_and_lineage(
        self,
        discovery: _TaskDiscoveryResult,
        dag_defs_by_id: dict[str, dict] | None = None,
    ) -> tuple[dict[str, uuid.UUID], int]:
        """Batch upsert pipelines, assign teams, and rebuild lineage edges.

        Replaces ~1000 sequential DB round-trips with ~10-20 batch operations:
        - 2 SELECT queries to pre-fetch all existing pipelines (by name + task_id).
        - 1 INSERT for new pipelines (ON CONFLICT DO NOTHING).
        - 1 SELECT + 1 flush for team resolution via get_or_create_many.
        - 1 SELECT + 1 flush for team assignment via bulk_set_teams.
        - 1 DELETE for all stale lineage edges across all pipelines.
        - Chunked bulk INSERT for all new edges.

        Returns a tuple of (task_id -> pipeline UUID mapping, synced_count) where
        synced_count is the number of pipelines whose lineage was committed.
        """
        # --- Phase A: collect all pipeline data dicts (pure Python, no DB) ---
        known_teams = await self.team_repo.get_all_names()

        pipeline_entries: list[dict] = []
        team_name_by_task_id: dict[str, str] = {}

        for task_id, meta in discovery.seen_tasks.items():
            display_name = task_id_to_display_name(task_id)
            pipeline_entries.append({
                "name": display_name,
                "task_id": task_id,
                "description": meta["description"],
                "category": meta["category"],
                "schedule": meta["schedule"],
            })

            # Resolve team name in memory — no DB call yet
            task_group = meta.get("task_group")
            team_name = extract_team_from_task_group(task_group, known_teams)
            if not team_name and dag_defs_by_id is not None:
                for proc in discovery.dag_processed:
                    if task_id in proc["canonical_by_airflow_tid"].values():
                        dag_def = dag_defs_by_id.get(proc["dag_id"], {})
                        dag_tags = dag_def.get("tags")
                        team_name = extract_team_from_dag_tags(dag_tags, known_teams)
                        if team_name:
                            break
            if team_name:
                team_name_by_task_id[task_id] = team_name
                known_teams.add(team_name)

        # --- Phase B: batch-resolve all teams in two DB round-trips ---
        unique_team_names = list({n for n in team_name_by_task_id.values()})
        teams_by_name = {
            t.name: t
            for t in await self.team_repo.get_or_create_many(unique_team_names, source="airflow")
        }

        # --- Phase C: batch upsert all pipelines (2 SELECTs + 1 INSERT + 1 flush) ---
        task_id_to_pipeline: dict[str, Pipeline] = (
            await self.pipeline_repo.bulk_upsert_pipelines(pipeline_entries)
        )
        task_id_to_pipeline_id: dict[str, uuid.UUID] = {
            tid: p.id for tid, p in task_id_to_pipeline.items()
        }

        # --- Phase D: batch set team assignments (1 SELECT + 1 flush) ---
        team_assignments: list[tuple[uuid.UUID, str, uuid.UUID]] = []
        for task_id, team_name in team_name_by_task_id.items():
            pipeline_id = task_id_to_pipeline_id.get(task_id)
            team = teams_by_name.get(team_name)
            if pipeline_id and team:
                team_assignments.append((pipeline_id, team_name, team.id))
        await self.pipeline_repo.bulk_set_teams(team_assignments)

        # --- Phase E: build all lineage edges in memory, then batch delete + insert ---
        all_edges: list[dict] = []
        for task_id, meta in discovery.seen_tasks.items():
            pipeline_id = task_id_to_pipeline_id.get(task_id)
            if not pipeline_id:
                continue
            primary_table = task_id
            for upstream_task_id in meta["needs"]:
                all_edges.append({
                    "source_pipeline_id": None,
                    "target_pipeline_id": pipeline_id,
                    "source_table": upstream_task_id,
                    "target_table": primary_table,
                    "edge_type": "reads_from",
                })
            if not is_api(task_id):
                # Skip writes_to edge generation if the pipeline has manual writes_to set
                pipeline_obj = task_id_to_pipeline.get(task_id)
                has_manual_writes = pipeline_obj and getattr(pipeline_obj, "writes_to_manual", None)
                if not has_manual_writes:
                    for dest in meta["destination_tables"]:
                        all_edges.append({
                            "source_pipeline_id": pipeline_id,
                            "target_pipeline_id": None,
                            "source_table": primary_table,
                            "target_table": dest,
                            "edge_type": "writes_to",
                        })

        synced = 0
        all_pipeline_ids = list(task_id_to_pipeline_id.values())
        try:
            async with self.session.begin_nested():
                # Single DELETE for all synced pipelines instead of one per pipeline
                await self.lineage_repo.delete_by_pipeline_ids(all_pipeline_ids)
                await self.lineage_repo.bulk_insert_edges(all_edges)
            synced = len(task_id_to_pipeline_id)
        except Exception:
            logger.exception(
                "Failed to sync lineage for %d pipelines — rolling back lineage changes",
                len(all_pipeline_ids),
            )

        # --- Pass 2: Resolve source_pipeline_id on reads_from edges (bulk) ---
        resolve_edges: list[dict] = []
        pipelines_with_reads: set[str] = set()
        for task_id, meta in discovery.seen_tasks.items():
            pipeline_id = task_id_to_pipeline_id.get(task_id)
            if not pipeline_id:
                continue
            for upstream_task_id in meta["needs"]:
                pipelines_with_reads.add(task_id)
                source_pid = task_id_to_pipeline_id.get(upstream_task_id)
                if source_pid:
                    resolve_edges.append({
                        "target_pipeline_id": pipeline_id,
                        "source_pipeline_id": source_pid,
                        "source_table": upstream_task_id,
                        "target_table": task_id,
                        "edge_type": "reads_from",
                    })
        if resolve_edges:
            await self.lineage_repo.bulk_insert_edges(resolve_edges)

        # --- Pass 3: Infer reads_from edges from DAG task graph (opt-in, bulk) ---
        if settings.infer_lineage_from_dag_graph:
            upstream_map: dict[str, set[str]] = {}
            for entry in discovery.dag_task_graph:
                source_tid = entry["task_id"]
                for downstream_tid in entry.get("downstream_task_ids", []):
                    upstream_map.setdefault(downstream_tid, set()).add(source_tid)

            inferred_edges: list[dict] = []
            for task_id in discovery.seen_tasks:
                if task_id in pipelines_with_reads:
                    continue
                pipeline_id = task_id_to_pipeline_id.get(task_id)
                if not pipeline_id:
                    continue
                for upstream_tid in upstream_map.get(task_id, set()):
                    source_pid = task_id_to_pipeline_id.get(upstream_tid)
                    if source_pid:
                        inferred_edges.append({
                            "target_pipeline_id": pipeline_id,
                            "source_pipeline_id": source_pid,
                            "source_table": upstream_tid,
                            "target_table": task_id,
                            "edge_type": "reads_from",
                        })
            if inferred_edges:
                await self.lineage_repo.bulk_insert_edges(inferred_edges)
                logger.info("Inferred %d reads_from edges from DAG task graph", len(inferred_edges))

        return task_id_to_pipeline_id, synced

    async def _persist_resources(
        self,
        discovery: _TaskDiscoveryResult,
        task_id_to_pipeline_id: dict[str, uuid.UUID],
    ) -> int:
        """Pass 3: sync resource configs (per pipeline per DAG).

        Returns the number of resource config rows upserted.
        """
        resource_count = 0
        for task_id, dag_map in discovery.resource_by_dag.items():
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
                        "synced_at": datetime.now(UTC),
                    })
                    resource_count += 1
                except Exception:
                    logger.exception(
                        "Failed to sync resource config for %s in %s", task_id, dag_id
                    )

        return resource_count

    async def _persist_bouncers(
        self,
        discovery: _TaskDiscoveryResult,
    ) -> dict[str, uuid.UUID]:
        """Pass 4: upsert bouncers (volume_per_day preserved in DB — not overwritten).

        Returns bouncer_name -> bouncer UUID mapping for use in dag_task persistence.
        """
        # Load all known teams — includes any created during _persist_pipelines_and_lineage
        # since they are flushed to the same session.
        known_teams = await self.team_repo.get_all_names()

        bouncer_name_to_id: dict[str, uuid.UUID] = {}
        for bouncer_name, meta in discovery.seen_bouncers.items():
            display_name = task_id_to_display_name(bouncer_name)
            task_group = meta.get("task_group")
            team_name = extract_team_from_task_group(task_group, known_teams)
            bouncer = await self.bouncer_repo.upsert({
                "bouncer_name": bouncer_name,
                "display_name": display_name,
                "description": meta.get("description") or display_name,
                "team": team_name or "",
                "dag_ids": meta["dag_ids"],
            })
            bouncer_name_to_id[bouncer_name] = bouncer.id

        logger.info("Synced %d bouncers from Airflow", len(discovery.seen_bouncers))
        return bouncer_name_to_id

    async def _persist_dag_tasks(
        self,
        discovery: _TaskDiscoveryResult,
        task_id_to_pipeline_id: dict[str, uuid.UUID],
        bouncer_name_to_id: dict[str, uuid.UUID],
    ) -> None:
        """Pass 5: bulk sync DAG task graph (membership + downstream edges), delete stale entries."""
        current_pairs: set[tuple[str, str]] = set()
        entries_to_upsert: list[dict] = []
        for entry in discovery.dag_task_graph:
            entry["pipeline_id"] = task_id_to_pipeline_id.get(entry["task_id"])
            s_name = entry.get("bouncer_name")
            if s_name:
                entry["bouncer_id"] = bouncer_name_to_id.get(s_name)
            entries_to_upsert.append(entry)
            current_pairs.add((entry["dag_id"], entry["task_id"]))

        if entries_to_upsert:
            await self.dag_task_repo.bulk_upsert(entries_to_upsert)

        stale_deleted = await self.dag_task_repo.delete_stale(current_pairs)
        if stale_deleted:
            logger.info("Deleted %d stale dag_task entries", stale_deleted)

    # ──────────────────────────────────────────────────────────────────────────
    # sync_single_pipeline — private helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _identify_target_dags(
        self,
        task_id: str,
        known_dag_ids: list[str],
        all_dag_ids: list[str],
    ) -> _SingleSyncTargets:
        """Phase 1: identify target DAGs via cache + differential check for new DAGs."""
        cached_set = set(known_dag_ids)
        all_set = set(all_dag_ids)
        uncached_dag_ids = all_set - cached_set

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

        target_dag_ids = list(cached_set | new_dag_ids)
        return _SingleSyncTargets(
            target_dag_ids=target_dag_ids,
            cached_dag_ids=known_dag_ids,
            new_dag_ids=list(new_dag_ids),
        )

    async def _fetch_single_pipeline_metadata(
        self,
        task_id: str,
        targets: _SingleSyncTargets,
        all_dags: list[dict],
    ) -> dict:
        """Phase 2: fetch latest run + instances for all target DAGs in parallel.

        Returns a metadata dict with well-known keys for the caller plus private
        underscore-prefixed keys carrying ancillary data:
          _resource_by_dag, _best_status, _best_dag_id, _best_exec_date,
          _found_dags, _run_dag_ids, _instances_results
        """
        dag_runs_results = await asyncio.gather(*[
            _limited(airflow_client.get_dag_runs(dag_id, limit=1))
            for dag_id in targets.target_dag_ids
        ])

        dag_latest_run: dict[str, dict] = {}
        for dag_id, runs in zip(targets.target_dag_ids, dag_runs_results):
            if runs and runs[0].get("dag_run_id"):
                dag_latest_run[dag_id] = runs[0]

        if not dag_latest_run:
            raise AirflowSyncError(f"Task {task_id} not found in any Airflow DAG (no runs)")

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
                t["task_id"]: unwrap_params(t.get("params", {}))
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
                    destination_tables = parse_writes(log_content, task_id)
                    description = parse_description(log_content, task_id_to_display_name(task_id))
                    task_group = task_group_map.get(task_id) or None
                    params = params_by_task.get(airflow_task_id, {})

                    meta = {
                        "category": extract_category_from_task_group(task_group),
                        "schedule": extract_dag_schedule(dag_defs_by_id.get(dag_id, {})),
                        "destination_tables": destination_tables,
                        "description": description,
                        "needs": params.get("needs", []),
                    }
                break

        if meta is None:
            raise AirflowSyncError(f"Task {task_id} not found in any Airflow DAG")

        # Attach ancillary data as private keys for the caller
        meta["_resource_by_dag"] = resource_by_dag
        meta["_best_status"] = best_status
        meta["_best_dag_id"] = best_dag_id
        meta["_best_exec_date"] = best_exec_date
        meta["_found_dags"] = list(found_dags)
        meta["_run_dag_ids"] = run_dag_ids
        meta["_instances_results"] = instances_results

        return meta

    async def _persist_single_pipeline_data(
        self,
        task_id: str,
        pipeline_id: uuid.UUID,
        display_name: str,
        meta: dict,
        resource_by_dag: dict[str, dict],
    ) -> None:
        """Phase 3: pipeline upsert, lineage edges, and resource configs for a single pipeline."""
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
            upstream = await self.pipeline_repo.get_by_task_id(upstream_task_id)
            edges_to_create.append({
                "source_pipeline_id": upstream.id if upstream else None,
                "target_pipeline_id": pipeline_id,
                "source_table": upstream_task_id,
                "target_table": primary_table,
                "edge_type": "reads_from",
            })

        if not is_api(task_id):
            # Skip writes_to if pipeline has manual writes_to override
            if not getattr(pipeline, "writes_to_manual", None):
                for dest in meta["destination_tables"]:
                    edges_to_create.append({
                        "source_pipeline_id": pipeline_id,
                        "target_pipeline_id": None,
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
                    "synced_at": datetime.now(UTC),
                })
            except Exception:
                logger.exception(
                    "Failed to sync resource config for %s in %s", task_id, dag_id
                )

    async def _sync_run_history(
        self,
        pipeline_id: uuid.UUID,
        task_id: str,
        found_dags: list[str],
        run_dag_ids: list[str],
        instances_results: list[list],
    ) -> None:
        """Phase 4: fetch run history, write history rows, and update resource actuals from logs."""
        history_count = 0

        # Fetch 5 runs per DAG in parallel
        history_runs_results = await asyncio.gather(*[
            _limited(airflow_client.get_dag_runs(dag_id, limit=5))
            for dag_id in found_dags
        ])

        # Collect all (dag_id, dag_run_id) pairs
        all_run_pairs: list[tuple[str, str]] = []
        for dag_id, runs in zip(found_dags, history_runs_results):
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

                start_date = parse_datetime(inst.get("start_date"))
                end_date = parse_datetime(inst.get("end_date"))

                await self.resource_repo.upsert_run({
                    "pipeline_id": pipeline_id,
                    "dag_id": dag_id,
                    "dag_run_id": dag_run_id,
                    "duration_seconds": duration,
                    "start_date": start_date,
                    "end_date": end_date,
                    "status": status,
                })
                history_count += 1

                # Upsert clears actuals on re-run, so always
                # re-fetch for successful runs
                if status == "success":
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
                    actuals = parse_resource_actual(log_content)
                    plan_json = parse_execution_plan(log_content)
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

        logger.info("Recorded %d new run history entries for %s", history_count, task_id_to_display_name(task_id))
