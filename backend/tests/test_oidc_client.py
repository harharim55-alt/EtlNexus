"""Tests for OIDCClient — OIDC claims extraction helpers.

Tests extract_groups and extract_role which are pure methods that don't
need network or JWKS infrastructure.
"""

from unittest.mock import patch

import pytest

from app.integrations.oidc_client import OIDCClient


@pytest.fixture
def client():
    return OIDCClient()


class TestExtractGroups:
    def test_keycloak_slash_prefixed_groups(self, client):
        claims = {"groups": ["/Dagger", "/Vault", "/Prism"]}
        result = client.extract_groups(claims)
        assert result == ["Dagger", "Vault", "Prism"]

    def test_flat_group_names(self, client):
        claims = {"groups": ["Dagger", "Vault"]}
        result = client.extract_groups(claims)
        assert result == ["Dagger", "Vault"]

    def test_empty_groups(self, client):
        assert client.extract_groups({"groups": []}) == []

    def test_missing_groups_claim(self, client):
        assert client.extract_groups({}) == []

    def test_non_list_groups_wrapped(self, client):
        claims = {"groups": "/Dagger"}
        result = client.extract_groups(claims)
        assert result == ["Dagger"]

    def test_non_string_elements_filtered(self, client):
        claims = {"groups": ["/Dagger", 42, None, "/Vault"]}
        result = client.extract_groups(claims)
        assert result == ["Dagger", "Vault"]


class TestExtractRole:
    def test_admin_role_from_realm_access(self, client):
        claims = {"realm_access": {"roles": ["admin", "member"]}}
        result = client.extract_role(claims)
        assert result == "admin"

    def test_member_role(self, client):
        claims = {"realm_access": {"roles": ["member"]}}
        result = client.extract_role(claims)
        assert result == "member"

    def test_viewer_role(self, client):
        claims = {"realm_access": {"roles": ["viewer"]}}
        result = client.extract_role(claims)
        assert result == "viewer"

    def test_unknown_role_defaults_to_member(self, client):
        claims = {"realm_access": {"roles": ["custom_role"]}}
        result = client.extract_role(claims)
        assert result == "member"

    def test_missing_realm_access_defaults_to_member(self, client):
        result = client.extract_role({})
        assert result == "member"

    def test_empty_roles_list_defaults_to_member(self, client):
        claims = {"realm_access": {"roles": []}}
        result = client.extract_role(claims)
        assert result == "member"

    def test_string_role_value(self, client):
        # If the claim path resolves to a string instead of list
        with patch("app.integrations.oidc_client.settings") as mock_settings:
            mock_settings.sso_role_claim = "role"
            mock_settings.sso_admin_role = "admin"
            result = client.extract_role({"role": "admin"})
            assert result == "admin"

    def test_string_invalid_role_defaults(self, client):
        with patch("app.integrations.oidc_client.settings") as mock_settings:
            mock_settings.sso_role_claim = "role"
            mock_settings.sso_admin_role = "admin"
            result = client.extract_role({"role": "superuser"})
            assert result == "member"

    def test_nested_path_traversal(self, client):
        claims = {"realm_access": {"roles": ["viewer", "member"]}}
        result = client.extract_role(claims)
        # viewer is a valid role
        assert result == "viewer"

    def test_admin_prioritized_over_others(self, client):
        claims = {"realm_access": {"roles": ["viewer", "admin", "member"]}}
        result = client.extract_role(claims)
        assert result == "admin"
