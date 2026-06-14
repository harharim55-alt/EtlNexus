import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError

from app.cache import join_suggestions_cache, pipeline_list_cache
from app.models.pipeline import Pipeline
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.revision_repo import RevisionRepository
from app.schemas.pipeline import (
    JoinSuggestion,
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListItem,
    PipelineListResponse,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
)

RESTORABLE_FIELDS = frozenset({"description", "documentation"})


class DuplicateProductNameError(Exception):
    """Raised when a data product / tag name collides with an existing one."""

    def __init__(self, name: str):
        self.name = name
        super().__init__(f"A data product named '{name}' already exists.")


class PipelineService:
    def __init__(
        self,
        pipeline_repo: PipelineRepository,
        revision_repo: RevisionRepository | None = None,
    ):
        self.pipeline_repo = pipeline_repo
        self.revision_repo = revision_repo

    async def list_pipelines(
        self,
        query: str | None = None,
        user_id: uuid.UUID | None = None,
        user_team_ids: set[uuid.UUID] | None = None,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 200,
        team_names: list[str] | None = None,
        schedule_types: list[str] | None = None,
        is_data_product: bool | None = None,
        is_tag: bool | None = None,
    ) -> PipelineListResponse:
        # Cache only unfiltered requests
        cache_key: str | None = None
        has_filters = (
            query or team_names or schedule_types
            or is_data_product is not None or is_tag is not None
        )
        if not has_filters:
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
            team_names=team_names,
            schedule_types=schedule_types,
            is_data_product=is_data_product,
            is_tag=is_tag,
        )

        items = [self._to_list_item(p) for p in pipelines]
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
        pipeline = preloaded_pipeline or await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        effective_revision_repo = revision_repo or self.revision_repo

        # Snapshot previous values before applying changes
        if effective_revision_repo:
            if "description" in update.model_fields_set and update.description != pipeline.description:
                await effective_revision_repo.create(
                    pipeline_id=pipeline_id,
                    field_name="description",
                    content=pipeline.description,
                    changed_by=updated_by,
                    change_source="user",
                )
            if "documentation" in update.model_fields_set and update.documentation != pipeline.documentation:
                await effective_revision_repo.create(
                    pipeline_id=pipeline_id,
                    field_name="documentation",
                    content=pipeline.documentation,
                    changed_by=updated_by,
                    change_source="user",
                )

        # Only forward fields the client explicitly included in the request
        repo_kwargs: dict = {}
        for field_name in ("description", "documentation", "import_snippet", "schedule_type"):
            if field_name in update.model_fields_set:
                repo_kwargs[field_name] = getattr(update, field_name)

        pipeline = await self.pipeline_repo.update_metadata(
            pipeline_id,
            **repo_kwargs,
            updated_by=updated_by,
            pipeline=pipeline,
            set_description_edited=("description" in update.model_fields_set),
        )
        if not pipeline:
            return None
        await self.pipeline_repo.session.commit()
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

        if revision.field_name not in RESTORABLE_FIELDS:
            return None

        field_name = revision.field_name
        current_content = getattr(pipeline, field_name)
        await effective_revision_repo.create(
            pipeline_id=pipeline_id,
            field_name=field_name,
            content=current_content,
            changed_by=restored_by,
            change_source="restore",
        )

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
        await self.pipeline_repo.session.commit()
        pipeline_list_cache.clear()
        return PipelineUpdateResponse(
            id=pipeline.id,
            description=pipeline.description,
            documentation=pipeline.documentation,
            last_updated_by=pipeline.last_updated_by,
            last_updated_at=pipeline.last_updated_at,
        )

    async def get_pipeline_detail(self, pipeline_id: uuid.UUID) -> PipelineDetail | None:
        from app.schemas.tag import TagResponse

        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        tag_pipelines = await self.pipeline_repo.tags_for_product(pipeline.id)
        tags = [TagResponse.model_validate(t) for t in tag_pipelines]

        return PipelineDetail(
            id=pipeline.id,
            name=pipeline.name,
            task_id=pipeline.task_id,
            description=pipeline.description,
            fields=[
                {
                    "id": f.id,
                    "name": f.name,
                    "data_type": f.data_type,
                    "ordinal_position": f.ordinal_position,
                }
                for f in pipeline.fields
            ],
            documentation=pipeline.documentation,
            last_updated_by=pipeline.last_updated_by,
            last_updated_at=pipeline.last_updated_at,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at,
            team=pipeline.team,
            team_id=pipeline.team_id,
            tags=tags,
            import_snippet=pipeline.import_snippet,
            schedule_type=pipeline.schedule_type,
            schema_manually_edited=pipeline.schema_manually_edited,
            is_data_product=pipeline.is_data_product,
            is_tag=pipeline.is_tag,
        )

    async def get_pipeline_detail_for_user(
        self,
        pipeline_id: uuid.UUID,
        user_id: uuid.UUID,
        user_team_ids: set[uuid.UUID],
        user_role: str,
        is_master: bool = False,
    ) -> PipelineDetail | None:
        """Fetch pipeline detail. Every authenticated user may view any product.

        ``can_edit`` is True for master admins (any product), and otherwise for
        non-viewer members of the owning team (team-leader admins included, but
        only for their own team).
        """
        result = await self.get_pipeline_detail(pipeline_id)
        if not result:
            return None

        result.can_edit = is_master or (
            user_role != "viewer" and (not result.team_id or result.team_id in user_team_ids)
        )
        return result

    async def get_join_suggestions(
        self,
        pipeline_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        user_team_ids: set[uuid.UUID] | None = None,
        is_admin: bool = False,
    ) -> JoinSuggestionsResponse | None:
        """Return schema-based join suggestions (pipelines sharing field names)."""
        cache_key = f"{pipeline_id}:{user_id}:{is_admin}"
        cached = join_suggestions_cache.get(cache_key)
        if cached is not None:
            return cached

        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None

        # Every authenticated user may view any product (and its join matches).
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

    async def set_manual_fields(
        self,
        pipeline_id: uuid.UUID,
        fields: list,
        updated_by: str = "System",
    ) -> bool:
        """Manually set pipeline fields, marking the schema as manually edited."""
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return False

        from app.models.pipeline import PipelineField

        for f in list(pipeline.fields):
            await self.pipeline_repo.session.delete(f)

        for i, field_data in enumerate(fields):
            name = field_data.name if hasattr(field_data, "name") else field_data["name"]
            data_type = field_data.data_type if hasattr(field_data, "data_type") else field_data.get("data_type")
            new_field = PipelineField(
                pipeline_id=pipeline_id,
                name=name,
                data_type=data_type,
                ordinal_position=i,
            )
            self.pipeline_repo.session.add(new_field)

        pipeline.schema_manually_edited = True
        pipeline.last_updated_by = updated_by
        pipeline.last_updated_at = datetime.now(UTC)
        await self.pipeline_repo.session.flush()
        await self.pipeline_repo.session.commit()
        pipeline_list_cache.clear()
        return True

    async def create_data_product(
        self,
        name: str,
        description: str | None = None,
        documentation: str | None = None,
        team_id: uuid.UUID | None = None,
        schedule_type: str | None = None,
        created_by: str = "System",
        is_tag: bool = False,
    ) -> PipelineDetail:
        """Create a new data product, or a tag (is_tag=True).

        For a product, ``task_id`` is set to the name so the Spark Connect catalog
        mirror auto-fills its schema. A tag has no schema: ``task_id`` stays None
        (no catalog match), it gets a read_by_tag consume snippet, and a detail
        page of its tagged sub-products.
        """
        team_name = None
        if team_id:
            from app.models.team import Team
            team = await self.pipeline_repo.session.get(Team, team_id)
            if team:
                team_name = team.name

        pipeline = Pipeline(
            name=name,
            task_id=None if is_tag else name,
            description=description,
            documentation=documentation,
            team=team_name,
            team_id=team_id,
            schedule_type=None if is_tag else schedule_type,
            is_data_product=True,
            is_tag=is_tag,
            last_updated_by=created_by,
            last_updated_at=datetime.now(UTC),
        )
        self.pipeline_repo.session.add(pipeline)
        try:
            await self.pipeline_repo.session.flush()
            await self.pipeline_repo.session.commit()
        except IntegrityError as exc:
            await self.pipeline_repo.session.rollback()
            raise DuplicateProductNameError(name) from exc
        pipeline_list_cache.clear()
        return await self.get_pipeline_detail(pipeline.id)

    async def promote_to_data_product(
        self,
        pipeline_id: uuid.UUID,
        promoted_by: str = "System",
    ) -> PipelineDetail | None:
        """Promote an existing pipeline to a data product."""
        pipeline = await self.pipeline_repo.get_by_id(pipeline_id)
        if not pipeline:
            return None
        pipeline.is_data_product = True
        pipeline.last_updated_by = promoted_by
        pipeline.last_updated_at = datetime.now(UTC)
        await self.pipeline_repo.session.flush()
        await self.pipeline_repo.session.commit()
        pipeline_list_cache.clear()
        return await self.get_pipeline_detail(pipeline_id)

    @staticmethod
    def _to_list_item(pipeline: Pipeline) -> PipelineListItem:
        return PipelineListItem(
            id=pipeline.id,
            name=pipeline.name,
            description=pipeline.description,
            schedule_type=pipeline.schedule_type,
            team=pipeline.team,
            is_data_product=pipeline.is_data_product,
            is_tag=pipeline.is_tag,
        )
