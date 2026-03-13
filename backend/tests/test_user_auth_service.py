"""Tests for UserAuthService — JIT provisioning, team sync, and caching."""

import uuid
from collections import OrderedDict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.user_auth_service import (
    UserAuthService,
    _CACHE_MAX_SIZE,
    _CACHE_TTL_SECONDS,
    _PROVISION_CACHE,
    _claims_cache_key,
    _evict_stale_entries,
)
from tests.conftest import make_team, make_user, make_user_team


@pytest.fixture(autouse=True)
def clear_provision_cache():
    """Ensure the provision cache is empty for each test."""
    _PROVISION_CACHE.clear()
    yield
    _PROVISION_CACHE.clear()


# ---------------------------------------------------------------------------
# Pure helper tests
# ---------------------------------------------------------------------------


class TestClaimsCacheKey:
    def test_deterministic(self):
        claims = {"sub": "user1", "email": "a@b.com"}
        k1 = _claims_cache_key(claims)
        k2 = _claims_cache_key(claims)
        assert k1 == k2

    def test_different_sub_different_key(self):
        c1 = {"sub": "user1", "email": "a@b.com"}
        c2 = {"sub": "user2", "email": "a@b.com"}
        assert _claims_cache_key(c1) != _claims_cache_key(c2)

    def test_different_email_different_key(self):
        c1 = {"sub": "user1", "email": "a@b.com"}
        c2 = {"sub": "user1", "email": "x@y.com"}
        assert _claims_cache_key(c1) != _claims_cache_key(c2)

    def test_different_groups_different_key(self):
        c1 = {"sub": "user1", "groups": ["/Dagger"]}
        c2 = {"sub": "user1", "groups": ["/Vault"]}
        assert _claims_cache_key(c1) != _claims_cache_key(c2)

    def test_different_roles_different_key(self):
        c1 = {"sub": "user1", "realm_access": {"roles": ["admin"]}}
        c2 = {"sub": "user1", "realm_access": {"roles": ["member"]}}
        assert _claims_cache_key(c1) != _claims_cache_key(c2)

    def test_missing_fields_still_works(self):
        key = _claims_cache_key({})
        assert isinstance(key, str)
        assert ":" in key


class TestEvictStaleEntries:
    def test_removes_expired(self):
        import time
        # Insert with a timestamp that is older than TTL
        _PROVISION_CACHE["old"] = (uuid.uuid4(), time.monotonic() - _CACHE_TTL_SECONDS - 10)
        _PROVISION_CACHE["fresh"] = (uuid.uuid4(), time.monotonic())
        _evict_stale_entries()
        assert "old" not in _PROVISION_CACHE
        assert "fresh" in _PROVISION_CACHE

    def test_lru_evicts_oldest_when_over_capacity(self):
        import time
        now = time.monotonic()
        for i in range(_CACHE_MAX_SIZE + 50):
            _PROVISION_CACHE[f"key_{i}"] = (uuid.uuid4(), now)
        _evict_stale_entries()
        # LRU eviction removes oldest 10%, so size drops below max
        assert len(_PROVISION_CACHE) <= _CACHE_MAX_SIZE


# ---------------------------------------------------------------------------
# UserAuthService tests
# ---------------------------------------------------------------------------


class TestGetOrCreateDefaultUser:
    async def test_returns_existing_default_user(self, mock_session):
        user = make_user(role="admin", sub="default-admin")
        user_repo = AsyncMock()
        user_repo.get_by_sub.return_value = user

        service = UserAuthService(mock_session)
        service._user_repo = user_repo

        result = await service.get_or_create_default_user()
        assert result.sub == "default-admin"
        assert result.role == "admin"

    async def test_creates_default_user_when_absent(self, mock_session):
        user_repo = AsyncMock()
        user_repo.get_by_sub.side_effect = [None, make_user(role="admin", sub="default-admin")]

        service = UserAuthService(mock_session)
        service._user_repo = user_repo

        result = await service.get_or_create_default_user()
        assert result.sub == "default-admin"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()


