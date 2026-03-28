"""DAG summary/statistics endpoint."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db_session
from app.dependencies import get_dag_summary_service, get_dag_task_repo
from app.models.pipeline import Pipeline
from app.models.user import User
from app.repositories.dag_task_repo import DagTaskRepository
from app.repositories.visibility_filter import VisibilityFilter
from app.schemas.dag_summary import DagSummaryResponse
from app.schemas.date_range import DateRangeParams
from app.services.dag_summary_service import DagSummaryService

router = APIRouter(prefix="/api/dags", tags=["dag-summary"])


@router.get("/summary", response_model=DagSummaryResponse)
async def get_dag_summary(
    dates: DateRangeParams = Depends(),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    dag_task_repo: DagTaskRepository = Depends(get_dag_task_repo),
    service: DagSummaryService = Depends(get_dag_summary_service),
) -> DagSummaryResponse:
    """Return DAG-level run summaries.

    Admins see all DAGs.  Non-admin users see only DAGs that contain at least
    one pipeline visible to them (own team, unassigned, or grant-accessible).
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

    return await service.get_dag_summaries(
        date_from=dates.date_from,
        date_to=dates.date_to,
        visible_dag_ids=visible_dag_ids,
    )
