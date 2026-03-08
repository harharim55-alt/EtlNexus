from datetime import datetime

from pydantic import BaseModel


class PipelineUsageSchema(BaseModel):
    id: str
    consumer_name: str
    usage_type: str  # "etl" or "api"
    description: str | None = None
    last_accessed_at: datetime | None = None
    access_count: int = 0
    airflow_status: str | None = None
    dag_id: str | None = None
    is_current: bool = False

    model_config = {"from_attributes": True}


class PipelineUsageResponse(BaseModel):
    usages: list[PipelineUsageSchema]
