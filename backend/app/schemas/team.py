"""Pydantic schemas for team endpoints."""

import uuid

from pydantic import BaseModel, ConfigDict


class TeamMemberInfo(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    role_in_team: str

    model_config = ConfigDict(from_attributes=True)


class TeamResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    source: str
    member_count: int

    model_config = ConfigDict(from_attributes=True)


class TeamDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    source: str
    members: list[TeamMemberInfo]

    model_config = ConfigDict(from_attributes=True)
