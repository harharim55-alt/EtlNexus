"""Pydantic schemas for visibility grant endpoints."""

from typing import Literal

from pydantic import BaseModel


class VisibilityGrantRequest(BaseModel):
    grantee_team_id: str | None = None
    grantee_user_id: str | None = None
    pipeline_id: str | None = None
    source_team_id: str | None = None
    grant_level: Literal["viewer", "editor"] = "viewer"


class VisibilityGrantResponse(BaseModel):
    id: str
    grantee_team_id: str | None = None
    grantee_team_name: str | None = None
    grantee_user_id: str | None = None
    grantee_user_name: str | None = None
    grantee_user_email: str | None = None
    pipeline_id: str | None = None
    source_team_id: str | None = None
    source_team_name: str | None = None
    grant_level: Literal["viewer", "editor"] = "viewer"
    granted_by: str
    created_at: str

    model_config = {"from_attributes": True}
