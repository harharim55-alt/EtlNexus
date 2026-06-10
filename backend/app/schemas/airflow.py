from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AirflowStatusSchema(BaseModel):
    pipeline_id: str
    dag_id: str
    status: str
    execution_date: datetime | None = None
    last_checked_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AirflowStatusesResponse(BaseModel):
    statuses: list[AirflowStatusSchema]
    airflow_connected: bool = True
