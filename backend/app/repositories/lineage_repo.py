import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lineage import LineageEdge


class LineageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_pipeline_id(self, pipeline_id: uuid.UUID) -> dict:
        """Get all lineage edges where this pipeline is source or target."""
        # Edges where this pipeline reads from (is the target)
        reads_stmt = (
            select(LineageEdge)
            .options(selectinload(LineageEdge.source_pipeline))
            .where(LineageEdge.target_pipeline_id == pipeline_id)
        )
        reads_result = await self.session.execute(reads_stmt)
        reads_from = list(reads_result.scalars().all())

        # Edges where this pipeline writes to (is the source)
        writes_stmt = (
            select(LineageEdge)
            .options(selectinload(LineageEdge.target_pipeline))
            .where(LineageEdge.source_pipeline_id == pipeline_id)
        )
        writes_result = await self.session.execute(writes_stmt)
        writes_to = list(writes_result.scalars().all())

        return {"reads_from": reads_from, "writes_to": writes_to}

    async def get_downstream_pipelines(self, pipeline_id: uuid.UUID) -> list[LineageEdge]:
        """Get lineage edges where this pipeline is the source (downstream consumers)."""
        stmt = (
            select(LineageEdge)
            .options(selectinload(LineageEdge.target_pipeline))
            .where(LineageEdge.source_pipeline_id == pipeline_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_edge(self, data: dict) -> LineageEdge:
        stmt = select(LineageEdge).where(
            LineageEdge.source_table == data["source_table"],
            LineageEdge.target_table == data["target_table"],
            LineageEdge.edge_type == data["edge_type"],
        )
        result = await self.session.execute(stmt)
        edge = result.scalar_one_or_none()

        if edge:
            for key, value in data.items():
                if hasattr(edge, key):
                    setattr(edge, key, value)
        else:
            edge = LineageEdge(**data)
            self.session.add(edge)

        await self.session.flush()
        return edge

    async def delete_by_pipeline_id(self, pipeline_id: uuid.UUID) -> None:
        await self.session.execute(
            delete(LineageEdge).where(
                (LineageEdge.source_pipeline_id == pipeline_id)
                | (LineageEdge.target_pipeline_id == pipeline_id)
            )
        )
