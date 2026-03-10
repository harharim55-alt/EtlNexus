from datetime import datetime

from pydantic import BaseModel


class PipelineFieldSchema(BaseModel):
    id: str
    name: str
    data_type: str | None = None
    ordinal_position: int = 0

    model_config = {"from_attributes": True}


class PipelineListItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str | None = None
    schedule: str | None = None
    rows_per_day: str | None = None
    airflow_status: str = "unknown"
    success_rate: float | None = None

    model_config = {"from_attributes": True}


class PipelineDetail(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str | None = None
    schedule: str | None = None
    rows_per_day: str | None = None
    airflow_status: str = "unknown"
    fields: list[PipelineFieldSchema] = []
    source_tables: list[str] = []
    destination_tables: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class SyncResponse(BaseModel):
    synced: bool
    pipeline_name: str


class JoinSuggestion(BaseModel):
    pipeline_id: str
    pipeline_name: str
    shared_fields: list[str]


class JoinSuggestionsResponse(BaseModel):
    schema_matches: list[JoinSuggestion]
