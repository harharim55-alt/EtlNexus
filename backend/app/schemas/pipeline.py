import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.tag import TagResponse


class PipelineFieldSchema(BaseModel):
    id: uuid.UUID
    name: str
    data_type: str | None = None
    ordinal_position: int = 0

    model_config = ConfigDict(from_attributes=True)


class PipelineListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    schedule_type: str | None = None
    team: str | None = None
    tags: list[TagResponse] = []
    is_data_product: bool = False

    model_config = ConfigDict(from_attributes=True)


class PipelineListResponse(BaseModel):
    items: list[PipelineListItem]
    total: int


class PipelineDetail(BaseModel):
    id: uuid.UUID
    name: str
    task_id: str | None = None
    description: str | None = None
    fields: list[PipelineFieldSchema] = []
    documentation: str | None = None
    last_updated_by: str | None = None
    last_updated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    team: str | None = None
    team_id: uuid.UUID | None = None
    can_edit: bool = False
    tags: list[TagResponse] = []
    import_snippet: str | None = None
    schedule_type: str | None = None
    schema_manually_edited: bool = False
    is_data_product: bool = False

    model_config = ConfigDict(from_attributes=True)


class PipelineUpdateRequest(BaseModel):
    description: str | None = Field(None, max_length=270)
    documentation: str | None = Field(None, max_length=100_000)
    import_snippet: str | None = Field(None, max_length=10_000)
    schedule_type: str | None = Field(None, pattern="^(daily|hourly|stream)$")


class PipelineUpdateResponse(BaseModel):
    id: uuid.UUID
    description: str | None = None
    documentation: str | None = None
    last_updated_by: str | None = None
    last_updated_at: datetime | None = None


class PipelineRevisionResponse(BaseModel):
    id: uuid.UUID
    pipeline_id: uuid.UUID
    field_name: str
    content: str | None = None
    changed_by: str
    change_source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RevisionListResponse(BaseModel):
    items: list[PipelineRevisionResponse]
    total: int


class JoinSuggestion(BaseModel):
    pipeline_id: uuid.UUID
    pipeline_name: str
    shared_fields: list[str]


class JoinSuggestionsResponse(BaseModel):
    schema_matches: list[JoinSuggestion]
