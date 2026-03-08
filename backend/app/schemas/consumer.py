from datetime import datetime

from pydantic import BaseModel


class PipelineConsumerSchema(BaseModel):
    pipeline_id: str
    pipeline_name: str
    dag_id: str
    airflow_status: str  # success, failed, running, unknown
    last_run_at: datetime | None = None


class PipelineConsumersResponse(BaseModel):
    consumers: list[PipelineConsumerSchema]
