"""Pydantic schemas for authentication and user endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.models.user import User

class AuthConfigResponse(BaseModel):
    sso_enabled: bool
    issuer_url: str
    client_id: str
    audience: str


class TeamMembershipResponse(BaseModel):
    id: str
    name: str
    role_in_team: str

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    teams: list[TeamMembershipResponse]

    model_config = {"from_attributes": True}


class RoleUpdateRequest(BaseModel):
    role: Literal["admin", "member", "viewer"]


def user_to_response(u: User) -> UserResponse:
    """Convert a User ORM instance to a UserResponse schema."""
    from app.models.user_team import UserTeam

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
