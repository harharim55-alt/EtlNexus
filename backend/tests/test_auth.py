"""Tests for app.auth — FastAPI auth dependency functions.

Tests the logic of get_current_user, require_role, require_team_membership,
and require_team_membership_or_editor_grant without a real DB or HTTP server.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from tests.conftest import make_pipeline, make_team, make_user, make_user_team


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @patch("app.auth.settings")
    async def test_sso_disabled_returns_default_user(self, mock_settings, mock_session):
        mock_settings.sso_enabled = False

        from app.auth import get_current_user

        with patch("app.auth.UserAuthService") as MockService:
            default_user = make_user(role="admin", sub="default-admin")
            MockService.return_value.get_or_create_default_user = AsyncMock(return_value=default_user)

            result = await get_current_user(
                request=MagicMock(),
                credentials=None,
                session=mock_session,
            )
            assert result.role == "admin"
            assert result.sub == "default-admin"

    @patch("app.auth.settings")
    async def test_sso_enabled_no_credentials_raises_401(self, mock_settings, mock_session):
        mock_settings.sso_enabled = True

        from app.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=MagicMock(),
                credentials=None,
                session=mock_session,
            )
        assert exc_info.value.status_code == 401

    @patch("app.auth.oidc_client")
    @patch("app.auth.settings")
    async def test_sso_enabled_invalid_token_raises_401(self, mock_settings, mock_oidc, mock_session):
        mock_settings.sso_enabled = True
        mock_oidc.validate_token = AsyncMock(side_effect=Exception("invalid"))

        from app.auth import get_current_user

        creds = MagicMock()
        creds.credentials = "bad-token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=MagicMock(),
                credentials=creds,
                session=mock_session,
            )
        assert exc_info.value.status_code == 401

    @patch("app.auth.oidc_client")
    @patch("app.auth.settings")
    async def test_sso_enabled_valid_token_returns_user(self, mock_settings, mock_oidc, mock_session):
        mock_settings.sso_enabled = True
        claims = {"sub": "user1", "email": "u@test.com"}
        mock_oidc.validate_token = AsyncMock(return_value=claims)

        from app.auth import get_current_user

        user = make_user(sub="user1")
        with patch("app.auth.UserAuthService") as MockService:
            MockService.return_value.upsert_from_claims = AsyncMock(return_value=user)

            creds = MagicMock()
            creds.credentials = "good-token"
            result = await get_current_user(
                request=MagicMock(),
                credentials=creds,
                session=mock_session,
            )
            assert result.sub == "user1"


# ---------------------------------------------------------------------------
# get_current_user_optional
# ---------------------------------------------------------------------------


class TestGetCurrentUserOptional:
    @patch("app.auth.settings")
    async def test_sso_disabled_returns_default(self, mock_settings, mock_session):
        mock_settings.sso_enabled = False

        from app.auth import get_current_user_optional

        with patch("app.auth.UserAuthService") as MockService:
            default_user = make_user(role="admin", sub="default-admin")
            MockService.return_value.get_or_create_default_user = AsyncMock(return_value=default_user)

            result = await get_current_user_optional(
                request=MagicMock(), credentials=None, session=mock_session,
            )
            assert result is not None

    @patch("app.auth.settings")
    async def test_sso_enabled_no_credentials_returns_none(self, mock_settings, mock_session):
        mock_settings.sso_enabled = True

        from app.auth import get_current_user_optional

        result = await get_current_user_optional(
            request=MagicMock(), credentials=None, session=mock_session,
        )
        assert result is None


# ---------------------------------------------------------------------------
# require_role
# ---------------------------------------------------------------------------


class TestRequireRole:
    async def test_matching_role_passes(self):
        from app.auth import require_role

        checker = require_role("admin")
        user = make_user(role="admin")
        result = await checker(user=user)
        assert result.role == "admin"

    async def test_multiple_accepted_roles(self):
        from app.auth import require_role

        checker = require_role("admin", "member")
        user = make_user(role="member")
        result = await checker(user=user)
        assert result.role == "member"

    async def test_wrong_role_raises_403(self):
        from app.auth import require_role

        checker = require_role("admin")
        user = make_user(role="viewer")
        with pytest.raises(HTTPException) as exc_info:
            await checker(user=user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# require_team_membership
# ---------------------------------------------------------------------------


class TestRequireTeamMembership:
    async def test_admin_bypasses(self, mock_session):
        from app.auth import require_team_membership

        checker = require_team_membership()
        user = make_user(role="admin")
        request = MagicMock()
        request.path_params = {"pipeline_id": str(uuid.uuid4())}

        result = await checker(request=request, user=user, session=mock_session)
        assert result.role == "admin"

    async def test_no_pipeline_id_passes(self, mock_session):
        from app.auth import require_team_membership

        checker = require_team_membership()
        user = make_user(role="member")
        request = MagicMock()
        request.path_params = {}

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    async def test_invalid_uuid_passes(self, mock_session):
        from app.auth import require_team_membership

        checker = require_team_membership()
        user = make_user(role="member")
        request = MagicMock()
        request.path_params = {"pipeline_id": "not-a-uuid"}

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_unassigned_pipeline_passes(self, mock_get_by_id, mock_session):
        from app.auth import require_team_membership

        pipeline = make_pipeline()
        pipeline.team_id = None
        mock_get_by_id.return_value = pipeline

        checker = require_team_membership()
        user = make_user(role="member")
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_team_member_passes(self, mock_get_by_id, mock_session):
        from app.auth import require_team_membership

        team = make_team(name="Dagger")
        pipeline = make_pipeline(team="Dagger", team_id=team.id)
        mock_get_by_id.return_value = pipeline

        user = make_user(role="member")
        ut = make_user_team(user, team)
        user.team_memberships = [ut]

        checker = require_team_membership()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_non_member_raises_403(self, mock_get_by_id, mock_session):
        from app.auth import require_team_membership

        team = make_team(name="Dagger")
        pipeline = make_pipeline(team="Dagger", team_id=team.id)
        mock_get_by_id.return_value = pipeline

        user = make_user(role="member")
        user.team_memberships = []  # Not a member

        checker = require_team_membership()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}

        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user, session=mock_session)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# require_team_membership_or_editor_grant
# ---------------------------------------------------------------------------


class TestRequireTeamMembershipOrEditorGrant:
    async def test_admin_bypasses(self, mock_session):
        from app.auth import require_team_membership_or_editor_grant

        checker = require_team_membership_or_editor_grant()
        user = make_user(role="admin")
        request = MagicMock()
        request.path_params = {"pipeline_id": str(uuid.uuid4())}

        result = await checker(request=request, user=user, session=mock_session)
        assert result.role == "admin"

    @patch("app.repositories.visibility_grant_repo.VisibilityGrantRepository.has_editor_grant")
    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_editor_grant_passes(self, mock_get_by_id, mock_has_editor, mock_session):
        from app.auth import require_team_membership_or_editor_grant

        team = make_team(name="Vault")
        pipeline = make_pipeline(team="Vault", team_id=team.id)
        mock_get_by_id.return_value = pipeline
        mock_has_editor.return_value = True

        user = make_user(role="member")
        user.team_memberships = []  # Not a member of Vault

        checker = require_team_membership_or_editor_grant()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}
        request.state = MagicMock()

        result = await checker(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.visibility_grant_repo.VisibilityGrantRepository.has_editor_grant")
    @patch("app.repositories.pipeline_repo.PipelineRepository.get_by_id")
    async def test_no_grant_no_membership_raises_403(self, mock_get_by_id, mock_has_editor, mock_session):
        from app.auth import require_team_membership_or_editor_grant

        team = make_team(name="Vault")
        pipeline = make_pipeline(team="Vault", team_id=team.id)
        mock_get_by_id.return_value = pipeline
        mock_has_editor.return_value = False

        user = make_user(role="member")
        user.team_memberships = []

        checker = require_team_membership_or_editor_grant()
        request = MagicMock()
        request.path_params = {"pipeline_id": str(pipeline.id)}
        request.state = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user, session=mock_session)
        assert exc_info.value.status_code == 403
