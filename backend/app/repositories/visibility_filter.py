"""Centralized visibility filter — single source of truth for grant-based authorization conditions.

Replaces duplicated grant condition logic that was previously scattered across
visibility_grant_repo.py, pipeline_repo.py, and auth.py.
"""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pipeline import Pipeline
from app.models.visibility_grant import VisibilityGrant


class VisibilityFilter:
    """Builds SQLAlchemy conditions for grant-based pipeline visibility."""

    @staticmethod
    def build_single_pipeline_conditions(
        pipeline_id: uuid.UUID,
        user_id: uuid.UUID,
        user_team_ids: set[uuid.UUID],
        pipeline_team_id: uuid.UUID | None,
    ) -> list:
        """Build OR-able SQLAlchemy conditions matching any grant that covers a pipeline.

        Returns a list of BinaryExpression clauses covering:
        - Direct pipeline grants to the user
        - Direct pipeline grants to user's teams
        - Source-team grants to the user
        - Source-team grants to user's teams
        """
        conditions = []

        # Direct pipeline grants -> user
        conditions.append(
            (VisibilityGrant.grantee_user_id == user_id)
            & (VisibilityGrant.pipeline_id == pipeline_id)
        )

        # Direct pipeline grants -> user's teams
        if user_team_ids:
            conditions.append(
                VisibilityGrant.grantee_team_id.in_(user_team_ids)
                & (VisibilityGrant.pipeline_id == pipeline_id)
            )

        # Source-team grants -> user
        if pipeline_team_id:
            conditions.append(
                (VisibilityGrant.grantee_user_id == user_id)
                & (VisibilityGrant.source_team_id == pipeline_team_id)
            )
            # Source-team grants -> user's teams
            if user_team_ids:
                conditions.append(
                    VisibilityGrant.grantee_team_id.in_(user_team_ids)
                    & (VisibilityGrant.source_team_id == pipeline_team_id)
                )

        return conditions

    @staticmethod
    async def build_batch_visibility_conditions(
        session: AsyncSession,
        user_id: uuid.UUID | None,
        user_team_ids: set[uuid.UUID] | None,
    ) -> list:
        """Build Pipeline-level OR conditions for batch list queries.

        Pre-fetches all grant-visible pipeline IDs and team IDs in one flat
        query instead of using correlated subqueries. Returns a list of
        Pipeline column conditions to be OR-ed together.

        Always includes Pipeline.team_id.is_(None) (unassigned pipelines visible to all).
        """
        visibility_conditions = [Pipeline.team_id.is_(None)]

        if user_team_ids:
            visibility_conditions.append(Pipeline.team_id.in_(user_team_ids))

        grant_conditions = []
        if user_team_ids:
            grant_conditions.append(
                VisibilityGrant.grantee_team_id.in_(user_team_ids)
            )
        if user_id:
            grant_conditions.append(
                VisibilityGrant.grantee_user_id == user_id
            )

        if grant_conditions:
            grant_stmt = select(
                VisibilityGrant.pipeline_id,
                VisibilityGrant.source_team_id,
            ).where(or_(*grant_conditions))
            grant_result = await session.execute(grant_stmt)

            granted_pipeline_ids: set[uuid.UUID] = set()
            granted_source_team_ids: set[uuid.UUID] = set()
            for row in grant_result.all():
                if row.pipeline_id:
                    granted_pipeline_ids.add(row.pipeline_id)
                if row.source_team_id:
                    granted_source_team_ids.add(row.source_team_id)

            if granted_pipeline_ids:
                visibility_conditions.append(
                    Pipeline.id.in_(granted_pipeline_ids)
                )
            if granted_source_team_ids:
                visibility_conditions.append(
                    Pipeline.team_id.in_(granted_source_team_ids)
                )

        return visibility_conditions
