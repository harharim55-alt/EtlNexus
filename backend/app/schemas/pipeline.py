import uuid
from datetime import datetime

from pydantic import BaseModel


class PipelineFieldSchema(BaseModel):
    id: uuid.UUID
    name: str
    data_type: str | None = None
    ordinal_position: int = 0

    model_config = {"from_attributes": True}


class PipelineListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    category: str | None = None
    pipeline_type: str = "etl"
    schedule: str | None = None
    rows_per_day: str | None = None
    airflow_status: str = "unknown"
    success_rate: float | None = None
    team: str | None = None
    last_run_at: datetime | None = None
    execution_date: datetime | None = None

    model_config = {"from_attributes": True}


class PipelineListResponse(BaseModel):
    items: list[PipelineListItem]
    total: int


class PipelineDetail(BaseModel):
    id: uuid.UUID
    name: str
    task_id: str | None = None
    description: str | None = None
    category: str | None = None
    pipeline_type: str = "etl"
    schedule: str | None = None
    rows_per_day: str | None = None
    airflow_status: str = "unknown"
    fields: list[PipelineFieldSchema] = []
    source_tables: list[str] = []
    destination_tables: list[str] = []
    documentation: str | None = None
    last_updated_by: str | None = None
    last_updated_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    team: str | None = None
    team_id: uuid.UUID | None = None
    can_edit: bool = False
    execution_date: datetime | None = None
    last_checked_at: datetime | None = None

    model_config = {"from_attributes": True}


class PipelineUpdateRequest(BaseModel):
    description: str | None = None
    documentation: str | None = None


class PipelineUpdateResponse(BaseModel):
    id: uuid.UUID
    description: str | None = None
    documentation: str | None = None
    last_updated_by: str | None = None
    last_updated_at: datetime | None = None


class SyncResponse(BaseModel):
    synced: bool
    pipeline_name: str


class PipelineRevisionResponse(BaseModel):
    id: uuid.UUID
    pipeline_id: uuid.UUID
    field_name: str
    content: str | None = None
    changed_by: str
    change_source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RevisionListResponse(BaseModel):
    items: list[PipelineRevisionResponse]
    total: int


class JoinSuggestion(BaseModel):
    pipeline_id: uuid.UUID
    pipeline_name: str
    shared_fields: list[str]


class JoinSuggestionsResponse(BaseModel):
    schema_matches: list[JoinSuggestion]
