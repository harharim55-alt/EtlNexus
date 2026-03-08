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

    model_config = {"from_attributes": True}


class PipelineDetail(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str | None = None
    schedule: str | None = None
    rows_per_day: str | None = None
    code_path: str | None = None
    airflow_status: str = "unknown"
    fields: list[PipelineFieldSchema] = []
    source_tables: list[str] = []
    destination_tables: list[str] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class JoinSuggestion(BaseModel):
    pipeline_id: str
    pipeline_name: str
    shared_fields: list[str]


class JoinSuggestionsResponse(BaseModel):
    schema_matches: list[JoinSuggestion]
