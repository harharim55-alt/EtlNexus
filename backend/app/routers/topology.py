"""Pipeline topology endpoints — thin HTTP layer over TopologyService."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import get_current_user, require_pipeline_visibility
from app.cache import topology_cache
from app.dependencies import get_topology_service
from app.enums import UserRole
from app.models.user import User
from app.schemas.topology import TopologyGraph, UpstreamTopologyGraph
from app.services.topology_service import TopologyService

router = APIRouter(prefix="/api/pipelines", tags=["topology"])


def _topology_cache_key(
    user: User,
    pipeline_id: uuid.UUID,
    dag_id: str | None,
    *,
    prefix: str = "",
) -> str:
    """Build a user-aware, optionally-prefixed topology cache key.

    Args:
        user: Authenticated user — admins share a single key, others are
            segmented by user ID and team membership.
        pipeline_id: Pipeline UUID being requested.
        dag_id: Optional DAG filter applied to the topology.
        prefix: Optional string prepended to distinguish topology variants
            (e.g. ``"upstream:"``).

    Returns:
        Cache key string.
    """
    user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
    if user.role == UserRole.ADMIN:
        return f"{prefix}admin:{pipeline_id}:{dag_id}"
    team_hash = "|".join(sorted(str(t) for t in user_team_ids)) if user_team_ids else ""
    return f"{prefix}{user.id}:{team_hash}:{pipeline_id}:{dag_id}"


@router.get("/{pipeline_id}/topology", response_model=TopologyGraph, dependencies=[Depends(require_pipeline_visibility())])
async def get_pipeline_topology(
    pipeline_id: uuid.UUID,
    dag_id: str | None = Query(None, description="Filter topology to a specific DAG"),
    dag_run_id: str | None = Query(None, description="Historical run ID for per-run statuses"),
    user: User = Depends(get_current_user),
    service: TopologyService = Depends(get_topology_service),
):
    cache_key = _topology_cache_key(user, pipeline_id, dag_id)

    # Skip cache for historical runs (per-run status is unique)
    if not dag_run_id:
        cached = topology_cache.get(cache_key)
        if cached is not None:
            return cached

    result = await service.build_pipeline_topology(pipeline_id, dag_id, dag_run_id=dag_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found or has no task_id")

    if not dag_run_id:
        topology_cache.set(cache_key, result)
    return result


@router.get("/{pipeline_id}/topology/upstream", response_model=UpstreamTopologyGraph, dependencies=[Depends(require_pipeline_visibility())])
async def get_upstream_topology(
    pipeline_id: uuid.UUID,
    dag_id: str | None = Query(None, description="Filter to a specific DAG"),
    dag_run_id: str | None = Query(None, description="Historical run ID for per-run statuses"),
    user: User = Depends(get_current_user),
    service: TopologyService = Depends(get_topology_service),
):
    """Return the full recursive upstream dependency subgraph via BFS through needs/prefers."""
    cache_key = _topology_cache_key(user, pipeline_id, dag_id, prefix="upstream:")

    if not dag_run_id:
        cached = topology_cache.get(cache_key)
        if cached is not None:
            return cached

    result = await service.build_upstream_topology(pipeline_id, dag_id, dag_run_id=dag_run_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pipeline not found or has no task_id")

    if not dag_run_id:
        topology_cache.set(cache_key, result)
    return result
