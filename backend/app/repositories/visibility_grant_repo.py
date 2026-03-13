"""Visibility grant repository — async SQLAlchemy data access for visibility grants."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cache import grant_level_cache
from app.models.visibility_grant import VisibilityGrant


def _build_grant_conditions(
    pipeline_id: uuid.UUID,
    user_id: uuid.UUID,
    user_team_ids: set[uuid.UUID],
    pipeline_team_id: uuid.UUID | None,
):
    """Build OR-able SQLAlchemy conditions matching any grant that covers a pipeline.

    Returns a list of BinaryExpression clauses covering:
    - Direct pipeline grants to the user
    - Direct pipeline grants to user's teams
    - Source-team grants to the user
    - Source-team grants to user's teams
    """
    conditions = []

    # Direct pipeline grants → user
    conditions.append(
        (VisibilityGrant.grantee_user_id == user_id)
        & (VisibilityGrant.pipeline_id == pipeline_id)
    )

    # Direct pipeline grants → user's teams
    if user_team_ids:
        conditions.append(
            VisibilityGrant.grantee_team_id.in_(user_team_ids)
            & (VisibilityGrant.pipeline_id == pipeline_id)
        )

    # Source-team grants → user
    if pipeline_team_id:
        conditions.append(
            (VisibilityGrant.grantee_user_id == user_id)
            & (VisibilityGrant.source_team_id == pipeline_team_id)
        )
        # Source-team grants → user's teams
        if user_team_ids:
            conditions.append(
                VisibilityGrant.grantee_team_id.in_(user_team_ids)
                & (VisibilityGrant.source_team_id == pipeline_team_id)
            )

    return conditions


class VisibilityGrantRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_grants_for_teams(
        self, team_ids: set[uuid.UUID]
    ) -> list[VisibilityGrant]:
        """Get all visibility grants where grantee is one of the given teams."""
        if not team_ids:
            return []
        stmt = (
            select(VisibilityGrant)
            .options(
                selectinload(VisibilityGrant.grantee_team),
                selectinload(VisibilityGrant.grantee_user),
                selectinload(VisibilityGrant.source_team),
            )
            .where(VisibilityGrant.grantee_team_id.in_(team_ids))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_grants_for_user(
        self, user_id: uuid.UUID
    ) -> list[VisibilityGrant]:
        """Get all visibility grants where grantee is a specific user."""
        stmt = (
            select(VisibilityGrant)
            .options(
                selectinload(VisibilityGrant.grantee_team),
                selectinload(VisibilityGrant.grantee_user),
                selectinload(VisibilityGrant.source_team),
            )
            .where(VisibilityGrant.grantee_user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self, skip: int = 0, limit: int = 200) -> list[VisibilityGrant]:
        """List all grants (admin view)."""
        stmt = (
            select(VisibilityGrant)
            .options(
                selectinload(VisibilityGrant.grantee_team),
                selectinload(VisibilityGrant.grantee_user),
                selectinload(VisibilityGrant.source_team),
            )
            .order_by(VisibilityGrant.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """Count total visibility grants."""
        stmt = select(func.count()).select_from(VisibilityGrant)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def _find_existing_grant(
        self,
        grantee_team_id: uuid.UUID | None,
        grantee_user_id: uuid.UUID | None,
        pipeline_id: uuid.UUID | None,
        source_team_id: uuid.UUID | None,
    ) -> VisibilityGrant | None:
        """Find an existing grant matching the same target+grantee combo."""
        conditions = []
        if grantee_team_id is not None:
            conditions.append(VisibilityGrant.grantee_team_id == grantee_team_id)
        else:
            conditions.append(VisibilityGrant.grantee_team_id.is_(None))
        if grantee_user_id is not None:
            conditions.append(VisibilityGrant.grantee_user_id == grantee_user_id)
        else:
            conditions.append(VisibilityGrant.grantee_user_id.is_(None))
        if pipeline_id is not None:
            conditions.append(VisibilityGrant.pipeline_id == pipeline_id)
        else:
            conditions.append(VisibilityGrant.pipeline_id.is_(None))
        if source_team_id is not None:
            conditions.append(VisibilityGrant.source_team_id == source_team_id)
        else:
            conditions.append(VisibilityGrant.source_team_id.is_(None))

        stmt = select(VisibilityGrant).where(*conditions)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _refetch(self, grant_id: uuid.UUID) -> VisibilityGrant:
        """Re-fetch a grant with all relationships eagerly loaded."""
        stmt = (
            select(VisibilityGrant)
            .options(
                selectinload(VisibilityGrant.grantee_team),
                selectinload(VisibilityGrant.grantee_user),
                selectinload(VisibilityGrant.source_team),
            )
            .where(VisibilityGrant.id == grant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create_pipeline_grant(
        self,
        pipeline_id: uuid.UUID,
        granted_by: str,
        grantee_team_id: uuid.UUID | None = None,
        grantee_user_id: uuid.UUID | None = None,
        grant_level: str = "viewer",
    ) -> VisibilityGrant:
        """Grant a specific pipeline's visibility to a team or user.

        If a matching grant already exists, updates its grant_level instead.
        """
        existing = await self._find_existing_grant(
            grantee_team_id=grantee_team_id,
            grantee_user_id=grantee_user_id,
            pipeline_id=pipeline_id,
            source_team_id=None,
        )
        if existing:
            existing.grant_level = grant_level
            existing.granted_by = granted_by
            await self.session.flush()
            return await self._refetch(existing.id)

        grant = VisibilityGrant(
            id=uuid.uuid4(),
            grantee_team_id=grantee_team_id,
            grantee_user_id=grantee_user_id,
            pipeline_id=pipeline_id,
            source_team_id=None,
            grant_level=grant_level,
            granted_by=granted_by,
        )
        self.session.add(grant)
        await self.session.flush()
        return await self._refetch(grant.id)

    async def create_team_grant(
        self,
        source_team_id: uuid.UUID,
        granted_by: str,
        grantee_team_id: uuid.UUID | None = None,
        grantee_user_id: uuid.UUID | None = None,
        grant_level: str = "viewer",
    ) -> VisibilityGrant:
        """Grant all pipelines of a team to another team or user.

        If a matching grant already exists, updates its grant_level instead.
        """
        existing = await self._find_existing_grant(
            grantee_team_id=grantee_team_id,
            grantee_user_id=grantee_user_id,
            pipeline_id=None,
            source_team_id=source_team_id,
        )
        if existing:
            existing.grant_level = grant_level
            existing.granted_by = granted_by
            await self.session.flush()
            return await self._refetch(existing.id)

        grant = VisibilityGrant(
            id=uuid.uuid4(),
            grantee_team_id=grantee_team_id,
            grantee_user_id=grantee_user_id,
            pipeline_id=None,
            source_team_id=source_team_id,
            grant_level=grant_level,
            granted_by=granted_by,
        )
        self.session.add(grant)
        await self.session.flush()
        return await self._refetch(grant.id)

    async def has_editor_grant(
        self,
        pipeline_id: uuid.UUID,
        user_id: uuid.UUID,
        user_team_ids: set[uuid.UUID],
        pipeline_team_id: uuid.UUID | None = None,
    ) -> bool:
        """Check if a user has an editor-level grant for a pipeline (directly or via team)."""
        if pipeline_team_id is None:
            from app.models.pipeline import Pipeline

            pipeline_stmt = select(Pipeline.team_id).where(Pipeline.id == pipeline_id)
            pipeline_result = await self.session.execute(pipeline_stmt)
            pipeline_team_id = pipeline_result.scalar_one_or_none()

        conditions = _build_grant_conditions(
            pipeline_id, user_id, user_team_ids, pipeline_team_id
        )

        stmt = select(VisibilityGrant.grant_level).where(or_(*conditions))
        result = await self.session.execute(stmt)
        levels = [row[0] for row in result.all()]
        return "editor" in levels

    async def get_grant_level_for_pipeline(
        self,
        pipeline_id: uuid.UUID,
        user_id: uuid.UUID,
        user_team_ids: set[uuid.UUID],
        pipeline_team_id: uuid.UUID | None,
    ) -> str | None:
        """Return the highest grant level a user has for a pipeline, or None."""
        cache_key = f"{user_id}:{pipeline_id}"
        cached = grant_level_cache.get(cache_key)
        if cached is not None:
            return cached

        conditions = _build_grant_conditions(
            pipeline_id, user_id, user_team_ids, pipeline_team_id
        )

        stmt = select(VisibilityGrant.grant_level).where(or_(*conditions))
        result = await self.session.execute(stmt)
        levels = [row[0] for row in result.all()]

        if "editor" in levels:
            level = "editor"
        elif "viewer" in levels:
            level = "viewer"
        else:
            level = ""

        grant_level_cache.set(cache_key, level)
        return level or None

    async def user_can_see_pipeline(
        self,
        pipeline_id: uuid.UUID,
        pipeline_team_id: uuid.UUID | None,
        user_id: uuid.UUID,
        user_team_ids: set[uuid.UUID],
    ) -> bool:
        """Check if a non-admin user has visibility to a specific pipeline.

        Mirrors the conditions in ``PipelineRepository.list_visible``:
        - Unassigned pipelines (no team) are visible to everyone.
        - Pipeline belongs to one of the user's teams.
        - A visibility grant targets this pipeline for the user or their teams.
        - A visibility grant targets the pipeline's source team for the user or their teams.
        """
        if not pipeline_team_id:
            return True

        if pipeline_team_id in user_team_ids:
            return True

        conditions = _build_grant_conditions(
            pipeline_id, user_id, user_team_ids, pipeline_team_id
        )

        stmt = select(VisibilityGrant.id).where(or_(*conditions)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def delete_grant(self, grant_id: uuid.UUID) -> bool:
        """Delete a visibility grant by ID. Returns True if deleted, False if not found."""
        stmt = select(VisibilityGrant).where(VisibilityGrant.id == grant_id)
        result = await self.session.execute(stmt)
        grant = result.scalar_one_or_none()
        if not grant:
            return False
        await self.session.delete(grant)
        await self.session.flush()
        return True
