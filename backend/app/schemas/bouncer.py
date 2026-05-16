"""Pydantic schemas for bouncer endpoints."""

from pydantic import BaseModel, ConfigDict


class BouncerResponse(BaseModel):
    id: str
    bouncer_name: str
    display_name: str
    description: str | None = None
    team: str | None = None
    team_id: str | None = None
    volume_per_day: int | None = None
    status: str | None = None
    dag_ids: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class BouncerUpdateRequest(BaseModel):
    team_id: str | None = None


class BouncerListResponse(BaseModel):
    bouncers: list[BouncerResponse]
    teams: list[str]


class BouncerTopologyNode(BaseModel):
    task_id: str
    pipeline_name: str | None = None
    pipeline_id: str | None = None
    status: str
    dag_id: str
    depends_on_bouncers: list[str] = []


class BouncerTopologyResponse(BaseModel):
    selected_bouncers: list[str]
    downstream_etls: list[BouncerTopologyNode]
    total_etl_count: int
