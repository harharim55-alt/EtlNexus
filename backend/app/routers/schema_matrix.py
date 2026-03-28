import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db_session
from app.dependencies import get_schema_matrix_service
from app.models.pipeline import Pipeline
from app.models.user import User
from app.repositories.visibility_filter import VisibilityFilter
from app.schemas.schema_matrix import SchemaMatrixResponse
from app.services.schema_matrix_service import SchemaMatrixService

router = APIRouter(prefix="/api/schema-matrix", tags=["schema-matrix"])


@router.get("", response_model=SchemaMatrixResponse)
async def get_schema_matrix(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    q: str | None = Query(None, max_length=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    service: SchemaMatrixService = Depends(get_schema_matrix_service),
) -> SchemaMatrixResponse:
    """Return cross-pipeline field frequency matrix.

    Admins see all pipelines.  Non-admin users see only fields from pipelines
    that are visible to them (own team, unassigned, or grant-accessible).
    """
    visible_pipeline_ids: set[uuid.UUID] | None = None

    if user.role != "admin":
        user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
        visibility_conditions = await VisibilityFilter.build_batch_visibility_conditions(
            session=session,
            user_id=user.id,
            user_team_ids=user_team_ids,
        )
        from sqlalchemy import or_
        id_stmt = select(Pipeline.id).where(or_(*visibility_conditions))
        result = await session.execute(id_stmt)
        visible_pipeline_ids = {row[0] for row in result.all()}

    return await service.get_schema_matrix(
        skip=skip,
        limit=limit,
        q=q,
        visible_pipeline_ids=visible_pipeline_ids,
    )
