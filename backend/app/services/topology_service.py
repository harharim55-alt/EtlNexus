"""Topology service — builds pipeline dependency graphs from cached DAG task data."""

import uuid
from collections import defaultdict

from app.repositories.bouncer_repo import BouncerRepository
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.resource_repo import ResourceRepository
from app.schemas.topology import (
    TopologyBouncer,
    TopologyGraph,
    TopologyTask,
    UpstreamEdge,
    UpstreamNode,
    UpstreamTopologyGraph,
)
from app.services.graph_builder import (
    bfs_bouncer_discovery,
    bfs_find_bouncers,
    bfs_upstream_semantic,
    connect_bouncers_forward,
)


class TopologyService:
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        dag_task_repo: DagTaskRepository,
        bouncer_repo: BouncerRepository,
        resource_repo: ResourceRepository,
    ):
        self.pipeline_repo = pipeline_repo
        self.dag_task_repo = dag_task_repo
        self.bouncer_repo = bouncer_repo
        self.resource_repo = resource_repo

    async def _build_status_map(
        self,
        dag_run_id: str | None,
        task_id_to_pipeline: dict,
    ) -> dict[str, str]:
        """Build a task_id -> status mapping.

        When ``dag_run_id`` is provided the historical run status table is
        used as the primary source; live ``AirflowRunStatus`` values are used
        to fill any gaps (e.g. still-running tasks not yet persisted).
        Without a ``dag_run_id`` only live statuses are used.

        Args:
            dag_run_id: Optional historical DAG run identifier.
            task_id_to_pipeline: Lightweight pipeline projection keyed by task_id.

        Returns:
            Mapping of task_id to status string.
        """
        if dag_run_id:
            run_statuses = await self.resource_repo.get_statuses_for_dag_run(dag_run_id)
            status_map: dict[str, str] = dict(run_statuses)
            # Fill gaps from live AirflowRunStatus for tasks without a run
            # history entry yet (e.g. running/queued/scheduled tasks).
            for tid, p in task_id_to_pipeline.items():
                if tid not in status_map and p.status and p.status != "unknown":
                    status_map[tid] = p.status
        else:
            status_map = {}
            for tid, p in task_id_to_pipeline.items():
                if p.status and p.status != "unknown":
                    status_map[tid] = p.status
        return status_map

    async def build_pipeline_topology(
        self, pipeline_id: uuid.UUID, dag_id: str | None = None,
        dag_run_id: str | None = None,
    ) -> TopologyGraph | None:
        """Build direct dependency topology for a pipeline.

        Returns None if pipeline not found or has no task_id.
        Returns empty TopologyGraph if pipeline has no DAG entries.
        """
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        my_task_id = pipeline.task_id
        if not my_task_id:
            return None

        dag_entries = await self.dag_task_repo.get_dags_for_task(my_task_id)
        if not dag_entries:
            return TopologyGraph(
                pipeline_task_id=my_task_id,
                pipeline_status="unknown",
                dag_ids=[],
                upstream_bouncers=[],
                upstream_needs=[],
                upstream_prefers=[],
                downstream=[],
            )

        all_dag_ids = [e.dag_id for e in dag_entries]

        # Filter to specific DAG if requested
        if dag_id and dag_id in all_dag_ids:
            active_entries = [e for e in dag_entries if e.dag_id == dag_id]
        else:
            active_entries = dag_entries

        # Build pipeline lookup from DB (lightweight projection, no ORM relationships)
        task_id_to_pipeline = await self.pipeline_repo.get_task_id_map()

        # Build task_group_id lookup from all active dag_task entries
        task_group_lookup: dict[tuple[str, str], str | None] = {}
        for entry in active_entries:
            for tid in (entry.needs or []) + (entry.prefers or []) + (entry.downstream_task_ids or []):
                task_group_lookup[(entry.dag_id, tid)] = None

        # Fetch all tasks per active DAG (used for task_group lookup + bouncer BFS)
        active_dag_ids = {e.dag_id for e in active_entries}
        dag_tasks_by_dag: dict[str, list] = {}
        reverse_adj: dict[str, dict[str, set[str]]] = {}

        for adid in active_dag_ids:
            all_tasks_in_dag = await self.dag_task_repo.get_tasks_for_dag(adid)
            dag_tasks_by_dag[adid] = all_tasks_in_dag
            reverse_adj[adid] = defaultdict(set)
            for dt in all_tasks_in_dag:
                task_group_lookup[(dt.dag_id, dt.task_id)] = dt.task_group_id
                for downstream_tid in dt.downstream_task_ids or []:
                    reverse_adj[adid][downstream_tid].add(dt.task_id)

        # BFS upstream from current task to find ancestor bouncers
        found_bouncers: dict[str, set[str]] = bfs_find_bouncers(
            root_task_id=my_task_id,
            dag_tasks_by_dag=dag_tasks_by_dag,
            reverse_adj=reverse_adj,
            active_dag_ids=active_dag_ids,
        )

        # Enrich bouncers from DB
        upstream_bouncers_list = await self._enrich_bouncers(found_bouncers)

        # Build status map — historical (per-run) or current (live Airflow)
        status_map = await self._build_status_map(dag_run_id, task_id_to_pipeline)
        if dag_run_id:
            pipeline_status = status_map.get(my_task_id, "unknown")
        else:
            pipeline_status = "unknown"
            if pipeline.airflow_status:
                pipeline_status = pipeline.airflow_status.status

        merged_needs: dict[str, TopologyTask] = {}
        merged_prefers: dict[str, TopologyTask] = {}
        merged_downstream: dict[str, TopologyTask] = {}

        for entry in active_entries:
            def _make_task(task_id: str, _did: str = entry.dag_id) -> TopologyTask:
                p = task_id_to_pipeline.get(task_id)
                return TopologyTask(
                    task_id=task_id,
                    pipeline_name=p.name if p else None,
                    pipeline_id=str(p.id) if p else None,
                    status=status_map.get(task_id, "unknown"),
                    dag_id=_did,
                    task_group_id=task_group_lookup.get((_did, task_id)),
                )

            for tid in entry.needs or []:
                if tid not in merged_needs:
                    merged_needs[tid] = _make_task(tid)

            for tid in entry.prefers or []:
                if tid not in merged_prefers:
                    merged_prefers[tid] = _make_task(tid)

            for tid in entry.downstream_task_ids or []:
                if tid not in merged_downstream:
                    merged_downstream[tid] = _make_task(tid)

        return TopologyGraph(
            pipeline_task_id=my_task_id,
            pipeline_status=pipeline_status,
            dag_ids=all_dag_ids,
            upstream_bouncers=upstream_bouncers_list,
            upstream_needs=list(merged_needs.values()),
            upstream_prefers=list(merged_prefers.values()),
            downstream=list(merged_downstream.values()),
        )

    async def build_upstream_topology(
        self, pipeline_id: uuid.UUID, dag_id: str | None = None,
        dag_run_id: str | None = None,
    ) -> UpstreamTopologyGraph | None:
        """Build full recursive upstream dependency subgraph via BFS through needs/prefers.

        Returns None if pipeline not found or has no task_id.
        """
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        my_task_id = pipeline.task_id
        if not my_task_id:
            return None

        # Resolve pipeline status — derived from status_map built later.
        # We compute it eagerly here only for the early-return (no dag_entries) path.
        pipeline_status = "unknown"
        if pipeline.airflow_status:
            pipeline_status = pipeline.airflow_status.status

        dag_entries = await self.dag_task_repo.get_dags_for_task(my_task_id)
        if not dag_entries:
            return UpstreamTopologyGraph(
                pipeline_task_id=my_task_id,
                pipeline_status=pipeline_status,
                dag_id=dag_id,
                dag_ids=[],
                nodes=[UpstreamNode(
                    task_id=my_task_id,
                    pipeline_name=pipeline.name,
                    pipeline_id=str(pipeline.id),
                    status=pipeline_status,
                    dag_id="",
                    depth=0,
                    is_current=True,
                )],
                edges=[],
                bouncers=[],
                max_depth=0,
            )

        all_dag_ids = sorted({e.dag_id for e in dag_entries})
        # Per-DAG only: default to first DAG when no filter specified
        if dag_id and dag_id in all_dag_ids:
            active_dag_ids = {dag_id}
        else:
            dag_id = all_dag_ids[0]
            active_dag_ids = {dag_id}

        # Load all tasks per active DAG into lookup + build reverse adjacency
        tid_to_dt: dict[str, object] = {}
        task_group_lookup: dict[str, str | None] = {}
        reverse_adj: dict[str, set[str]] = defaultdict(set)

        for adid in active_dag_ids:
            all_tasks_in_dag = await self.dag_task_repo.get_tasks_for_dag(adid)
            for dt in all_tasks_in_dag:
                if dt.task_id not in tid_to_dt:
                    tid_to_dt[dt.task_id] = dt
                task_group_lookup[dt.task_id] = dt.task_group_id
                for downstream_tid in dt.downstream_task_ids or []:
                    reverse_adj[downstream_tid].add(dt.task_id)

        # Build pipeline lookup for enrichment (lightweight projection, no ORM relationships)
        task_id_to_pipeline = await self.pipeline_repo.get_task_id_map()

        # Status map — historical or current
        status_map = await self._build_status_map(dag_run_id, task_id_to_pipeline)
        if dag_run_id:
            pipeline_status = status_map.get(my_task_id, "unknown")

        # BFS through needs/prefers (semantic data dependencies)
        visited, raw_edges = bfs_upstream_semantic(
            root_task_id=my_task_id,
            tid_to_dt=tid_to_dt,
        )
        edges: list[UpstreamEdge] = [
            UpstreamEdge(source_task_id=src, target_task_id=tgt, edge_type=etype)
            for src, tgt, etype in raw_edges
        ]

        # Bouncer discovery via reverse_adj BFS from all visited tasks
        found_bouncers: dict[str, set[str]] = bfs_bouncer_discovery(
            visited=visited,
            tid_to_dt=tid_to_dt,
            reverse_adj=reverse_adj,
            active_dag_id=dag_id,
        )

        # Build ETL nodes
        nodes: list[UpstreamNode] = []
        for tid, depth in visited.items():
            p = task_id_to_pipeline.get(tid)
            dt = tid_to_dt.get(tid)
            nodes.append(UpstreamNode(
                task_id=tid,
                pipeline_name=p.name if p else None,
                pipeline_id=str(p.id) if p else None,
                status=status_map.get(tid, "unknown"),
                dag_id=dt.dag_id if dt else "",
                task_group_id=task_group_lookup.get(tid),
                depth=depth,
                is_current=(tid == my_task_id),
            ))

        max_depth = max(visited.values()) if visited else 0

        # Enrich bouncers from DB and add as graph nodes with edges
        upstream_bouncers_list = await self._enrich_bouncers(found_bouncers)

        if found_bouncers:
            bouncer_depth = max_depth + 1
            bouncer_names_list = list(found_bouncers.keys())
            bouncers_db = await self.bouncer_repo.get_by_names(bouncer_names_list)
            bouncer_by_name = {s.bouncer_name: s for s in bouncers_db}

            bouncer_connections = connect_bouncers_forward(
                found_bouncers=found_bouncers,
                tid_to_dt=tid_to_dt,
                visited=visited,
            )
            bouncer_edge_lookup: dict[str, list[str]] = defaultdict(list)
            for sname, connected_tid in bouncer_connections:
                bouncer_edge_lookup[sname].append(connected_tid)

            for sname in sorted(found_bouncers.keys()):
                s = bouncer_by_name.get(sname)
                bouncer_dt = tid_to_dt.get(sname)
                nodes.append(UpstreamNode(
                    task_id=sname,
                    pipeline_name=s.display_name if s else sname.replace("_", " ").title(),
                    pipeline_id=None,
                    status=s.status if s else "unknown",
                    dag_id=bouncer_dt.dag_id if bouncer_dt else dag_id,
                    task_group_id=None,
                    depth=bouncer_depth,
                    is_current=False,
                    is_bouncer=True,
                    bouncer_name=sname,
                ))

                for connected_tid in bouncer_edge_lookup.get(sname, []):
                    edges.append(UpstreamEdge(
                        source_task_id=sname,
                        target_task_id=connected_tid,
                        edge_type="needs",
                    ))

            max_depth = bouncer_depth

        return UpstreamTopologyGraph(
            pipeline_task_id=my_task_id,
            pipeline_status=pipeline_status,
            dag_id=dag_id,
            dag_ids=all_dag_ids,
            nodes=nodes,
            edges=edges,
            bouncers=upstream_bouncers_list,
            max_depth=max_depth,
        )

    async def _enrich_bouncers(
        self, found_bouncers: dict[str, set[str]],
    ) -> list[TopologyBouncer]:
        """Enrich discovered bouncer names with DB metadata."""
        if not found_bouncers:
            return []

        bouncer_names_list = list(found_bouncers.keys())
        bouncers_db = await self.bouncer_repo.get_by_names(bouncer_names_list)
        bouncer_by_name = {s.bouncer_name: s for s in bouncers_db}

        result: list[TopologyBouncer] = []
        for sname, dag_id_set in sorted(found_bouncers.items()):
            s = bouncer_by_name.get(sname)
            result.append(
                TopologyBouncer(
                    bouncer_name=sname,
                    display_name=s.display_name if s else sname.replace("_", " ").title(),
                    sensor_id=str(s.id) if s else None,
                    status=s.status if s else None,
                    team=s.team if s else None,
                    volume_per_day=s.volume_per_day if s else None,
                    dag_ids=sorted(dag_id_set),
                )
            )
        return result
