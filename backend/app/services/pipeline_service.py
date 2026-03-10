import uuid

from app.cache import pipeline_list_cache
from app.models.pipeline import Pipeline
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.schemas.pipeline import (
    JoinSuggestion,
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListItem,
)


class PipelineService:
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        lineage_repo: LineageRepository,
    ):
        self.pipeline_repo = pipeline_repo
        self.lineage_repo = lineage_repo

    async def list_pipelines(self, query: str | None = None) -> list[PipelineListItem]:
        if not query:
            cached = pipeline_list_cache.get("all")
            if cached is not None:
                return cached

        if query:
            pipelines = await self.pipeline_repo.search(query)
        else:
            pipelines = await self.pipeline_repo.get_all()

        items = [self._to_list_item(p) for p in pipelines]
        if pipelines:
            ids = [p.id for p in pipelines]
            rates = await self.pipeline_repo.get_success_rates(ids)
            for item in items:
                item.success_rate = rates.get(uuid.UUID(item.id))

        if not query:
            pipeline_list_cache.set("all", items)
        return items

    async def get_pipeline_detail(self, pipeline_id: uuid.UUID) -> PipelineDetail | None:
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        lineage = await self.lineage_repo.get_by_pipeline_id(pipeline_id)
        source_tables = list({e.source_table for e in lineage["reads_from"]})
        destination_tables = list({e.target_table for e in lineage["writes_to"]})

        return PipelineDetail(
            id=str(pipeline.id),
            name=pipeline.name,
            description=pipeline.description,
            category=pipeline.category,
            schedule=pipeline.schedule,
            rows_per_day=pipeline.rows_per_day,
            airflow_status=(
                pipeline.airflow_status.status if pipeline.airflow_status else "unknown"
            ),
            fields=[
                {
                    "id": str(f.id),
                    "name": f.name,
                    "data_type": f.data_type,
                    "ordinal_position": f.ordinal_position,
                }
                for f in pipeline.fields
            ],
            source_tables=sorted(source_tables),
            destination_tables=sorted(destination_tables),
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at,
        )

    async def get_join_suggestions(
        self, pipeline_id: uuid.UUID
    ) -> JoinSuggestionsResponse | None:
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        pipeline_field_names = {f.name for f in pipeline.fields}
        all_pipelines = await self.pipeline_repo.get_all_with_fields()

        suggestions = []
        for other in all_pipelines:
            if other.id == pipeline_id:
                continue
            other_field_names = {f.name for f in other.fields}
            shared = pipeline_field_names & other_field_names
            if shared:
                suggestions.append(
                    JoinSuggestion(
                        pipeline_id=str(other.id),
                        pipeline_name=other.name,
                        shared_fields=sorted(shared),
                    )
                )

        # Sort by number of shared fields descending
        suggestions.sort(key=lambda s: len(s.shared_fields), reverse=True)
        return JoinSuggestionsResponse(schema_matches=suggestions)

    @staticmethod
    def _to_list_item(pipeline: Pipeline) -> PipelineListItem:
        return PipelineListItem(
            id=str(pipeline.id),
            name=pipeline.name,
            description=pipeline.description,
            category=pipeline.category,
            schedule=pipeline.schedule,
            rows_per_day=pipeline.rows_per_day,
            airflow_status=(
                pipeline.airflow_status.status if pipeline.airflow_status else "unknown"
            ),
        )
