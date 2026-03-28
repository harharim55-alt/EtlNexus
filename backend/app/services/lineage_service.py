"""Lineage service — assembles pipeline lineage graphs from repository data."""

import uuid

from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.lineage import LineageEdgeSchema, LineageGraphSchema, LineageNode


class LineageService:
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        lineage_repo: LineageRepository,
    ):
        self.pipeline_repo = pipeline_repo
        self.lineage_repo = lineage_repo

    async def build_lineage_graph(
        self, pipeline_id: uuid.UUID,
    ) -> LineageGraphSchema | None:
        """Assemble the lineage graph for a pipeline.

        Loads the pipeline record and its associated lineage edges, then
        builds a graph of source / destination table nodes connected to the
        central pipeline node.

        Args:
            pipeline_id: UUID of the pipeline to build the graph for.

        Returns:
            A populated :class:`LineageGraphSchema`, or ``None`` when the
            pipeline does not exist.
        """
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        lineage = await self.lineage_repo.get_by_pipeline_id(pipeline_id)
        nodes: list[LineageNode] = []
        edges: list[LineageEdgeSchema] = []
        source_tables: list[str] = []
        destination_tables: list[str] = []

        # Add the pipeline itself as the central node
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
