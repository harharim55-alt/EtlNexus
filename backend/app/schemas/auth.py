"""Pydantic schemas for authentication and user endpoints."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from app.models.user import User


class AuthConfigResponse(BaseModel):
    sso_enabled: bool = Field(description="Whether SSO/OIDC authentication is enabled")
    issuer_url: str = Field(description="OIDC issuer URL for the frontend OIDC client")
    client_id: str = Field(description="OIDC client ID for the SPA")
    audience: str = Field(description="Expected OIDC audience claim")


class TeamMembershipResponse(BaseModel):
    id: uuid.UUID = Field(description="Team UUID")
    name: str = Field(description="Team display name")
    role_in_team: str = Field(description="User's role within this team")

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: uuid.UUID = Field(description="User UUID")
    email: str = Field(description="User email address from SSO claims")
    display_name: str = Field(description="User display name from SSO claims")
    role: str = Field(description="Global role: admin, member, or viewer")
    is_active: bool = Field(description="Whether the user account is active")
    teams: list[TeamMembershipResponse] = Field(description="Teams the user belongs to")

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class RoleUpdateRequest(BaseModel):
    role: Literal["admin", "member", "viewer"] = Field(
        description="New role to assign (admin, member, or viewer)"
    )


class ActiveUpdateRequest(BaseModel):
    is_active: bool = Field(description="Whether the user account is active")


def user_to_response(u: User) -> UserResponse:
    """Convert a User ORM instance to a UserResponse schema."""
    from app.models.user_team import UserTeam

    teams = [
        TeamMembershipResponse(
            id=ut.team.id if ut.team else ut.team_id,
            name=ut.team.name if ut.team else "",
            role_in_team=ut.role_in_team,
        )
        for ut in (u.team_memberships or [])
        if isinstance(ut, UserTeam)
    ]
    return UserResponse(
        id=u.id,
        email=u.email,
        display_name=u.display_name,
        role=u.role,
        is_active=u.is_active,
        teams=teams,
    )
