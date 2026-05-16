"""Pipeline log schemas — DTOs for multi-log data structure management."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LogFieldSchema(BaseModel):
    id: uuid.UUID | None = None
    name: str
    data_type: str | None = None
    ordinal_position: int = 0

    model_config = ConfigDict(from_attributes=True)


class LogNetworkSchema(BaseModel):
    id: uuid.UUID | None = None
    network_id: uuid.UUID
    network_name: str | None = None
    retention: str | None = None

    model_config = ConfigDict(from_attributes=True)


class LogResponse(BaseModel):
    id: uuid.UUID
    pipeline_id: uuid.UUID
    name: str
    ordinal_position: int = 0
    created_at: datetime | None = None
    networks: list[LogNetworkSchema] = []
    fields: list[LogFieldSchema] = []

    model_config = ConfigDict(from_attributes=True)


class LogCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    ordinal_position: int = 0


class LogUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    ordinal_position: int | None = None


class LogNetworkSetRequest(BaseModel):
    """Set networks + retention for a log. Replaces all existing log-network associations."""
    networks: list[LogNetworkSchema]


class LogFieldSetRequest(BaseModel):
    """Set schema fields for a log. Replaces all existing log fields."""
    fields: list[LogFieldSchema]


class LogListResponse(BaseModel):
    items: list[LogResponse]
