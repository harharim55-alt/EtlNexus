"""Pydantic schemas for team endpoints."""

from pydantic import BaseModel


class TeamMemberInfo(BaseModel):
    id: str
    email: str
    display_name: str
    role: str
    role_in_team: str

    model_config = {"from_attributes": True}


class TeamResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    source: str
    member_count: int

    model_config = {"from_attributes": True}


class TeamDetailResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    source: str
    members: list[TeamMemberInfo]

    model_config = {"from_attributes": True}
