"""Team service — business logic for team listing and detail retrieval."""

import uuid

from app.models.team import Team
from app.repositories.pipeline_repo import PipelineRepository
from app.repositories.team_repo import TeamRepository


class TeamService:
    def __init__(
        self,
        team_repo: TeamRepository,
        pipeline_repo: PipelineRepository,
    ):
        self.team_repo = team_repo
        self.pipeline_repo = pipeline_repo

    async def list_teams(self) -> list[Team]:
        """Return all teams ordered by name."""
        return await self.team_repo.get_all()

    async def get_team_detail(self, team_id: uuid.UUID) -> Team | None:
        """Return a single team with its members eagerly loaded, or None."""
        return await self.team_repo.get_by_id(team_id)

    async def get_team_pipelines(self, team_id: uuid.UUID) -> list:
        """Get all pipelines owned by this team."""
        return await self.pipeline_repo.get_by_team_id(team_id)

    async def add_member_by_username(self, team_id: uuid.UUID, username: str):
        """Add an existing user (looked up by username/email) to a team.

        Returns the added User, or None when no user matches the username.
        """
        user = await self.team_repo.find_user_by_username(username)
        if not user:
            return None
        await self.team_repo.add_member(team_id, user.id)
        return user

    async def remove_member(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Remove a user from a team. Returns True if a membership was removed."""
        return await self.team_repo.remove_member(team_id, user_id)

    @staticmethod
    def user_can_access_team(user: "object", team_id: uuid.UUID) -> bool:
        """Return whether the user may access team detail or team pipelines.

        Admins may always access any team.  Other roles may only access teams
        they belong to.

        Args:
            user: Authenticated ``User`` ORM instance (or compatible mock).
            team_id: UUID of the team to check access for.

        Returns:
            ``True`` when access is permitted, ``False`` otherwise.
        """
        if getattr(user, "role", None) == "admin":
            return True
        memberships = getattr(user, "team_memberships", None) or []
        user_team_ids = {ut.team_id for ut in memberships}
        return team_id in user_team_ids
