"""Visibility grant repository — async SQLAlchemy data access for visibility grants."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.visibility_grant import VisibilityGrant


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
            )
            .where(VisibilityGrant.grantee_user_id == user_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all(self) -> list[VisibilityGrant]:
        """List all grants (admin view)."""
        stmt = (
            select(VisibilityGrant)
            .options(
                selectinload(VisibilityGrant.grantee_team),
                selectinload(VisibilityGrant.grantee_user),
            )
            .order_by(VisibilityGrant.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _refetch(self, grant_id: uuid.UUID) -> VisibilityGrant:
        """Re-fetch a grant with all relationships eagerly loaded."""
        stmt = (
            select(VisibilityGrant)
            .options(
                selectinload(VisibilityGrant.grantee_team),
                selectinload(VisibilityGrant.grantee_user),
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
        """Grant a specific pipeline's visibility to a team or user."""
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
        """Grant all pipelines of a team to another team or user."""
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
    ) -> bool:
        """Check if a user has an editor-level grant for a pipeline (directly or via team)."""
        from app.models.pipeline import Pipeline

        # Look up the pipeline's team_id for team-grant matching
        pipeline_stmt = select(Pipeline.team_id).where(Pipeline.id == pipeline_id)
        pipeline_result = await self.session.execute(pipeline_stmt)
        pipeline_team_id = pipeline_result.scalar_one_or_none()

        conditions = []

        # Direct pipeline grants to this user
        conditions.append(
            (VisibilityGrant.grantee_user_id == user_id)
            & (VisibilityGrant.pipeline_id == pipeline_id)
        )

        # Direct pipeline grants to user's teams
        if user_team_ids:
            conditions.append(
                VisibilityGrant.grantee_team_id.in_(user_team_ids)
                & (VisibilityGrant.pipeline_id == pipeline_id)
            )

        # Team-level grants (source_team_id) to this user
        if pipeline_team_id:
            conditions.append(
                (VisibilityGrant.grantee_user_id == user_id)
                & (VisibilityGrant.source_team_id == pipeline_team_id)
            )
            # Team-level grants to user's teams
            if user_team_ids:
                conditions.append(
                    VisibilityGrant.grantee_team_id.in_(user_team_ids)
                    & (VisibilityGrant.source_team_id == pipeline_team_id)
                )

        from sqlalchemy import or_

        stmt = (
            select(VisibilityGrant.grant_level)
            .where(or_(*conditions))
        )
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
        from sqlalchemy import or_

        conditions = []

        # Direct pipeline grants to this user
        conditions.append(
            (VisibilityGrant.grantee_user_id == user_id)
            & (VisibilityGrant.pipeline_id == pipeline_id)
        )

        # Direct pipeline grants to user's teams
        if user_team_ids:
            conditions.append(
                VisibilityGrant.grantee_team_id.in_(user_team_ids)
                & (VisibilityGrant.pipeline_id == pipeline_id)
            )

        # Team-level grants (source_team_id) to this user
        if pipeline_team_id:
            conditions.append(
                (VisibilityGrant.grantee_user_id == user_id)
                & (VisibilityGrant.source_team_id == pipeline_team_id)
            )
            if user_team_ids:
                conditions.append(
                    VisibilityGrant.grantee_team_id.in_(user_team_ids)
                    & (VisibilityGrant.source_team_id == pipeline_team_id)
                )

        stmt = select(VisibilityGrant.grant_level).where(or_(*conditions))
        result = await self.session.execute(stmt)
        levels = [row[0] for row in result.all()]

        if "editor" in levels:
            return "editor"
        if "viewer" in levels:
            return "viewer"
        return None

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
