"""Tests for auth schema helper functions (user_to_response)."""

from unittest.mock import patch

from app.auth import AuthUser
from app.schemas.auth import user_to_response


class TestUserToResponse:
    def test_user_with_teams(self):
        u = AuthUser(username="bob", email="b@t.local", role="member", teams=["Dagger"])
        resp = user_to_response(u)
        assert resp.username == "bob"
        assert resp.role == "member"
        assert resp.teams == ["Dagger"]

    def test_user_with_no_teams(self):
        u = AuthUser(username="alice", role="admin", teams=[])
        resp = user_to_response(u)
        assert resp.teams == []

    def test_user_with_multiple_teams(self):
        u = AuthUser(username="carol", role="member", teams=["Vault", "Prism"])
        resp = user_to_response(u)
        assert set(resp.teams) == {"Vault", "Prism"}

    def test_master_admin_flag(self):
        with patch("app.config.settings.master_admin_usernames", "carol"):
            u = AuthUser(username="carol", role="member", teams=[])
            resp = user_to_response(u)
            assert resp.is_master is True

    def test_non_master_by_default(self):
        u = AuthUser(username="dave", role="member", teams=[])
        resp = user_to_response(u)
        assert resp.is_master is False
