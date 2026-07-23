"""Pydantic schemas for authentication and user endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.auth import AuthUser


class AuthConfigResponse(BaseModel):
    sso_enabled: bool = Field(description="Whether SSO/OIDC authentication is enabled")
    issuer_url: str = Field(description="OIDC issuer URL for the frontend OIDC client")
    client_id: str = Field(description="OIDC client ID for the SPA")
    client_secret: str = Field(
        default="", description="OIDC client secret (only for a confidential client; empty = public)"
    )
    audience: str = Field(description="Expected OIDC audience claim")
    ai_greeting: str = Field(default="", description="Opening message for the AI Architect chat")
    app_name: str = Field(default="ETL Nexus", description="System name shown on the login page")
    app_owner: str = Field(default="", description="Owner credit ('Made by …') shown on the login page")
    ai_request_timeout_seconds: int = Field(
        default=300, description="Client-side timeout (seconds) for an AI chat request"
    )


class UserResponse(BaseModel):
    username: str = Field(description="Username from SSO claims (stable identifier)")
    full_name: str = Field(default="", description="Human name (first + last) from SSO claims")
    email: str = Field(default="", description="User email address from SSO claims")
    role: str = Field(description="Global role: admin, member, or viewer")
    is_master: bool = Field(default=False, description="Master admin (superuser) — edits all teams")
    teams: list[str] = Field(default=[], description="Team names the user belongs to (from Keycloak)")


def user_to_response(u: AuthUser) -> UserResponse:
    """Convert a transient AuthUser into a UserResponse schema."""
    return UserResponse(
        username=u.username,
        full_name=u.full_name,
        email=u.email,
        role=u.role,
        is_master=u.is_master,
        teams=u.teams,
    )
