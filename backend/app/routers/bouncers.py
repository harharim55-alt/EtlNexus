"""Bouncer endpoints — list bouncers and query downstream topology."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db_session
from app.dependencies import get_bouncer_service, get_dag_task_repo
from app.models.pipeline import Pipeline
from app.models.user import User
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.visibility_filter import VisibilityFilter
from app.schemas.bouncer import BouncerListResponse, BouncerTopologyResponse
from app.services.bouncer_service import BouncerService

router = APIRouter(prefix="/api/bouncers", tags=["bouncers"])


@router.get("", response_model=BouncerListResponse)
async def list_bouncers(
    team: str | None = Query(None, description="Filter by team name"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
    service: BouncerService = Depends(get_bouncer_service),
) -> BouncerListResponse:
    """List bouncers visible to the requesting user.

    Admins see all bouncers.  Non-admin users see only bouncers associated
    with DAGs that contain at least one pipeline visible to them.
    """
    visible_dag_ids: set[str] | None = None

    if user.role != "admin":
        user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
        visibility_conditions = await VisibilityFilter.build_batch_visibility_conditions(
            session=session,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        id_stmt = select(Pipeline.id).where(or_(*visibility_conditions))
        result = await session.execute(id_stmt)
        visible_pipeline_ids: set[uuid.UUID] = {row[0] for row in result.all()}
        visible_dag_ids = await dag_task_repo.get_dag_ids_for_pipelines(visible_pipeline_ids)

    return await service.get_all_bouncers(team=team, visible_dag_ids=visible_dag_ids)


@router.get("/topology", response_model=BouncerTopologyResponse)
async def get_bouncer_topology(
    bouncers: list[str] = Query(..., description="Bouncer names to query"),
    mode: str = Query("union", description="union or intersection"),
    user: User = Depends(get_current_user),
    service: BouncerService = Depends(get_bouncer_service),
) -> BouncerTopologyResponse:
    return await service.get_bouncer_topology(bouncer_names=bouncers, mode=mode)
