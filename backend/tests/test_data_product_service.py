"""Tests for DataProductService — fqn parsing, can_edit, detail, duplicate names."""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.cache import product_list_cache
from app.services.data_product_service import (
    DataProductService,
    DuplicateProductNameError,
    _can_edit,
    parse_fqn,
)
from tests.conftest import make_product


@pytest.fixture(autouse=True)
def clear_cache():
    product_list_cache.clear()
    yield
    product_list_cache.clear()


@pytest.fixture
def repo():
    return AsyncMock()


@pytest.fixture
def service(repo):
    return DataProductService(repo)


class TestParseFqn:
    def test_simple(self):
        ref = parse_fqn("vault.logins")
        assert ref.namespace == "vault"
        assert ref.table_name == "logins"

    def test_multilevel_namespace_splits_on_last_dot(self):
        ref = parse_fqn("a.b.c")
        assert ref.namespace == "a.b"
        assert ref.table_name == "c"

    def test_no_dot(self):
        ref = parse_fqn("logins")
        assert ref.namespace == ""
        assert ref.table_name == "logins"


class TestCanEdit:
    def test_master_edits_anything(self):
        assert _can_edit("Vault", set(), "viewer", is_master=True) is True

    def test_viewer_blocked(self):
        assert _can_edit(None, {"Vault"}, "viewer", is_master=False) is False

    def test_unassigned_editable_only_by_creator(self):
        # Team-less product: editable by its creator, not by other non-viewers.
        assert _can_edit(None, set(), "member", is_master=False, created_by="alice", username="alice") is True
        assert _can_edit(None, set(), "member", is_master=False, created_by="alice", username="bob") is False
        assert _can_edit(None, set(), "member", is_master=False, created_by=None, username="bob") is False

    def test_team_member_case_insensitive(self):
        assert _can_edit("vault", {"Vault"}, "member", is_master=False) is True

    def test_non_member_blocked(self):
        assert _can_edit("Dagger", {"Prism"}, "member", is_master=False) is False


class TestGetProductDetail:
    async def test_parses_tables_and_renders_snippet(self, service, repo):
        repo.get_by_id.return_value = make_product(name="Login Events", tables=["vault.logins", "prism.events"])
        detail = await service.get_product_detail(uuid.uuid4())
        assert {(t.namespace, t.table_name) for t in detail.tables} == {
            ("vault", "logins"),
            ("prism", "events"),
        }
        assert detail.default_import_snippet  # rendered from the env template

    async def test_missing_returns_none(self, service, repo):
        repo.get_by_id.return_value = None
        assert await service.get_product_detail(uuid.uuid4()) is None

    async def test_can_edit_set_for_user(self, service, repo):
        repo.get_by_id.return_value = make_product(team="Vault")
        detail = await service.get_product_detail_for_user(
            uuid.uuid4(), user_teams={"Vault"}, user_role="member", is_master=False
        )
        assert detail.can_edit is True


class TestCreateProduct:
    async def test_duplicate_name_raises(self, service, repo):
        repo.create.side_effect = IntegrityError("stmt", {}, Exception("dup"))
        with pytest.raises(DuplicateProductNameError):
            await service.create_product(
                name="dupe",
                description=None,
                documentation=None,
                team="Vault",
                schedule_type=None,
                created_by="bob",
                tables=["vault.logins"],
            )
        repo.session.rollback.assert_awaited()
