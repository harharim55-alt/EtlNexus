"""Tests for auth schema helper functions (user_to_response)."""

import uuid
from unittest.mock import MagicMock

import pytest

from app.models.user_team import UserTeam
from app.schemas.auth import user_to_response
from tests.conftest import make_team, make_user, make_user_team


class TestUserToResponse:
    def test_user_with_teams(self):
        team = make_team(name="Dagger")
        user = make_user(role="member")
        ut = make_user_team(user, team)
        user.team_memberships = [ut]

        resp = user_to_response(user)
        assert resp.role == "member"
        assert len(resp.teams) == 1
        assert resp.teams[0].name == "Dagger"

    def test_user_with_no_teams(self):
        user = make_user(role="admin")
        user.team_memberships = []
        resp = user_to_response(user)
        assert resp.teams == []

    def test_user_with_none_memberships(self):
        user = make_user()
        user.team_memberships = None
        resp = user_to_response(user)
        assert resp.teams == []

    def test_filters_non_userteam_objects(self):
        user = make_user()
        # Simulate a relationship that includes non-UserTeam objects
        user.team_memberships = [MagicMock(), MagicMock()]
        resp = user_to_response(user)
        assert resp.teams == []

    def test_user_with_multiple_teams(self):
        user = make_user(role="member")
        team_a = make_team(name="Vault")
        team_b = make_team(name="Prism")
        ut_a = make_user_team(user, team_a)
        ut_b = make_user_team(user, team_b)
        user.team_memberships = [ut_a, ut_b]

        resp = user_to_response(user)
        assert len(resp.teams) == 2
        names = {t.name for t in resp.teams}
        assert names == {"Vault", "Prism"}
