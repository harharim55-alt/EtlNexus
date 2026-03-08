from pydantic import BaseModel


class LineageNode(BaseModel):
    table_name: str
    pipeline_id: str | None = None
    pipeline_name: str | None = None
    node_type: str  # "source" | "target" | "pipeline"


class LineageEdgeSchema(BaseModel):
    source: str
    target: str
    edge_type: str


class LineageGraphSchema(BaseModel):
    nodes: list[LineageNode]
    edges: list[LineageEdgeSchema]
    source_tables: list[str]
    destination_tables: list[str]
