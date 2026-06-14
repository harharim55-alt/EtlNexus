"""AI architect endpoint — chat and join insights."""

import uuid

from fastapi import APIRouter, Depends, Request

from app.auth import get_current_user, require_pipeline_visibility
from app.dependencies import get_ai_service
from app.models.user import User
from app.rate_limit import limiter
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
):
    # All products are visible to every user, so the AI sees the full catalog.
    history = [{"role": m.role, "content": m.content} for m in body.history]
    content = await service.chat(body.message, history, visible_pipeline_ids=None)
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
