"""Tag schemas — request/response DTOs for tag management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TagResponse(BaseModel):
    id: uuid.UUID
    name: str
    created_by_team_id: uuid.UUID | None = None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TagCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class PipelineTagsRequest(BaseModel):
    tag_ids: list[uuid.UUID]


class TagListResponse(BaseModel):
    items: list[TagResponse]
