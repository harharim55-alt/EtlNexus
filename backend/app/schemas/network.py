"""Network schemas — request/response DTOs for admin-managed networks."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NetworkResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class NetworkCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None


class NetworkUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None


class NetworkListResponse(BaseModel):
    items: list[NetworkResponse]
