"""Visibility service — business logic for managing visibility grants."""

import uuid

from app.cache import grant_level_cache
from app.models.visibility_grant import VisibilityGrant
from app.repositories.team_repo import TeamRepository
from app.repositories.visibility_grant_repo import VisibilityGrantRepository


class VisibilityService:
    def __init__(
        self,
        grant_repo: VisibilityGrantRepository,
        team_repo: TeamRepository,
    ):
        self.grant_repo = grant_repo
        self.team_repo = team_repo

    async def list_grants(
        self, skip: int = 0, limit: int = 200
    ) -> tuple[list[VisibilityGrant], int]:
        """Return all visibility grants with total count."""
        grants = await self.grant_repo.get_all(skip=skip, limit=limit)
        total = await self.grant_repo.count_all()
        return grants, total

    async def create_grant(
        self,
        pipeline_id: uuid.UUID | None = None,
        source_team_id: uuid.UUID | None = None,
        grantee_team_id: uuid.UUID | None = None,
        grantee_user_id: uuid.UUID | None = None,
        granted_by: str = "",
        grant_level: str = "viewer",
        granted_by_user_id: uuid.UUID | None = None,
    ) -> VisibilityGrant:
        """Create a visibility grant.

        Exactly one of pipeline_id or source_team_id must be set (target).
        Exactly one of grantee_team_id or grantee_user_id must be set (recipient).
        grant_level must be "viewer" or "editor".
        """
        if (pipeline_id is None) == (source_team_id is None):
            raise ValueError(
                "Exactly one of pipeline_id or source_team_id must be provided."
            )
        if (grantee_team_id is None) == (grantee_user_id is None):
            raise ValueError(
                "Exactly one of grantee_team_id or grantee_user_id must be provided."
            )
        if grant_level not in ("viewer", "editor"):
            raise ValueError("grant_level must be 'viewer' or 'editor'")

        if pipeline_id is not None:
            grant = await self.grant_repo.create_pipeline_grant(
                pipeline_id=pipeline_id,
                granted_by=granted_by,
                grantee_team_id=grantee_team_id,
                grantee_user_id=grantee_user_id,
                grant_level=grant_level,
                granted_by_user_id=granted_by_user_id,
            )
        else:
            grant = await self.grant_repo.create_team_grant(
                source_team_id=source_team_id,  # type: ignore[arg-type]
                granted_by=granted_by,
                grantee_team_id=grantee_team_id,
                grantee_user_id=grantee_user_id,
                grant_level=grant_level,
                granted_by_user_id=granted_by_user_id,
            )

        grant_level_cache.clear()
        return grant

    async def delete_grant(self, grant_id: uuid.UUID) -> bool:
        """Delete a visibility grant. Returns True if deleted, False if not found."""
        deleted = await self.grant_repo.delete_grant(grant_id)
        if deleted:
            grant_level_cache.clear()
        return deleted
