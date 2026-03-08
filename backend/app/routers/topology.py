"""Pipeline topology endpoint — returns dependency graph from Airflow."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import get_pipeline_repo
from app.integrations.airflow_client import airflow_client
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.topology import TopologyGraph, TopologyTask
from app.services.airflow_service import TASK_STATE_MAP

router = APIRouter(prefix="/api/pipelines", tags=["topology"])


def _pipeline_name_to_task_id(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


@router.get("/{pipeline_id}/topology", response_model=TopologyGraph)
async def get_pipeline_topology(
    pipeline_id: uuid.UUID,
    dag_id: Optional[str] = Query(None, description="Filter topology to a specific DAG"),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
):
    pipeline = await pipeline_repo.get_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    my_task_id = _pipeline_name_to_task_id(pipeline.name)

    # Discover which DAGs contain this task
    all_dag_ids: list[str] = []
    all_dags = await airflow_client.get_all_dags()
    for d in all_dags:
        did = d.get("dag_id", "")
        tasks = await airflow_client.get_dag_tasks(did)
        task_ids = [t["task_id"] for t in tasks]
        if my_task_id in task_ids:
            all_dag_ids.append(did)

    if not all_dag_ids:
        return TopologyGraph(
            pipeline_task_id=my_task_id,
            pipeline_status="unknown",
            dag_ids=[],
            upstream_needs=[],
            upstream_prefers=[],
            downstream=[],
        )

    # If a specific DAG is requested, filter to only that DAG
    active_dag_ids = [dag_id] if dag_id and dag_id in all_dag_ids else all_dag_ids

    # Build pipeline name lookup
    all_pipelines = await pipeline_repo.get_all()
    task_id_to_pipeline = {}
    for p in all_pipelines:
        tid = _pipeline_name_to_task_id(p.name)
        task_id_to_pipeline[tid] = p

    merged_needs: dict[str, TopologyTask] = {}
    merged_prefers: dict[str, TopologyTask] = {}
    merged_downstream: dict[str, TopologyTask] = {}
    best_status = "unknown"
    best_exec_date = None

    for active_did in active_dag_ids:
        tasks_def = await airflow_client.get_dag_tasks(active_did)
        if not tasks_def:
            continue

        downstream_map: dict[str, list[str]] = {}
        for t in tasks_def:
            downstream_map[t["task_id"]] = t.get("downstream_task_ids", [])

        runs = await airflow_client.get_dag_runs(active_did, limit=1)
        status_map: dict[str, str] = {}
        needs_list: list[str] = []
        prefers_list: list[str] = []
        exec_date_str = None

        if runs:
            run = runs[0]
            dag_run_id = run.get("dag_run_id")
            exec_date_str = run.get("execution_date")
            if dag_run_id:
                instances = await airflow_client.get_task_instances(active_did, dag_run_id)
                for inst in instances:
                    tid = inst["task_id"]
                    raw_state = inst.get("state", "unknown")
                    status_map[tid] = TASK_STATE_MAP.get(raw_state, "unknown")

                    if tid == my_task_id:
                        rendered = inst.get("rendered_fields", {}) or {}
                        op_kwargs = rendered.get("op_kwargs", {}) or {}
                        needs_list = op_kwargs.get("needs", [])
                        prefers_list = op_kwargs.get("prefers", [])

        def _make_task(task_id: str, _did: str = active_did) -> TopologyTask:
            p = task_id_to_pipeline.get(task_id)
            return TopologyTask(
                task_id=task_id,
                pipeline_name=p.name if p else None,
                pipeline_id=str(p.id) if p else None,
                status=status_map.get(task_id, "unknown"),
                dag_id=_did,
            )

        for tid in needs_list:
            if tid in downstream_map and tid not in merged_needs:
                merged_needs[tid] = _make_task(tid)

        for tid in prefers_list:
            if tid in downstream_map and tid not in merged_prefers:
                merged_prefers[tid] = _make_task(tid)

        for tid in downstream_map.get(my_task_id, []):
            if tid not in merged_downstream:
                merged_downstream[tid] = _make_task(tid)

        my_status = status_map.get(my_task_id)
        if my_status and (best_exec_date is None or (exec_date_str and exec_date_str > (best_exec_date or ""))):
            best_status = my_status
            best_exec_date = exec_date_str

    return TopologyGraph(
        pipeline_task_id=my_task_id,
        pipeline_status=best_status,
        dag_ids=all_dag_ids,
        upstream_needs=list(merged_needs.values()),
        upstream_prefers=list(merged_prefers.values()),
        downstream=list(merged_downstream.values()),
    )
