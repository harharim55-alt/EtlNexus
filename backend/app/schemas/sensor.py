"""Pydantic schemas for sensor endpoints."""

from pydantic import BaseModel


class SensorResponse(BaseModel):
    id: str
    sensor_name: str
    display_name: str
    description: str | None = None
    team: str | None = None
    volume_per_day: int | None = None
    status: str | None = None
    dag_ids: list[str] = []

    model_config = {"from_attributes": True}


class SensorListResponse(BaseModel):
    sensors: list[SensorResponse]
    teams: list[str]


class SensorTopologyNode(BaseModel):
    task_id: str
    pipeline_name: str | None = None
    pipeline_id: str | None = None
    status: str
    dag_id: str
    depends_on_sensors: list[str] = []


class SensorTopologyResponse(BaseModel):
    selected_sensors: list[str]
    downstream_etls: list[SensorTopologyNode]
    total_etl_count: int
