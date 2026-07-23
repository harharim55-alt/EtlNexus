"""Tests for OIDCClient — OIDC claims extraction helpers.

Tests extract_groups (a pure method) and the TLS verify resolver, neither of
which needs network or JWKS infrastructure. SSO roles are not consulted by the
app (admin status comes from MASTER_ADMIN_USERNAMES).
"""

from unittest.mock import patch

import pytest

from app.integrations.oidc_client import OIDCClient, _resolve_verify


@pytest.fixture
def client():
    return OIDCClient()


class TestResolveVerify:
    def test_verify_off_returns_false(self):
        with patch("app.integrations.oidc_client.settings") as s:
            s.oidc_verify_ssl = False
            s.oidc_ca_bundle = ""
            assert _resolve_verify() is False

    def test_verify_off_ignores_ca_bundle(self):
        # The footgun fix: verify=false must win and NOT try to load a CA path.
        with patch("app.integrations.oidc_client.settings") as s:
            s.oidc_verify_ssl = False
            s.oidc_ca_bundle = "/certs/does-not-exist.pem"
            assert _resolve_verify() is False

    def test_verify_on_with_ca_bundle_returns_path(self):
        with patch("app.integrations.oidc_client.settings") as s:
            s.oidc_verify_ssl = True
            s.oidc_ca_bundle = "/certs/idp-ca.pem"
            assert _resolve_verify() == "/certs/idp-ca.pem"

    def test_verify_on_without_ca_bundle_returns_true(self):
        with patch("app.integrations.oidc_client.settings") as s:
            s.oidc_verify_ssl = True
            s.oidc_ca_bundle = ""
            assert _resolve_verify() is True


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


class TestExtractGroupsMapping:
    def test_renames_and_drops_unmapped_when_map_present(self, client):
        # Non-empty map is an allow-list: mapped groups are renamed, others dropped.
        with patch("app.integrations.oidc_client.settings") as s:
            s.sso_groups_claim = "groups"
            s.sso_group_map = {"kc-dagger": "Dagger"}
            result = client.extract_groups({"groups": ["/kc-dagger", "Other"]})
            assert result == ["Dagger"]

    def test_map_key_matches_with_leading_slash(self, client):
        with patch("app.integrations.oidc_client.settings") as s:
            s.sso_groups_claim = "groups"
            s.sso_group_map = {"/vault-grp": "Vault"}
            result = client.extract_groups({"groups": ["/vault-grp"]})
            assert result == ["Vault"]

    def test_empty_map_passes_through_stripped(self, client):
        with patch("app.integrations.oidc_client.settings") as s:
            s.sso_groups_claim = "groups"
            s.sso_group_map = {}
            result = client.extract_groups({"groups": ["/Prism"]})
            assert result == ["Prism"]
