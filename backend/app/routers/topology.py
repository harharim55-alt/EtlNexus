"""Pipeline topology endpoint — returns dependency graph from cached DAG task data."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.topology import TopologyGraph, TopologyTask

router = APIRouter(prefix="/api/pipelines", tags=["topology"])


@router.get("/{pipeline_id}/topology", response_model=TopologyGraph)
async def get_pipeline_topology(
    pipeline_id: uuid.UUID,
    dag_id: Optional[str] = Query(None, description="Filter topology to a specific DAG"),
    session: AsyncSession = Depends(get_db_session),
):
    pipeline_repo = PipelineRepository(session)
    dag_task_repo = DagTaskRepository(session)

    pipeline = await pipeline_repo.get_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    my_task_id = pipeline.task_id or pipeline.name.lower().replace(" ", "_")

    # Get all DAGs containing this task (from cached dag_tasks table)
    dag_entries = await dag_task_repo.get_dags_for_task(my_task_id)
    if not dag_entries:
        return TopologyGraph(
            pipeline_task_id=my_task_id,
            pipeline_status="unknown",
            dag_ids=[],
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
        tid = p.task_id or p.name.lower().replace(" ", "_")
        task_id_to_pipeline[tid] = p

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
        tid = p.task_id or p.name.lower().replace(" ", "_")
        if p.airflow_status:
            status_map[tid] = p.airflow_status.status

    for entry in active_entries:
        def _make_task(task_id: str, _did: str = entry.dag_id) -> TopologyTask:
            p = task_id_to_pipeline.get(task_id)
            return TopologyTask(
                task_id=task_id,
                pipeline_name=p.name if p else None,
                pipeline_id=str(p.id) if p else None,
                status=status_map.get(task_id, "unknown"),
                dag_id=_did,
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
        upstream_needs=list(merged_needs.values()),
        upstream_prefers=list(merged_prefers.values()),
        downstream=list(merged_downstream.values()),
    )
