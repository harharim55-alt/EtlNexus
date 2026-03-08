from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import Pipeline, PipelineField


class FieldFrequencyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_field_frequencies(self) -> list[dict]:
        """Get field name frequencies across all pipelines, sorted desc."""
        stmt = (
            select(
                PipelineField.name,
                func.count(PipelineField.pipeline_id.distinct()).label("frequency"),
            )
            .group_by(PipelineField.name)
            .having(func.count(PipelineField.pipeline_id.distinct()) > 1)
            .order_by(func.count(PipelineField.pipeline_id.distinct()).desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        frequencies = []
        for row in rows:
            # Get pipelines that have this field
            pipelines_stmt = (
                select(Pipeline.id, Pipeline.name)
                .join(PipelineField, Pipeline.id == PipelineField.pipeline_id)
                .where(PipelineField.name == row.name)
                .order_by(Pipeline.name)
            )
            pipelines_result = await self.session.execute(pipelines_stmt)
            pipelines = [
                {"pipeline_id": str(p.id), "pipeline_name": p.name}
                for p in pipelines_result.all()
            ]
            frequencies.append(
                {
                    "field_name": row.name,
                    "frequency": row.frequency,
                    "pipelines": pipelines,
                }
            )

        return frequencies
