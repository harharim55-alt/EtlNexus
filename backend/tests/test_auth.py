"""Tests for app.auth — FastAPI auth dependency functions.

Tests get_current_user, require_role, require_team_membership, and
require_product_visibility without a real DB or HTTP server.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from tests.conftest import make_auth_user, make_product

# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @patch("app.auth.settings")
    async def test_sso_disabled_returns_default_admin(self, mock_settings):
        mock_settings.sso_enabled = False

        from app.auth import get_current_user

        result = await get_current_user(request=MagicMock(), credentials=None)
        assert result.role == "admin"
        assert result.username == "admin"

    @patch("app.auth.settings")
    async def test_sso_enabled_no_credentials_raises_401(self, mock_settings):
        mock_settings.sso_enabled = True

        from app.auth import get_current_user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=MagicMock(), credentials=None)
        assert exc_info.value.status_code == 401

    @patch("app.auth.oidc_client")
    @patch("app.auth.settings")
    async def test_sso_enabled_invalid_token_raises_401(self, mock_settings, mock_oidc):
        mock_settings.sso_enabled = True
        mock_oidc.validate_token = AsyncMock(side_effect=Exception("invalid"))

        from app.auth import get_current_user

        creds = MagicMock()
        creds.credentials = "bad-token"

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=MagicMock(), credentials=creds)
        assert exc_info.value.status_code == 401

    @patch("app.auth.oidc_client")
    @patch("app.auth.settings")
    async def test_sso_enabled_valid_token_builds_user(self, mock_settings, mock_oidc):
        mock_settings.sso_enabled = True
        mock_oidc.validate_token = AsyncMock(return_value={"preferred_username": "bob", "email": "bob@test.com"})
        mock_oidc.extract_groups = MagicMock(return_value=["Dagger"])

        from app.auth import get_current_user

        creds = MagicMock()
        creds.credentials = "good-token"
        with patch("app.auth.team_is_allowed", return_value=True):
            result = await get_current_user(request=MagicMock(), credentials=creds)
        assert result.username == "bob"
        assert result.role == "member"
        assert result.teams == ["Dagger"]


# ---------------------------------------------------------------------------
# get_current_user_optional
# ---------------------------------------------------------------------------


class TestGetCurrentUserOptional:
    @patch("app.auth.settings")
    async def test_sso_disabled_returns_default(self, mock_settings):
        mock_settings.sso_enabled = False

        from app.auth import get_current_user_optional

        result = await get_current_user_optional(request=MagicMock(), credentials=None)
        assert result is not None

    @patch("app.auth.settings")
    async def test_sso_enabled_no_credentials_returns_none(self, mock_settings):
        mock_settings.sso_enabled = True

        from app.auth import get_current_user_optional

        result = await get_current_user_optional(request=MagicMock(), credentials=None)
        assert result is None


# ---------------------------------------------------------------------------
# _user_from_claims
# ---------------------------------------------------------------------------


class TestUserFromClaims:
    @patch("app.auth.oidc_client")
    def test_dedupes_same_alias_teams(self, mock_oidc):
        """Several SSO groups mapped to the same alias collapse to one team."""
        mock_oidc.extract_groups = MagicMock(return_value=["Dagger", "Dagger", "Vault"])

        from app.auth import _user_from_claims

        with patch("app.auth.team_is_allowed", return_value=True):
            user = _user_from_claims({"preferred_username": "bob"})
        assert user.teams == ["Dagger", "Vault"]

    @patch("app.auth.oidc_client")
    def test_full_name_from_given_family(self, mock_oidc):
        mock_oidc.extract_groups = MagicMock(return_value=[])

        from app.auth import _user_from_claims

        user = _user_from_claims({"preferred_username": "bob", "given_name": "Bob", "family_name": "Jones"})
        assert user.full_name == "Bob Jones"


# ---------------------------------------------------------------------------
# require_role
# ---------------------------------------------------------------------------


class TestRequireRole:
    async def test_matching_role_passes(self):
        from app.auth import require_role

        result = await require_role("admin")(user=make_auth_user(role="admin"))
        assert result.role == "admin"

    async def test_multiple_accepted_roles(self):
        from app.auth import require_role

        result = await require_role("admin", "member")(user=make_auth_user(role="member"))
        assert result.role == "member"

    async def test_wrong_role_raises_403(self):
        from app.auth import require_role

        with pytest.raises(HTTPException) as exc_info:
            await require_role("admin")(user=make_auth_user(role="viewer"))
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# require_team_membership
# ---------------------------------------------------------------------------


class TestRequireTeamMembership:
    @patch("app.repositories.data_product_repo.DataProductRepository.get_by_id")
    async def test_admin_not_in_team_is_blocked(self, mock_get_by_id, mock_session):
        """Editing is team-scoped even for admins (team leader != global editor)."""
        from app.auth import require_team_membership

        product = make_product(team="Vault")
        mock_get_by_id.return_value = product

        user = make_auth_user(role="admin", teams=[])  # admin, but not in Vault
        checker = require_team_membership()
        request = MagicMock()
        request.path_params = {"product_id": str(product.id)}

        with pytest.raises(HTTPException) as exc_info:
            await checker(request=request, user=user, session=mock_session)
        assert exc_info.value.status_code == 403

    async def test_no_product_id_passes(self, mock_session):
        from app.auth import require_team_membership

        request = MagicMock()
        request.path_params = {}
        result = await require_team_membership()(
            request=request, user=make_auth_user(role="member"), session=mock_session
        )
        assert result is not None

    async def test_invalid_uuid_passes(self, mock_session):
        from app.auth import require_team_membership

        request = MagicMock()
        request.path_params = {"product_id": "not-a-uuid"}
        result = await require_team_membership()(
            request=request, user=make_auth_user(role="member"), session=mock_session
        )
        assert result is not None

    @patch("app.repositories.data_product_repo.DataProductRepository.get_by_id")
    async def test_unassigned_product_creator_can_edit(self, mock_get_by_id, mock_session):
        from app.auth import require_team_membership

        product = make_product(team=None, created_by="tester")
        mock_get_by_id.return_value = product

        request = MagicMock()
        request.path_params = {"product_id": str(product.id)}
        result = await require_team_membership()(
            request=request, user=make_auth_user(role="member", username="tester"), session=mock_session
        )
        assert result is not None

    @patch("app.repositories.data_product_repo.DataProductRepository.get_by_id")
    async def test_unassigned_product_non_creator_blocked(self, mock_get_by_id, mock_session):
        from app.auth import require_team_membership

        product = make_product(team=None, created_by="someone-else")
        mock_get_by_id.return_value = product

        request = MagicMock()
        request.path_params = {"product_id": str(product.id)}
        with pytest.raises(HTTPException) as exc_info:
            await require_team_membership()(
                request=request, user=make_auth_user(role="member", username="tester"), session=mock_session
            )
        assert exc_info.value.status_code == 403

    @patch("app.repositories.data_product_repo.DataProductRepository.get_by_id")
    async def test_team_member_passes_case_insensitive(self, mock_get_by_id, mock_session):
        from app.auth import require_team_membership

        product = make_product(team="vault")  # lowercase namespace
        mock_get_by_id.return_value = product

        user = make_auth_user(role="member", teams=["Vault"])  # title-case team
        request = MagicMock()
        request.path_params = {"product_id": str(product.id)}
        result = await require_team_membership()(request=request, user=user, session=mock_session)
        assert result is not None

    @patch("app.repositories.data_product_repo.DataProductRepository.get_by_id")
    async def test_non_member_raises_403(self, mock_get_by_id, mock_session):
        from app.auth import require_team_membership

        product = make_product(team="Dagger")
        mock_get_by_id.return_value = product

        user = make_auth_user(role="member", teams=["Prism"])
        request = MagicMock()
        request.path_params = {"product_id": str(product.id)}

        with pytest.raises(HTTPException) as exc_info:
            await require_team_membership()(request=request, user=user, session=mock_session)
        assert exc_info.value.status_code == 403

    async def test_viewer_blocked(self, mock_session):
        from app.auth import require_team_membership

        request = MagicMock()
        request.path_params = {}
        with pytest.raises(HTTPException) as exc_info:
            await require_team_membership()(request=request, user=make_auth_user(role="viewer"), session=mock_session)
        assert exc_info.value.status_code == 403
