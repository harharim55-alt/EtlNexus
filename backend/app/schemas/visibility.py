"""Pydantic schemas for visibility grant endpoints."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GrantListResponse(BaseModel):
    items: list["VisibilityGrantResponse"]
    total: int


class VisibilityGrantRequest(BaseModel):
    grantee_team_id: uuid.UUID | None = None
    grantee_user_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    source_team_id: uuid.UUID | None = None
    grant_level: Literal["viewer", "editor"] = "viewer"


class VisibilityGrantResponse(BaseModel):
    id: uuid.UUID
    grantee_team_id: uuid.UUID | None = None
    grantee_team_name: str | None = None
    grantee_user_id: uuid.UUID | None = None
    grantee_user_name: str | None = None
    grantee_user_email: str | None = None
    pipeline_id: uuid.UUID | None = None
    source_team_id: uuid.UUID | None = None
    source_team_name: str | None = None
    grant_level: Literal["viewer", "editor"] = "viewer"
    granted_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
