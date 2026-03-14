"""Tests for Pydantic schema validation.

Verifies request/response schemas enforce constraints and serialize correctly.
"""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.auth import (
    AuthConfigResponse,
    RoleUpdateRequest,
    TeamMembershipResponse,
    UserResponse,
)
from app.schemas.pipeline import (
    JoinSuggestion,
    JoinSuggestionsResponse,
    PipelineDetail,
    PipelineListItem,
    PipelineListResponse,
    PipelineUpdateRequest,
    PipelineUpdateResponse,
)
from app.schemas.team import TeamDetailResponse, TeamMemberInfo, TeamResponse
from app.schemas.visibility import VisibilityGrantRequest, VisibilityGrantResponse

# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class TestRoleUpdateRequest:
    def test_valid_roles(self):
        for role in ("admin", "member", "viewer"):
            req = RoleUpdateRequest(role=role)
            assert req.role == role

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            RoleUpdateRequest(role="superuser")

    def test_empty_role_rejected(self):
        with pytest.raises(ValidationError):
            RoleUpdateRequest(role="")


class TestAuthConfigResponse:
    def test_serializes_correctly(self):
        resp = AuthConfigResponse(
            sso_enabled=True,
            issuer_url="http://keycloak:8090/realms/test",
            client_id="app",
            audience="app",
        )
        data = resp.model_dump()
        assert data["sso_enabled"] is True
        assert data["client_id"] == "app"


class TestTeamMembershipResponse:
    def test_from_attributes(self):
        team_id = uuid.uuid4()
        resp = TeamMembershipResponse(
            id=team_id, name="Dagger", role_in_team="member"
        )
        assert resp.id == team_id
        assert resp.name == "Dagger"


class TestUserResponse:
    def test_with_teams(self):
        team = TeamMembershipResponse(id=uuid.uuid4(), name="Vault", role_in_team="member")
        resp = UserResponse(
            id=uuid.uuid4(),
            email="user@test.local",
            display_name="Test User",
            role="admin",
            is_active=True,
            teams=[team],
        )
        assert len(resp.teams) == 1
        assert resp.teams[0].name == "Vault"

    def test_with_empty_teams(self):
        resp = UserResponse(
            id=uuid.uuid4(),
            email="user@test.local",
            display_name="Test User",
            role="member",
            is_active=True,
            teams=[],
        )
        assert resp.teams == []


# ---------------------------------------------------------------------------
# Pipeline schemas
# ---------------------------------------------------------------------------


class TestPipelineListItem:
    def test_defaults(self):
        item = PipelineListItem(id=uuid.uuid4(), name="Test Pipeline")
        assert item.airflow_status == "unknown"
        assert item.success_rate is None
        assert item.team is None

    def test_full_item(self):
        item = PipelineListItem(
            id=uuid.uuid4(),
            name="Switch Port Collector",
            description="Collects switch ports",
            category="Network",
            schedule="daily",
            rows_per_day="5000",
            airflow_status="success",
            success_rate=95.5,
            team="Dagger",
        )
        assert item.team == "Dagger"
        assert item.success_rate == 95.5


class TestPipelineListResponse:
    def test_structure(self):
        items = [PipelineListItem(id=uuid.uuid4(), name="P1")]
        resp = PipelineListResponse(items=items, total=10)
        assert resp.total == 10
        assert len(resp.items) == 1

    def test_empty(self):
        resp = PipelineListResponse(items=[], total=0)
        assert resp.total == 0


class TestPipelineDetail:
    def test_defaults(self):
        detail = PipelineDetail(id=uuid.uuid4(), name="Test")
        assert detail.can_edit is False
        assert detail.fields == []
        assert detail.source_tables == []

    def test_can_edit_flag(self):
        detail = PipelineDetail(id=uuid.uuid4(), name="Test", can_edit=True)
        assert detail.can_edit is True


class TestPipelineUpdateRequest:
    def test_both_optional(self):
        req = PipelineUpdateRequest()
        assert req.description is None
        assert req.documentation is None

    def test_partial_update(self):
        req = PipelineUpdateRequest(description="New description")
        assert req.description == "New description"
        assert req.documentation is None

    def test_full_update(self):
        req = PipelineUpdateRequest(
            description="Desc", documentation="# Docs"
        )
        assert req.documentation == "# Docs"


class TestPipelineUpdateResponse:
    def test_serializes(self):
        resp = PipelineUpdateResponse(
            id=uuid.uuid4(),
            description="Updated",
            last_updated_by="admin",
            last_updated_at=datetime.now(UTC),
        )
        assert resp.description == "Updated"


class TestJoinSuggestion:
    def test_structure(self):
        s = JoinSuggestion(
            pipeline_id=uuid.uuid4(),
            pipeline_name="Other Pipeline",
            shared_fields=["ip_address", "hostname"],
        )
        assert len(s.shared_fields) == 2


class TestJoinSuggestionsResponse:
    def test_empty_matches(self):
        resp = JoinSuggestionsResponse(schema_matches=[])
        assert resp.schema_matches == []


# ---------------------------------------------------------------------------
# Visibility schemas
# ---------------------------------------------------------------------------


class TestVisibilityGrantRequest:
    def test_pipeline_grant(self):
        req = VisibilityGrantRequest(
            grantee_team_id=uuid.uuid4(),
            pipeline_id=uuid.uuid4(),
            grant_level="viewer",
        )
        assert req.source_team_id is None

    def test_team_grant(self):
        req = VisibilityGrantRequest(
            grantee_user_id=uuid.uuid4(),
            source_team_id=uuid.uuid4(),
            grant_level="editor",
        )
        assert req.pipeline_id is None

    def test_default_grant_level(self):
        req = VisibilityGrantRequest(
            grantee_team_id=uuid.uuid4(),
            pipeline_id=uuid.uuid4(),
        )
        assert req.grant_level == "viewer"

    def test_invalid_grant_level(self):
        with pytest.raises(ValidationError):
            VisibilityGrantRequest(
                grantee_team_id=uuid.uuid4(),
                pipeline_id=uuid.uuid4(),
                grant_level="superadmin",
            )


class TestVisibilityGrantResponse:
    def test_serializes_with_names(self):
        resp = VisibilityGrantResponse(
            id=uuid.uuid4(),
            grantee_team_id=uuid.uuid4(),
            grantee_team_name="Dagger",
            pipeline_id=uuid.uuid4(),
            grant_level="editor",
            granted_by="Admin",
            created_at=datetime.now(UTC),
        )
        data = resp.model_dump()
        assert data["grantee_team_name"] == "Dagger"
        assert data["source_team_id"] is None


# ---------------------------------------------------------------------------
# Team schemas
# ---------------------------------------------------------------------------


class TestTeamResponse:
    def test_structure(self):
        resp = TeamResponse(
            id=uuid.uuid4(),
            name="Prism",
            source="sso",
            member_count=5,
        )
        assert resp.member_count == 5


class TestTeamDetailResponse:
    def test_with_members(self):
        member = TeamMemberInfo(
            id=uuid.uuid4(),
            email="user@test.local",
            display_name="User",
            role="member",
            role_in_team="member",
        )
        resp = TeamDetailResponse(
            id=uuid.uuid4(),
            name="Vault",
            source="sso",
            members=[member],
        )
        assert len(resp.members) == 1
