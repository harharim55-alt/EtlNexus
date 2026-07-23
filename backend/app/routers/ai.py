"""AI architect endpoint — chat with data-product catalog context."""

from fastapi import APIRouter, Depends, Request

from app.auth import AuthUser, get_current_user
from app.config import settings
from app.dependencies import get_ai_service
from app.rate_limit import limiter
from app.schemas.ai import AIChatRequest, AIChatResponse
from app.services.ai_service import AIService

router = APIRouter(prefix="/api", tags=["ai"])


@router.post("/ai/chat", response_model=AIChatResponse)
@limiter.limit(settings.rate_limit_ai)
async def ai_chat(
    request: Request,
    body: AIChatRequest,
    user: AuthUser = Depends(get_current_user),
    service: AIService = Depends(get_ai_service),
):
    # All data products are visible to every user, so the AI sees the full catalog.
    history = [{"role": m.role, "content": m.content} for m in body.history]
    content = await service.chat(body.message, history)
    return AIChatResponse(content=content)
