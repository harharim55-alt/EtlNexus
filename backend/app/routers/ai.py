"""AI architect endpoint — chat and join insights."""

import uuid

from fastapi import APIRouter, Depends

from app.dependencies import get_ai_service
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/ai/chat", response_model=AIChatResponse)
async def ai_chat(
    request: AIChatRequest,
    service: AIService = Depends(get_ai_service),
):
    history = [{"role": m.role, "content": m.content} for m in request.history]
    content = await service.chat(request.message, history)
    return AIChatResponse(content=content)


@router.get("/pipelines/{pipeline_id}/joins/ai")
async def ai_join_insight(
    pipeline_id: uuid.UUID,
    service: AIService = Depends(get_ai_service),
):
    insight = await service.get_join_insight(pipeline_id)
    return {"insight": insight}
