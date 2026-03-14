"""Pydantic schemas for visibility grant endpoints."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, model_validator


class GrantListResponse(BaseModel):
    items: list["VisibilityGrantResponse"]
    total: int


class VisibilityGrantRequest(BaseModel):
    grantee_team_id: uuid.UUID | None = None
    grantee_user_id: uuid.UUID | None = None
    pipeline_id: uuid.UUID | None = None
    source_team_id: uuid.UUID | None = None
    grant_level: Literal["viewer", "editor"] = "viewer"

    @model_validator(mode="after")
    def validate_xor_fields(self) -> "VisibilityGrantRequest":
        if not self.pipeline_id and not self.source_team_id:
            raise ValueError("Must specify pipeline_id or source_team_id")
        if self.pipeline_id and self.source_team_id:
            raise ValueError("Cannot specify both pipeline_id and source_team_id")
        if not self.grantee_team_id and not self.grantee_user_id:
            raise ValueError("Must specify grantee_team_id or grantee_user_id")
        if self.grantee_team_id and self.grantee_user_id:
            raise ValueError("Cannot specify both grantee_team_id and grantee_user_id")
        return self


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
    granted_by_user_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
