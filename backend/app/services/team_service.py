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
