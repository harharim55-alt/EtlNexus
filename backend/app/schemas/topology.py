from pydantic import BaseModel


class TopologyTask(BaseModel):
    task_id: str
    pipeline_name: str | None = None
    pipeline_id: str | None = None
    status: str  # "success" | "failed" | "running" | "unknown"
    dag_id: str


class TopologyGraph(BaseModel):
    pipeline_task_id: str
    pipeline_status: str
    dag_ids: list[str]
    upstream_needs: list[TopologyTask]
    upstream_prefers: list[TopologyTask]
    downstream: list[TopologyTask]
