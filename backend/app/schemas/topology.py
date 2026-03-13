from pydantic import BaseModel


class TopologyTask(BaseModel):
    task_id: str
    pipeline_name: str | None = None
    pipeline_id: str | None = None
    status: str  # "success" | "failed" | "running" | "unknown"
    dag_id: str
    task_group_id: str | None = None


class TopologyBouncer(BaseModel):
    sensor_name: str
    display_name: str
    sensor_id: str | None = None
    status: str | None = None
    team: str | None = None
    volume_per_day: int | None = None
    dag_ids: list[str] = []


class TopologyGraph(BaseModel):
    pipeline_task_id: str
    pipeline_status: str
    dag_ids: list[str]
    upstream_bouncers: list[TopologyBouncer] = []
    upstream_needs: list[TopologyTask]
    upstream_prefers: list[TopologyTask]
    downstream: list[TopologyTask]


class UpstreamNode(BaseModel):
    task_id: str
    pipeline_name: str | None = None
    pipeline_id: str | None = None
    status: str
    dag_id: str
    task_group_id: str | None = None
    depth: int
    is_current: bool = False
    is_bouncer: bool = False
    bouncer_name: str | None = None


class UpstreamEdge(BaseModel):
    source_task_id: str
    target_task_id: str
    edge_type: str  # "needs" | "prefers"


class UpstreamTopologyGraph(BaseModel):
    pipeline_task_id: str
    pipeline_status: str
    dag_id: str | None
    dag_ids: list[str] = []
    nodes: list[UpstreamNode]
    edges: list[UpstreamEdge]
    bouncers: list[TopologyBouncer] = []
    max_depth: int
