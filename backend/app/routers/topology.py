"""Pipeline topology endpoint — returns dependency graph from cached DAG task data."""

import uuid
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.cache import topology_cache
from app.database import get_db_session
from app.models.user import User
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.sensor_repo import SensorRepository
from app.schemas.topology import (
    TopologyGraph,
    TopologySensor,
    TopologyTask,
    UpstreamEdge,
    UpstreamNode,
    UpstreamTopologyGraph,
)

router = APIRouter(prefix="/api/pipelines", tags=["topology"])


@router.get("/{pipeline_id}/topology", response_model=TopologyGraph)
async def get_pipeline_topology(
    pipeline_id: uuid.UUID,
    dag_id: str | None = Query(None, description="Filter topology to a specific DAG"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    cache_key = f"{pipeline_id}:{dag_id}"
    cached = topology_cache.get(cache_key)
    if cached is not None:
        return cached

    pipeline_repo = PipelineRepository(session)
    dag_task_repo = DagTaskRepository(session)

    pipeline = await pipeline_repo.get_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    my_task_id = pipeline.task_id
    if not my_task_id:
        raise HTTPException(status_code=404, detail="Pipeline has no task_id")

    # Get all DAGs containing this task (from cached dag_tasks table)
    dag_entries = await dag_task_repo.get_dags_for_task(my_task_id)
    if not dag_entries:
        return TopologyGraph(
            pipeline_task_id=my_task_id,
            pipeline_status="unknown",
            dag_ids=[],
            upstream_sensors=[],
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

    # Build pipeline lookup from DB
    all_pipelines = await pipeline_repo.get_all()
    task_id_to_pipeline = {}
    for p in all_pipelines:
        if p.task_id:
            task_id_to_pipeline[p.task_id] = p

    # Build task_group_id lookup from all active dag_task entries
    # Key: (dag_id, task_id) -> task_group_id
    task_group_lookup: dict[tuple[str, str], str | None] = {}
    for entry in active_entries:
        for tid in (entry.needs or []) + (entry.prefers or []) + (entry.downstream_task_ids or []):
            task_group_lookup[(entry.dag_id, tid)] = None

    # Fetch all tasks per active DAG (used for task_group lookup + sensor BFS)
    active_dag_ids = {e.dag_id for e in active_entries}
    dag_tasks_by_dag: dict[str, list] = {}
    reverse_adj: dict[str, dict[str, set[str]]] = {}

    for adid in active_dag_ids:
        all_tasks_in_dag = await dag_task_repo.get_tasks_for_dag(adid)
        dag_tasks_by_dag[adid] = all_tasks_in_dag
        reverse_adj[adid] = defaultdict(set)
        for dt in all_tasks_in_dag:
            task_group_lookup[(dt.dag_id, dt.task_id)] = dt.task_group_id
            for downstream_tid in dt.downstream_task_ids or []:
                reverse_adj[adid][downstream_tid].add(dt.task_id)

    # BFS upstream from current task to find ancestor sensors
    found_sensors: dict[str, set[str]] = {}  # sensor_name -> dag_ids
    for adid in active_dag_ids:
        tid_to_dt = {dt.task_id: dt for dt in dag_tasks_by_dag[adid]}
        visited: set[str] = set()
        queue = [my_task_id]
        while queue:
            tid = queue.pop(0)
            if tid in visited:
                continue
            visited.add(tid)
            dt_entry = tid_to_dt.get(tid)
            if dt_entry and dt_entry.sensor_name:
                found_sensors.setdefault(dt_entry.sensor_name, set()).add(adid)
                continue  # sensors are terminal roots
            for upstream_tid in reverse_adj[adid].get(tid, set()):
                if upstream_tid not in visited:
                    queue.append(upstream_tid)

    # Enrich sensors from DB
    sensor_repo = SensorRepository(session)
    sensor_names_list = list(found_sensors.keys())
    sensors_db = await sensor_repo.get_by_names(sensor_names_list) if sensor_names_list else []
    sensor_by_name = {s.sensor_name: s for s in sensors_db}

    upstream_sensors: list[TopologySensor] = []
    for sname, dag_id_set in sorted(found_sensors.items()):
        s = sensor_by_name.get(sname)
        upstream_sensors.append(
            TopologySensor(
                sensor_name=sname,
                display_name=s.display_name if s else sname.replace("_", " ").title(),
                sensor_id=str(s.id) if s else None,
                status=s.status if s else None,
                team=s.team if s else None,
                volume_per_day=s.volume_per_day if s else None,
                dag_ids=sorted(dag_id_set),
            )
        )

    # Get status from airflow_run_statuses (already in DB)
    pipeline_status = "unknown"
    if pipeline.airflow_status:
        pipeline_status = pipeline.airflow_status.status

    merged_needs: dict[str, TopologyTask] = {}
    merged_prefers: dict[str, TopologyTask] = {}
    merged_downstream: dict[str, TopologyTask] = {}

    # Build status map from all pipelines' airflow_status
    status_map: dict[str, str] = {}
    for p in all_pipelines:
        if p.task_id and p.airflow_status:
            status_map[p.task_id] = p.airflow_status.status

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

    result = TopologyGraph(
        pipeline_task_id=my_task_id,
        pipeline_status=pipeline_status,
        dag_ids=all_dag_ids,
        upstream_sensors=upstream_sensors,
        upstream_needs=list(merged_needs.values()),
        upstream_prefers=list(merged_prefers.values()),
        downstream=list(merged_downstream.values()),
    )
    topology_cache.set(cache_key, result)
    return result


@router.get("/{pipeline_id}/topology/upstream", response_model=UpstreamTopologyGraph)
async def get_upstream_topology(
    pipeline_id: uuid.UUID,
    dag_id: str | None = Query(None, description="Filter to a specific DAG"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Return the full recursive upstream dependency subgraph via BFS through needs/prefers."""
    pipeline_repo = PipelineRepository(session)
    dag_task_repo = DagTaskRepository(session)

    pipeline = await pipeline_repo.get_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    my_task_id = pipeline.task_id
    if not my_task_id:
        raise HTTPException(status_code=404, detail="Pipeline has no task_id")

    dag_entries = await dag_task_repo.get_dags_for_task(my_task_id)
    if not dag_entries:
        pipeline_status = "unknown"
        if pipeline.airflow_status:
            pipeline_status = pipeline.airflow_status.status
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
            sensors=[],
            max_depth=0,
        )

    all_dag_ids = sorted({e.dag_id for e in dag_entries})
    # Per-DAG only: default to first DAG when no filter specified
    if dag_id and dag_id in all_dag_ids:
        active_dag_ids = {dag_id}
    else:
        dag_id = all_dag_ids[0]
        active_dag_ids = {dag_id}

    # Cache check after resolving dag_id so keys are consistent
    cache_key = f"upstream:{pipeline_id}:{dag_id}"
    cached = topology_cache.get(cache_key)
    if cached is not None:
        return cached

    # Load all tasks per active DAG into lookup + build reverse adjacency for sensor BFS
    tid_to_dt: dict[str, object] = {}  # task_id -> DagTask (first DAG wins)
    task_group_lookup: dict[str, str | None] = {}
    reverse_adj: dict[str, set[str]] = defaultdict(set)  # downstream_tid -> set of upstream tids

    for adid in active_dag_ids:
        all_tasks_in_dag = await dag_task_repo.get_tasks_for_dag(adid)
        for dt in all_tasks_in_dag:
            if dt.task_id not in tid_to_dt:
                tid_to_dt[dt.task_id] = dt
            task_group_lookup[dt.task_id] = dt.task_group_id
            # Build reverse adjacency from Airflow's >> operator (downstream_task_ids)
            for downstream_tid in dt.downstream_task_ids or []:
                reverse_adj[downstream_tid].add(dt.task_id)

    # Build pipeline lookup for enrichment
    all_pipelines = await pipeline_repo.get_all()
    task_id_to_pipeline = {}
    status_map: dict[str, str] = {}
    for p in all_pipelines:
        if not p.task_id:
            continue
        task_id_to_pipeline[p.task_id] = p
        if p.airflow_status:
            status_map[p.task_id] = p.airflow_status.status

    pipeline_status = "unknown"
    if pipeline.airflow_status:
        pipeline_status = pipeline.airflow_status.status

    # BFS through needs/prefers (semantic data dependencies)
    visited: dict[str, int] = {}  # task_id -> depth
    edges: list[UpstreamEdge] = []
    queue: list[tuple[str, int]] = [(my_task_id, 0)]

    while queue:
        tid, depth = queue.pop(0)
        if tid in visited:
            continue
        visited[tid] = depth

        dt = tid_to_dt.get(tid)
        if not dt:
            continue

        # Traverse needs
        for dep_tid in dt.needs or []:
            edges.append(UpstreamEdge(
                source_task_id=dep_tid,
                target_task_id=tid,
                edge_type="needs",
            ))
            if dep_tid not in visited:
                queue.append((dep_tid, depth + 1))

        # Traverse prefers
        for dep_tid in dt.prefers or []:
            edges.append(UpstreamEdge(
                source_task_id=dep_tid,
                target_task_id=tid,
                edge_type="prefers",
            ))
            if dep_tid not in visited:
                queue.append((dep_tid, depth + 1))

    # Sensor discovery: sensors connect to root ETLs via Airflow's >> operator.
    # BFS upstream from all visited tasks using reverse_adj to find ancestor sensor tasks.
    found_sensors: dict[str, set[str]] = {}  # sensor_name -> dag_ids
    sensor_visited: set[str] = set()
    sensor_queue = list(visited.keys())
    while sensor_queue:
        tid = sensor_queue.pop(0)
        if tid in sensor_visited:
            continue
        sensor_visited.add(tid)
        for upstream_tid in reverse_adj.get(tid, set()):
            if upstream_tid in sensor_visited:
                continue
            dt_entry = tid_to_dt.get(upstream_tid)
            if dt_entry and dt_entry.sensor_name:
                found_sensors.setdefault(dt_entry.sensor_name, set()).add(dag_id)
            elif upstream_tid not in visited:
                sensor_queue.append(upstream_tid)

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

    # Enrich sensors from DB and add them as graph nodes with edges
    sensor_repo = SensorRepository(session)
    sensor_names_list = list(found_sensors.keys())
    sensors_db = await sensor_repo.get_by_names(sensor_names_list) if sensor_names_list else []
    sensor_by_name = {s.sensor_name: s for s in sensors_db}

    upstream_sensors: list[TopologySensor] = []
    if found_sensors:
        sensor_depth = max_depth + 1
        for sname, dag_id_set in sorted(found_sensors.items()):
            s = sensor_by_name.get(sname)
            upstream_sensors.append(
                TopologySensor(
                    sensor_name=sname,
                    display_name=s.display_name if s else sname.replace("_", " ").title(),
                    sensor_id=str(s.id) if s else None,
                    status=s.status if s else None,
                    team=s.team if s else None,
                    volume_per_day=s.volume_per_day if s else None,
                    dag_ids=sorted(dag_id_set),
                )
            )

            # Add sensor as a graph node at sensor_depth
            sensor_dt = tid_to_dt.get(sname)
            nodes.append(UpstreamNode(
                task_id=sname,
                pipeline_name=s.display_name if s else sname.replace("_", " ").title(),
                pipeline_id=None,
                status=s.status if s else "unknown",
                dag_id=sensor_dt.dag_id if sensor_dt else dag_id,
                task_group_id=None,
                depth=sensor_depth,
                is_current=False,
                is_sensor=True,
                sensor_name=sname,
            ))

            # Connect sensor to visited ETL tasks it feeds (via downstream_task_ids BFS)
            if sensor_dt:
                fwd_queue = list(sensor_dt.downstream_task_ids or [])
                fwd_seen: set[str] = set()
                while fwd_queue:
                    next_tid = fwd_queue.pop(0)
                    if next_tid in fwd_seen:
                        continue
                    fwd_seen.add(next_tid)
                    if next_tid in visited:
                        edges.append(UpstreamEdge(
                            source_task_id=sname,
                            target_task_id=next_tid,
                            edge_type="needs",
                        ))
                        continue
                    # Follow through intermediate non-ETL tasks
                    dt_next = tid_to_dt.get(next_tid)
                    if dt_next:
                        for dtid in dt_next.downstream_task_ids or []:
                            if dtid not in fwd_seen:
                                fwd_queue.append(dtid)

        max_depth = sensor_depth

    result = UpstreamTopologyGraph(
        pipeline_task_id=my_task_id,
        pipeline_status=pipeline_status,
        dag_id=dag_id,
        dag_ids=all_dag_ids,
        nodes=nodes,
        edges=edges,
        sensors=upstream_sensors,
        max_depth=max_depth,
    )
    topology_cache.set(cache_key, result)
    return result
