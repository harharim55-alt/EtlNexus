"""Auth endpoints — OIDC config discovery and current-user lookup."""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.config import settings
from app.models.user import User
from app.models.user_team import UserTeam
from app.schemas.auth import AuthConfigResponse, TeamMembershipResponse, UserResponse

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
    """Return the current authenticated user with team memberships.

    Args:
        user: Injected by ``get_current_user`` after JWT validation.

    Returns:
        Full user record including team memberships and per-team roles.
    """
    teams = [
        TeamMembershipResponse(
            id=str(ut.team.id) if ut.team else str(ut.team_id),
            name=ut.team.name if ut.team else "",
            role_in_team=ut.role_in_team,
        )
        for ut in (user.team_memberships or [])
        if isinstance(ut, UserTeam)
    ]
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        teams=teams,
    )
