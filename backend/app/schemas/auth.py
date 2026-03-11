"""Pydantic schemas for authentication and user endpoints."""

from pydantic import BaseModel


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
