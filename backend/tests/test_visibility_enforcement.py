"""Tests for require_pipeline_visibility() and require_pipeline_visibility_by_name().

These dependency factories enforce that non-admin users may only access
pipelines they are allowed to see according to the visibility grant rules.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from tests.conftest import make_pipeline, make_team, make_user, make_user_team


# ---------------------------------------------------------------------------
# require_pipeline_visibility
# ---------------------------------------------------------------------------


class TestRequirePipelineVisibility:
    async def test_admin_can_access_any_pipeline(self, mock_session):
        """Admin users bypass all visibility checks entirely."""
        from app.auth import require_pipeline_visibility

        checker = require_pipeline_visibility()
        user = make_user(role="admin")
        request = MagicMock()
        request.path_params = {"pipeline_id": str(uuid.uuid4())}

        result = await checker(request=request, user=user, session=mock_session)
        assert result.role == "admin"

    @patch("app.repositories.visibility_grant_repo.VisibilityGrantRepository.user_can_see_pipeline")
    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_team_member_can_access_own_teams_pipeline(
        self, mock_get_by_id, mock_can_see, mock_session
    ):
        """Non-admin user who belongs to the pipeline's team can access it."""
        from app.auth import require_pipeline_visibility

        team = make_team(name="Dagger")
        pipeline = make_pipeline(team="Dagger", team_id=team.id)
        mock_get_by_id.return_value = pipeline

        user = make_user(role="member")
        ut = make_user_team(user, team)
        user.team_memberships = [ut]

        # user_can_see_pipeline should return True for team members
        mock_can_see.return_value = True

        checker = require_pipeline_visibility()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}
        request.state = MagicMock()

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.visibility_grant_repo.VisibilityGrantRepository.user_can_see_pipeline")
    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_user_with_visibility_grant_can_access(
        self, mock_get_by_id, mock_can_see, mock_session
    ):
        """Non-admin user with a visibility grant can access a pipeline from another team."""
        from app.auth import require_pipeline_visibility

        other_team = make_team(name="Vault")
        pipeline = make_pipeline(team="Vault", team_id=other_team.id)
        mock_get_by_id.return_value = pipeline

        user = make_user(role="member")
        user.team_memberships = []  # Not a member of Vault

        # Visibility grant exists
        mock_can_see.return_value = True

        checker = require_pipeline_visibility()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}
        request.state = MagicMock()

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.visibility_grant_repo.VisibilityGrantRepository.user_can_see_pipeline")
    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_user_without_access_gets_404(
        self, mock_get_by_id, mock_can_see, mock_session
    ):
        """Non-admin user without team membership or grant gets HTTP 404."""
        from app.auth import require_pipeline_visibility

        other_team = make_team(name="Vault")
        pipeline = make_pipeline(team="Vault", team_id=other_team.id)
        mock_get_by_id.return_value = pipeline

        user = make_user(role="member")
        user.team_memberships = []

        mock_can_see.return_value = False

        checker = require_pipeline_visibility()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}
        request.state = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user, session=mock_session)
        assert exc_info.value.status_code == 404

    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_unassigned_pipeline_accessible_to_all(
        self, mock_get_by_id, mock_session
    ):
        """Pipeline with no team_id is visible to all authenticated users."""
        from app.auth import require_pipeline_visibility

        pipeline = make_pipeline()
        pipeline.team_id = None
        mock_get_by_id.return_value = pipeline

        user = make_user(role="viewer")
        user.team_memberships = []

        checker = require_pipeline_visibility()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}
        request.state = MagicMock()

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_missing_pipeline_raises_404(self, mock_get_by_id, mock_session):
        """When the pipeline UUID does not exist, raise HTTP 404."""
        from app.auth import require_pipeline_visibility

        mock_get_by_id.return_value = None

        user = make_user(role="member")
        checker = require_pipeline_visibility()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(uuid.uuid4())}

        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user, session=mock_session)
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# require_pipeline_visibility_by_name
# ---------------------------------------------------------------------------


class TestRequirePipelineVisibilityByName:
    @patch("app.repositories.visibility_grant_repo.VisibilityGrantRepository.user_can_see_pipeline")
    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_task_id")
    async def test_resolves_etl_name_and_checks_visibility(
        self, mock_get_by_task_id, mock_can_see, mock_session
    ):
        """Resolves a pipeline by task_id from the etl_name path param."""
        from app.auth import require_pipeline_visibility_by_name

        team = make_team(name="Prism")
        pipeline = make_pipeline(task_id="PortScanCollector", team="Prism", team_id=team.id)
        mock_get_by_task_id.return_value = pipeline
        mock_can_see.return_value = True

        user = make_user(role="member")
        ut = make_user_team(user, team)
        user.team_memberships = [ut]

        checker = require_pipeline_visibility_by_name()
        request = MagicMock()
        request.path_params = {"etl_name": "PortScanCollector"}
        request.state = MagicMock()

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None
        mock_get_by_task_id.assert_awaited_once_with("PortScanCollector")

    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_task_id")
    async def test_unknown_etl_name_returns_user_gracefully(
        self, mock_get_by_task_id, mock_session
    ):
        """When no pipeline matches the etl_name, the user is returned without error."""
        from app.auth import require_pipeline_visibility_by_name

        mock_get_by_task_id.return_value = None

        user = make_user(role="member")
        user.team_memberships = []

        checker = require_pipeline_visibility_by_name()
        request = MagicMock()
        request.path_params = {"etl_name": "NonExistentTask"}

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None
        assert result.role == "member"

    async def test_admin_bypasses_name_based_check(self, mock_session):
        """Admin users bypass the name-based visibility check."""
        from app.auth import require_pipeline_visibility_by_name

        checker = require_pipeline_visibility_by_name()
        user = make_user(role="admin")
        request = MagicMock()
        request.path_params = {"etl_name": "AnyTask"}

        result = await checker(request=request, user=user, session=mock_session)
        assert result.role == "admin"

    @patch("app.repositories.visibility_grant_repo.VisibilityGrantRepository.user_can_see_pipeline")
    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_task_id")
    async def test_denied_name_based_access_raises_404(
        self, mock_get_by_task_id, mock_can_see, mock_session
    ):
        """Non-admin user without access via name-based lookup gets HTTP 404."""
        from app.auth import require_pipeline_visibility_by_name

        team = make_team(name="Vault")
        pipeline = make_pipeline(task_id="SecretCollector", team="Vault", team_id=team.id)
        mock_get_by_task_id.return_value = pipeline
        mock_can_see.return_value = False

        user = make_user(role="member")
        user.team_memberships = []

        checker = require_pipeline_visibility_by_name()
        request = MagicMock()
        request.path_params = {"etl_name": "SecretCollector"}
        request.state = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user, session=mock_session)
        assert exc_info.value.status_code == 404

    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_task_id")
    async def test_unassigned_pipeline_by_name_accessible(
        self, mock_get_by_task_id, mock_session
    ):
        """Unassigned pipeline found by name is visible to all."""
        from app.auth import require_pipeline_visibility_by_name

        pipeline = make_pipeline(task_id="SharedCollector")
        pipeline.team_id = None
        mock_get_by_task_id.return_value = pipeline

        user = make_user(role="viewer")
        user.team_memberships = []

        checker = require_pipeline_visibility_by_name()
        request = MagicMock()
        request.path_params = {"etl_name": "SharedCollector"}
        request.state = MagicMock()

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None
