"""Auth endpoints — OIDC config discovery and current-user lookup."""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.config import settings
from app.models.user import User
from app.schemas.auth import AuthConfigResponse, UserResponse, user_to_response

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/config", response_model=AuthConfigResponse)
async def get_auth_config() -> AuthConfigResponse:
    """Return OIDC configuration for the frontend.

    This endpoint is intentionally public — it must not carry an auth
    dependency so the frontend can call it before a user is logged in.
    """
    return AuthConfigResponse(
        sso_enabled=settings.sso_enabled,
        issuer_url=settings.sso_public_issuer_url,
        client_id=settings.sso_client_id,
        audience=settings.sso_audience,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the current authenticated user with team memberships."""
    return user_to_response(user)
