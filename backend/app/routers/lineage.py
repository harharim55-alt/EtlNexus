import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.dependencies import get_lineage_repo, get_pipeline_repo
from app.models.user import User
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.lineage import LineageGraphSchema, LineageNode, LineageEdgeSchema

router = APIRouter(prefix="/api/pipelines", tags=["lineage"])


@router.get("/{pipeline_id}/lineage", response_model=LineageGraphSchema)
async def get_pipeline_lineage(
    pipeline_id: uuid.UUID,
    user: User = Depends(get_current_user),
    pipeline_repo: PipelineRepository = Depends(get_pipeline_repo),
    lineage_repo: LineageRepository = Depends(get_lineage_repo),
):
    pipeline = await pipeline_repo.get_by_id(pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    lineage = await lineage_repo.get_by_pipeline_id(pipeline_id)
    nodes: list[LineageNode] = []
    edges: list[LineageEdgeSchema] = []
    source_tables: list[str] = []
    destination_tables: list[str] = []

    # Add the pipeline itself as a node
    nodes.append(
        LineageNode(
            table_name=pipeline.name,
            pipeline_id=str(pipeline.id),
            pipeline_name=pipeline.name,
            node_type="pipeline",
        )
    )

    # Source tables (reads_from edges)
    for edge in lineage["reads_from"]:
        source_tables.append(edge.source_table)
        nodes.append(
            LineageNode(
                table_name=edge.source_table,
                pipeline_id=str(edge.source_pipeline_id) if edge.source_pipeline_id else None,
                pipeline_name=edge.source_pipeline.name if edge.source_pipeline else None,
                node_type="source",
            )
        )
        edges.append(
            LineageEdgeSchema(
                source=edge.source_table,
                target=pipeline.name,
                edge_type=edge.edge_type,
            )
        )

    # Destination tables (writes_to edges)
    for edge in lineage["writes_to"]:
        destination_tables.append(edge.target_table)
        nodes.append(
            LineageNode(
                table_name=edge.target_table,
                pipeline_id=str(edge.target_pipeline_id) if edge.target_pipeline_id else None,
                pipeline_name=edge.target_pipeline.name if edge.target_pipeline else None,
                node_type="target",
            )
        )
        edges.append(
            LineageEdgeSchema(
                source=pipeline.name,
                target=edge.target_table,
                edge_type=edge.edge_type,
            )
        )

    return LineageGraphSchema(
        nodes=nodes,
        edges=edges,
        source_tables=sorted(set(source_tables)),
        destination_tables=sorted(set(destination_tables)),
    )
