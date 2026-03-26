"""Pipeline topology endpoints — thin HTTP layer over TopologyService."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.cache import topology_cache
from app.database import get_db_session
from app.models.user import User
from app.schemas.topology import TopologyGraph, UpstreamTopologyGraph
from app.services.topology_service import TopologyService

router = APIRouter(prefix="/api/pipelines", tags=["topology"])


@router.get("/{pipeline_id}/topology", response_model=TopologyGraph)
async def get_pipeline_topology(
    pipeline_id: uuid.UUID,
    dag_id: str | None = Query(None, description="Filter topology to a specific DAG"),
    dag_run_id: str | None = Query(None, description="Historical run ID for per-run statuses"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    # Skip cache for historical runs (per-run status is unique)
    if not dag_run_id:
        cache_key = f"{pipeline_id}:{dag_id}"
        cached = topology_cache.get(cache_key)
        if cached is not None:
            return cached

    service = TopologyService(session)
    result = await service.build_pipeline_topology(pipeline_id, dag_id, dag_run_id=dag_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found or has no task_id")

    if not dag_run_id:
        topology_cache.set(cache_key, result)
    return result


@router.get("/{pipeline_id}/topology/upstream", response_model=UpstreamTopologyGraph)
async def get_upstream_topology(
    pipeline_id: uuid.UUID,
    dag_id: str | None = Query(None, description="Filter to a specific DAG"),
    dag_run_id: str | None = Query(None, description="Historical run ID for per-run statuses"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Return the full recursive upstream dependency subgraph via BFS through needs/prefers."""
    if not dag_run_id:
        cache_key = f"upstream:{pipeline_id}:{dag_id}"
        cached = topology_cache.get(cache_key)
        if cached is not None:
            return cached

    service = TopologyService(session)
    result = await service.build_upstream_topology(pipeline_id, dag_id, dag_run_id=dag_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found or has no task_id")

    if not dag_run_id:
        topology_cache.set(cache_key, result)
    return result
