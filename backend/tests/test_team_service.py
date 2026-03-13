"""Tests for TeamService — team listing and detail retrieval."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.services.team_service import TeamService
from tests.conftest import make_pipeline, make_team


@pytest.fixture
def team_repo():
    return AsyncMock()


@pytest.fixture
def pipeline_repo():
    return AsyncMock()


@pytest.fixture
def service(team_repo, pipeline_repo):
    return TeamService(team_repo, pipeline_repo)


class TestListTeams:
    async def test_returns_all_teams(self, service, team_repo):
        teams = [make_team(name="Dagger"), make_team(name="Vault")]
        team_repo.get_all.return_value = teams
        result = await service.list_teams()
        assert len(result) == 2
        team_repo.get_all.assert_awaited_once()


class TestGetTeamDetail:
    async def test_returns_team(self, service, team_repo):
        team = make_team(name="Prism")
        team_repo.get_by_id.return_value = team
        result = await service.get_team_detail(team.id)
        assert result.name == "Prism"

    async def test_returns_none_when_not_found(self, service, team_repo):
        team_repo.get_by_id.return_value = None
        result = await service.get_team_detail(uuid.uuid4())
        assert result is None


class TestGetTeamPipelines:
    async def test_delegates_to_pipeline_repo(self, service, pipeline_repo):
        pipelines = [make_pipeline(), make_pipeline(name="P2")]
        pipeline_repo.get_by_team_id.return_value = pipelines
        result = await service.get_team_pipelines(uuid.uuid4())
        assert len(result) == 2
        pipeline_repo.get_by_team_id.assert_awaited_once()
