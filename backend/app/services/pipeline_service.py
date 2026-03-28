import uuid
from datetime import datetime

from app.cache import join_suggestions_cache, pipeline_list_cache
from app.models.pipeline import Pipeline
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.revision_repo import RevisionRepository
from app.repositories.visibility_grant_repo import VisibilityGrantRepository
from app.schemas.pipeline import (
    JoinSuggestion,
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListItem,
    PipelineListResponse,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
)


class PipelineService:
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        lineage_repo: LineageRepository,
        revision_repo: RevisionRepository | None = None,
    ):
        self.pipeline_repo = pipeline_repo
        self.lineage_repo = lineage_repo
        self.revision_repo = revision_repo

    async def list_pipelines(
        self,
        query: str | None = None,
        user_id: uuid.UUID | None = None,
        user_team_ids: set[uuid.UUID] | None = None,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 200,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        team_names: list[str] | None = None,
        dag_ids: list[str] | None = None,
        statuses: list[str] | None = None,
    ) -> PipelineListResponse:
        # Build cache key — only cache unfiltered (no search query, no date range, no filters) requests
        cache_key: str | None = None
        if not query and not date_from and not date_to and not team_names and not dag_ids and not statuses:
            if is_admin:
                cache_key = f"all:{skip}:{limit}"
            elif user_team_ids:
                sorted_ids = "|".join(sorted(str(t) for t in user_team_ids))
                cache_key = f"teams:{sorted_ids}:user:{user_id}:{skip}:{limit}"
            elif user_id:
                cache_key = f"user:{user_id}:{skip}:{limit}"

        if cache_key:
            cached = pipeline_list_cache.get(cache_key)
            if cached is not None:
                return cached

        pipelines, total = await self.pipeline_repo.list_visible(
            user_id=user_id,
            user_team_ids=user_team_ids,
            is_admin=is_admin,
            query=query,
            skip=skip,
            limit=limit,
            last_run_after=date_from,
            last_run_before=date_to,
            team_names=team_names,
            dag_ids=dag_ids,
            statuses=statuses,
        )

        items = [self._to_list_item(p) for p in pipelines]
        if pipelines:
            ids = [p.id for p in pipelines]
            rates = await self.pipeline_repo.get_success_rates(
                ids, date_from=date_from, date_to=date_to,
            )
            run_dates = await self.pipeline_repo.get_last_run_dates(ids)
            for item in items:
                item.success_rate = rates.get(item.id)
                item.last_run_at = run_dates.get(item.id)

        result = PipelineListResponse(items=items, total=total)
        if cache_key:
            pipeline_list_cache.set(cache_key, result)
        return result

    async def update_pipeline_metadata(
        self,
        pipeline_id: uuid.UUID,
        update: PipelineUpdateRequest,
        updated_by: str = "System",
        preloaded_pipeline: "Pipeline | None" = None,
        revision_repo: RevisionRepository | None = None,
    ) -> PipelineUpdateResponse | None:
        # Load pipeline to snapshot previous values for revisions
        pipeline = preloaded_pipeline or await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        # Use explicitly passed revision_repo, fall back to injected instance
        effective_revision_repo = revision_repo or self.revision_repo

        # Snapshot previous values before applying changes
        if effective_revision_repo:
            if update.description is not None and update.description != pipeline.description:
                await effective_revision_repo.create(
                    pipeline_id=pipeline_id,
                    field_name="description",
                    content=pipeline.description,
                    changed_by=updated_by,
                    change_source="user",
                )
            if update.documentation is not None and update.documentation != pipeline.documentation:
                await effective_revision_repo.create(
                    pipeline_id=pipeline_id,
                    field_name="documentation",
                    content=pipeline.documentation,
                    changed_by=updated_by,
                    change_source="user",
                )

        pipeline = await self.pipeline_repo.update_metadata(
            pipeline_id,
            description=update.description,
            documentation=update.documentation,
            updated_by=updated_by,
            pipeline=pipeline,
            set_description_edited=(update.description is not None),
        )
        if not pipeline:
            return None
        pipeline_list_cache.clear()
        return PipelineUpdateResponse(
            id=pipeline.id,
            description=pipeline.description,
            documentation=pipeline.documentation,
            last_updated_by=pipeline.last_updated_by,
            last_updated_at=pipeline.last_updated_at,
        )

    async def restore_revision(
        self,
        pipeline_id: uuid.UUID,
        revision_id: uuid.UUID,
        restored_by: str,
        revision_repo: RevisionRepository | None = None,
    ) -> PipelineUpdateResponse | None:
        effective_revision_repo = revision_repo or self.revision_repo
        if not effective_revision_repo:
            return None

        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        revision = await effective_revision_repo.get_by_id(revision_id)
        if not revision or revision.pipeline_id != pipeline_id:
            return None

        # Snapshot current state before restoring
        field_name = revision.field_name
        current_content = getattr(pipeline, field_name)
        await effective_revision_repo.create(
            pipeline_id=pipeline_id,
            field_name=field_name,
            content=current_content,
            changed_by=restored_by,
            change_source="restore",
        )

        # Apply the restored content
        kwargs = {field_name: revision.content}
        pipeline = await self.pipeline_repo.update_metadata(
            pipeline_id,
            **kwargs,
            updated_by=restored_by,
            pipeline=pipeline,
            set_description_edited=(field_name == "description"),
        )
        if not pipeline:
            return None
        pipeline_list_cache.clear()
        return PipelineUpdateResponse(
            id=pipeline.id,
            description=pipeline.description,
            documentation=pipeline.documentation,
            last_updated_by=pipeline.last_updated_by,
            last_updated_at=pipeline.last_updated_at,
        )

    async def get_pipeline_detail(self, pipeline_id: uuid.UUID) -> PipelineDetail | None:
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        lineage = await self.lineage_repo.get_by_pipeline_id(pipeline_id)
        source_tables = list({e.source_table for e in lineage["reads_from"]})
        destination_tables = list({e.target_table for e in lineage["writes_to"]})

        return PipelineDetail(
            id=pipeline.id,
            name=pipeline.name,
            task_id=pipeline.task_id,
            description=pipeline.description,
            category=pipeline.category,
            pipeline_type=self._detect_pipeline_type(pipeline.task_id),
            schedule=pipeline.schedule,
            rows_per_day=pipeline.rows_per_day,
            airflow_status=(
                pipeline.airflow_status.status if pipeline.airflow_status else "unknown"
            ),
            fields=[
                {
                    "id": f.id,
                    "name": f.name,
                    "data_type": f.data_type,
                    "ordinal_position": f.ordinal_position,
                }
                for f in pipeline.fields
            ],
            source_tables=sorted(source_tables),
            destination_tables=sorted(destination_tables),
            documentation=pipeline.documentation,
            last_updated_by=pipeline.last_updated_by,
            last_updated_at=pipeline.last_updated_at,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at,
            team=pipeline.team,
            team_id=pipeline.team_id,
            execution_date=(
                pipeline.airflow_status.execution_date
                if pipeline.airflow_status
                else None
            ),
            last_checked_at=(
                pipeline.airflow_status.last_checked_at
                if pipeline.airflow_status
                else None
            ),
        )

    async def get_pipeline_detail_for_user(
        self,
        pipeline_id: uuid.UUID,
        user_id: uuid.UUID,
        user_team_ids: set[uuid.UUID],
        is_admin: bool,
        grant_repo: VisibilityGrantRepository,
    ) -> PipelineDetail | None:
        """Fetch pipeline detail with visibility enforcement and can_edit computation.

        Returns None (callers should raise 404) if:
        - Pipeline does not exist
        - Non-admin user lacks visibility to the pipeline
        """
        result = await self.get_pipeline_detail(pipeline_id)
        if not result:
            return None

        if is_admin:
            result.can_edit = True
            return result

        if not result.team_id:
            result.can_edit = True
            return result

        pipeline_team_id = result.team_id

        # Enforce visibility — return None to prevent UUID enumeration
        can_see = await grant_repo.user_can_see_pipeline(
            pipeline_id=pipeline_id,
            pipeline_team_id=pipeline_team_id,
            user_id=user_id,
            user_team_ids=user_team_ids,
        )
        if not can_see:
            return None

        if pipeline_team_id in user_team_ids:
            result.can_edit = True
        else:
            grant_level = await grant_repo.get_grant_level_for_pipeline(
                pipeline_id=pipeline_id,
                user_id=user_id,
                user_team_ids=user_team_ids,
                pipeline_team_id=pipeline_team_id,
            )
            result.can_edit = grant_level == "editor"

        return result

    async def get_join_suggestions(
        self,
        pipeline_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        user_team_ids: set[uuid.UUID] | None = None,
        is_admin: bool = False,
        grant_repo: VisibilityGrantRepository | None = None,
    ) -> JoinSuggestionsResponse | None:
        """Return schema-based join suggestions for the given pipeline.

        When ``grant_repo`` is provided and the caller is not an admin, the
        pipeline visibility is enforced before returning results.

        Args:
            pipeline_id: UUID of the pipeline to fetch join suggestions for.
            user_id: ID of the requesting user (used for visibility checks).
            user_team_ids: Set of team IDs the user belongs to.
            is_admin: When ``True``, bypass all visibility checks.
            grant_repo: Repository used for visibility enforcement.

        Returns:
            ``JoinSuggestionsResponse`` when the pipeline is visible and found,
            ``None`` otherwise (callers should raise 404).
        """
        cache_key = f"{pipeline_id}:{user_id}:{is_admin}"
        cached = join_suggestions_cache.get(cache_key)
        if cached is not None:
            return cached

        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        if not is_admin and grant_repo is not None:
            can_see = await grant_repo.user_can_see_pipeline(
                pipeline_id=pipeline_id,
                pipeline_team_id=pipeline.team_id,
                user_id=user_id,
                user_team_ids=user_team_ids or set(),
            )
            if not can_see:
                return None

        # Use SQL-based field intersection instead of loading all pipelines into memory
        rows = await self.pipeline_repo.get_shared_field_pipelines(pipeline_id)
        suggestions = [
            JoinSuggestion(
                pipeline_id=row["pipeline_id"],
                pipeline_name=row["pipeline_name"],
                shared_fields=row["shared_fields"],
            )
            for row in rows
        ]

        result = JoinSuggestionsResponse(schema_matches=suggestions)
        join_suggestions_cache.set(cache_key, result)
        return result

    @staticmethod
    def _detect_pipeline_type(task_id: str | None) -> str:
        """Derive pipeline type from task_id (same logic as AirflowSyncService._is_api)."""
        if task_id and ("Api" in task_id or "API" in task_id):
            return "api"
        return "etl"

    @staticmethod
    def _to_list_item(pipeline: Pipeline) -> PipelineListItem:
        return PipelineListItem(
            id=pipeline.id,
            name=pipeline.name,
            description=pipeline.description,
            category=pipeline.category,
            pipeline_type=PipelineService._detect_pipeline_type(pipeline.task_id),
            schedule=pipeline.schedule,
            rows_per_day=pipeline.rows_per_day,
            airflow_status=(
                pipeline.airflow_status.status if pipeline.airflow_status else "unknown"
            ),
            team=pipeline.team,
            execution_date=(
                pipeline.airflow_status.execution_date
                if pipeline.airflow_status
                else None
            ),
        )
