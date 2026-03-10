from itertools import groupby

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import Pipeline, PipelineField


class FieldFrequencyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_field_frequencies(self) -> list[dict]:
        """Get field name frequencies across all pipelines, sorted desc.

        Uses a single query with a subquery filter instead of N+1:
        1. Subquery identifies field names appearing in 2+ pipelines
        2. Main query joins fields → pipelines for those names only
        """
        # Subquery: field names that appear in more than one pipeline
        shared_fields = (
            select(PipelineField.name)
            .group_by(PipelineField.name)
            .having(func.count(PipelineField.pipeline_id.distinct()) > 1)
            .scalar_subquery()
        )

        # Single query: get all (field_name, pipeline) pairs for shared fields
        stmt = (
            select(
                PipelineField.name.label("field_name"),
                Pipeline.id.label("pipeline_id"),
                Pipeline.name.label("pipeline_name"),
            )
            .join(Pipeline, Pipeline.id == PipelineField.pipeline_id)
            .where(PipelineField.name.in_(shared_fields))
            .order_by(PipelineField.name, Pipeline.name)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        # Group in Python (rows are already sorted by field_name)
        frequencies = []
        for field_name, group in groupby(rows, key=lambda r: r.field_name):
            pipelines = [
                {"pipeline_id": str(r.pipeline_id), "pipeline_name": r.pipeline_name}
                for r in group
            ]
            frequencies.append(
                {
                    "field_name": field_name,
                    "frequency": len(pipelines),
                    "pipelines": pipelines,
                }
            )

        # Sort by frequency descending
        frequencies.sort(key=lambda f: f["frequency"], reverse=True)
        return frequencies