class TestUpsertFromClaims:
    @patch("app.services.user_auth_service.oidc_client")
    async def test_cache_hit_returns_user(self, mock_oidc, mock_session):
        import time

        user = make_user()
        user_repo = AsyncMock()
        user_repo.get_by_id.return_value = user

        service = UserAuthService(mock_session)
        service._user_repo = user_repo

        claims = {"sub": "test-sub", "email": "test@test.com"}
        cache_key = _claims_cache_key(claims)
        _PROVISION_CACHE[cache_key] = (user.id, time.monotonic())

        result = await service.upsert_from_claims(claims)
        assert result.id == user.id
        # Should NOT have done full provisioning
        user_repo.upsert_from_sso.assert_not_awaited()

    @patch("app.services.user_auth_service.oidc_client")
    async def test_cache_miss_does_full_provision(self, mock_oidc, mock_session):
        mock_oidc.extract_role.return_value = "member"
        mock_oidc.extract_groups.return_value = ["Dagger"]

        user = make_user()
        user_repo = AsyncMock()
        user_repo.upsert_from_sso.return_value = user
        user_repo.get_by_sub.return_value = user
        user.team_memberships = []

        team = make_team(name="Dagger")
        team_repo = AsyncMock()
        team_repo.get_or_create_many.return_value = [team]

        service = UserAuthService(mock_session)
        service._user_repo = user_repo
        service._team_repo = team_repo

        claims = {"sub": "new-user", "email": "new@test.com"}
        result = await service.upsert_from_claims(claims)
        assert result is not None
        user_repo.upsert_from_sso.assert_awaited_once()

    @patch("app.services.user_auth_service.oidc_client")
    async def test_expired_cache_triggers_full_provision(self, mock_oidc, mock_session):
        import time

        mock_oidc.extract_role.return_value = "member"
        mock_oidc.extract_groups.return_value = []

        user = make_user()
        user_repo = AsyncMock()
        user_repo.upsert_from_sso.return_value = user
        user_repo.get_by_sub.return_value = user
        user.team_memberships = []

        team_repo = AsyncMock()
        team_repo.get_or_create_many.return_value = []

        service = UserAuthService(mock_session)
        service._user_repo = user_repo
        service._team_repo = team_repo

        claims = {"sub": "cached-user", "email": "cached@test.com"}
        cache_key = _claims_cache_key(claims)
        # Insert expired entry (older than TTL)
        _PROVISION_CACHE[cache_key] = (user.id, time.monotonic() - _CACHE_TTL_SECONDS - 10)

        await service.upsert_from_claims(claims)
        user_repo.upsert_from_sso.assert_awaited_once()


class TestFullProvision:
    @patch("app.services.user_auth_service.oidc_client")
    async def test_adds_new_team_memberships(self, mock_oidc, mock_session):
        mock_oidc.extract_role.return_value = "member"
        mock_oidc.extract_groups.return_value = ["Dagger", "Vault"]

        user = make_user()
        user.team_memberships = []

        user_repo = AsyncMock()
        user_repo.upsert_from_sso.return_value = user
        user_repo.get_by_sub.return_value = user

        team_dagger = make_team(name="Dagger")
        team_vault = make_team(name="Vault")
        team_repo = AsyncMock()
        team_repo.get_or_create_many.return_value = [team_dagger, team_vault]

        service = UserAuthService(mock_session)
        service._user_repo = user_repo
        service._team_repo = team_repo

        claims = {"sub": "test", "email": "t@t.com"}
        await service._full_provision(claims)

        # Should add 2 memberships
        assert mock_session.add.call_count == 2

    @patch("app.services.user_auth_service.oidc_client")
    async def test_removes_stale_memberships(self, mock_oidc, mock_session):
        mock_oidc.extract_role.return_value = "member"
        mock_oidc.extract_groups.return_value = ["Dagger"]  # Only Dagger now

        team_dagger = make_team(name="Dagger")
        team_vault = make_team(name="Vault")

        user = make_user()
        stale_membership = make_user_team(user, team_vault)
        user.team_memberships = [stale_membership]

        user_repo = AsyncMock()
        user_repo.upsert_from_sso.return_value = user
        user_repo.get_by_sub.return_value = user

        team_repo = AsyncMock()
        team_repo.get_or_create_many.return_value = [team_dagger]

        service = UserAuthService(mock_session)
        service._user_repo = user_repo
        service._team_repo = team_repo

        claims = {"sub": "test", "email": "t@t.com"}
        await service._full_provision(claims)

        # Stale membership (Vault) should be deleted
        mock_session.delete.assert_awaited_once_with(stale_membership)
