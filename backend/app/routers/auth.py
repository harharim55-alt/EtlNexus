"""Auth endpoints — OIDC config discovery and current-user lookup."""

from fastapi import APIRouter, Depends

from app.auth import AuthUser, get_current_user
from app.config import settings
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
        client_secret=settings.sso_client_secret,
        audience=settings.sso_audience,
        ai_greeting=settings.ai_greeting,
        app_name=settings.app_name,
        app_owner=settings.app_owner,
        ai_request_timeout_seconds=settings.ai_request_timeout_seconds,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: AuthUser = Depends(get_current_user)) -> UserResponse:
    """Return the current authenticated user with their Keycloak teams."""
    return user_to_response(user)
