"""Tests for VisibilityService — business logic for grant management."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.visibility_service import VisibilityService
from tests.conftest import make_grant


@pytest.fixture
def grant_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def team_repo():
    repo = AsyncMock()
    return repo


@pytest.fixture
def service(grant_repo, team_repo):
    return VisibilityService(grant_repo, team_repo)


class TestListGrants:
    async def test_delegates_to_repo(self, service, grant_repo):
        grants = [make_grant(), make_grant()]
        grant_repo.get_all.return_value = grants
        result = await service.list_grants()
        assert len(result) == 2
        grant_repo.get_all.assert_awaited_once()


class TestCreateGrant:
    async def test_pipeline_grant_to_team(self, service, grant_repo):
        expected = make_grant()
        grant_repo.create_pipeline_grant.return_value = expected

        result = await service.create_grant(
            pipeline_id=uuid.uuid4(),
            grantee_team_id=uuid.uuid4(),
            granted_by="Admin",
            grant_level="viewer",
        )
        assert result == expected
        grant_repo.create_pipeline_grant.assert_awaited_once()
        grant_repo.create_team_grant.assert_not_awaited()

    async def test_team_grant_to_user(self, service, grant_repo):
        expected = make_grant()
        grant_repo.create_team_grant.return_value = expected

        result = await service.create_grant(
            source_team_id=uuid.uuid4(),
            grantee_user_id=uuid.uuid4(),
            granted_by="Admin",
            grant_level="editor",
        )
        assert result == expected
        grant_repo.create_team_grant.assert_awaited_once()
        grant_repo.create_pipeline_grant.assert_not_awaited()

    async def test_both_targets_raises(self, service):
        with pytest.raises(ValueError, match="Exactly one"):
            await service.create_grant(
                pipeline_id=uuid.uuid4(),
                source_team_id=uuid.uuid4(),
                grantee_team_id=uuid.uuid4(),
            )

    async def test_no_target_raises(self, service):
        with pytest.raises(ValueError, match="Exactly one"):
            await service.create_grant(
                grantee_team_id=uuid.uuid4(),
            )

    async def test_both_grantees_raises(self, service):
        with pytest.raises(ValueError, match="Exactly one"):
            await service.create_grant(
                pipeline_id=uuid.uuid4(),
                grantee_team_id=uuid.uuid4(),
                grantee_user_id=uuid.uuid4(),
            )

    async def test_no_grantee_raises(self, service):
        with pytest.raises(ValueError, match="Exactly one"):
            await service.create_grant(
                pipeline_id=uuid.uuid4(),
            )

    async def test_invalid_grant_level_raises(self, service):
        with pytest.raises(ValueError, match="grant_level"):
            await service.create_grant(
                pipeline_id=uuid.uuid4(),
                grantee_team_id=uuid.uuid4(),
                grant_level="superadmin",
            )


class TestDeleteGrant:
    async def test_delegates_to_repo_success(self, service, grant_repo):
        grant_repo.delete_grant.return_value = True
        result = await service.delete_grant(uuid.uuid4())
        assert result is True

    async def test_delegates_to_repo_not_found(self, service, grant_repo):
        grant_repo.delete_grant.return_value = False
        result = await service.delete_grant(uuid.uuid4())
        assert result is False
