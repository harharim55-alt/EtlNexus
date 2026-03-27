"""AI architect endpoint — chat and join insights."""

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_pipeline_visibility
from app.database import get_db_session
from app.dependencies import get_ai_service
from app.models.pipeline import Pipeline
from app.models.user import User
from app.rate_limit import limiter
from app.repositories.visibility_filter import VisibilityFilter
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/ai/chat", response_model=AIChatResponse)
@limiter.limit("60/minute")
async def ai_chat(
    request: Request,
    body: AIChatRequest,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
    session: AsyncSession = Depends(get_db_session),
):
    visible_pipeline_ids: set[uuid.UUID] | None = None

    if user.role != "admin":
        user_team_ids = {ut.team_id for ut in user.team_memberships}
        visibility_conditions = await VisibilityFilter.build_batch_visibility_conditions(
            session, user.id, user_team_ids,
        )
        stmt = select(Pipeline.id).where(or_(*visibility_conditions))
        result = await session.execute(stmt)
        visible_pipeline_ids = {row[0] for row in result.all()}

    history = [{"role": m.role, "content": m.content} for m in body.history]
    content = await service.chat(body.message, history, visible_pipeline_ids=visible_pipeline_ids)
    return AIChatResponse(content=content)


@router.get(
    "/pipelines/{pipeline_id}/joins/ai",
    dependencies=[Depends(require_pipeline_visibility())],
)
async def ai_join_insight(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
):
    insight = await service.get_join_insight(pipeline_id)
    return {"insight": insight}
