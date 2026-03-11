"""User management endpoints — admin listing and role updates."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.database import get_db_session
from app.models.user import User
from app.models.user_team import UserTeam
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TeamMembershipResponse, UserResponse

router = APIRouter(prefix="/api/users", tags=["users"])

_VALID_ROLES = frozenset({"admin", "member", "viewer"})


@router.get("", response_model=list[UserResponse])
async def list_users(
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> list[UserResponse]:
    """List all users with team memberships (admin only).

    Args:
        user: Authenticated admin caller.
        session: Async DB session.

    Returns:
        All users ordered by display name, each with their team memberships.
    """
    users = await UserRepository(session).get_all()
    return [_user_to_response(u) for u in users]


@router.patch("/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: uuid.UUID,
    body: dict,
    user: User = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Change a user's global role (admin only).

    The request body must be a JSON object with a ``role`` key whose value
    is one of ``"admin"``, ``"member"``, or ``"viewer"``.

    Args:
        user_id: UUID of the user whose role should be updated.
        body: Request payload — expects ``{"role": "<role>"}``.
        user: Authenticated admin caller.
        session: Async DB session.

    Returns:
        ``{"ok": True}`` on success.

    Raises:
        HTTPException(400): When the supplied role string is not recognised.
        HTTPException(404): When no user with the given ID exists.
    """
    role = body.get("role")
    if role not in _VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role '{role}'. Must be one of: {sorted(_VALID_ROLES)}",
        )

    updated = await UserRepository(session).update_role(user_id, role)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")

    return {"ok": True}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _user_to_response(u: User) -> UserResponse:
    """Convert a User ORM instance to a UserResponse schema.

    Args:
        u: Fully loaded User with team_memberships eagerly loaded.

    Returns:
        Serialisable UserResponse.
    """
    teams = [
        TeamMembershipResponse(
            id=str(ut.team.id) if ut.team else str(ut.team_id),
            name=ut.team.name if ut.team else "",
            role_in_team=ut.role_in_team,
        )
        for ut in (u.team_memberships or [])
        if isinstance(ut, UserTeam)
    ]
    return UserResponse(
        id=str(u.id),
        email=u.email,
        display_name=u.display_name,
        role=u.role,
        teams=teams,
    )
