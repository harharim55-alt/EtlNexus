"""Shared test fixtures for the EtlNexus backend test suite."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.pipeline import Pipeline
from app.models.team import Team
from app.models.user import User
from app.models.user_team import UserTeam
from app.models.visibility_grant import VisibilityGrant

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_user(
    *,
    role: str = "member",
    team_memberships: list | None = None,
    sub: str | None = None,
    email: str | None = None,
    display_name: str | None = None,
) -> User:
    """Create a User ORM-like object for testing."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.sub = sub or f"user-{user.id.hex[:8]}"
    user.email = email or f"{user.sub}@test.local"
    user.display_name = display_name or user.sub
    user.role = role
    user.is_active = True
    user.last_login = datetime.now(UTC)
    user.team_memberships = team_memberships or []
    return user


def make_team(*, name: str = "Dagger", source: str = "sso") -> Team:
    """Create a Team ORM-like object for testing."""
    team = MagicMock(spec=Team)
    team.id = uuid.uuid4()
    team.name = name
    team.description = None
    team.source = source
    team.members = []
    return team


def make_user_team(user: User, team: Team, role_in_team: str = "member") -> UserTeam:
    """Create a UserTeam membership linking user and team."""
    ut = MagicMock(spec=UserTeam)
    ut.id = uuid.uuid4()
    ut.user_id = user.id
    ut.team_id = team.id
    ut.user = user
    ut.team = team
    ut.role_in_team = role_in_team
    return ut


def make_pipeline(
    *,
    name: str = "Switch Port Collector",
    task_id: str = "SwitchPortCollector",
    team: str | None = None,
    team_id: uuid.UUID | None = None,
    category: str = "Network Infrastructure",
) -> Pipeline:
    """Create a Pipeline ORM-like object for testing."""
    pipeline = MagicMock(spec=Pipeline)
    pipeline.id = uuid.uuid4()
    pipeline.name = name
    pipeline.task_id = task_id
    pipeline.description = f"Test pipeline {name}"
    pipeline.category = category
    pipeline.schedule = "daily"
    pipeline.rows_per_day = "10000"
    pipeline.documentation = None
    pipeline.last_updated_by = None
    pipeline.last_updated_at = None
    pipeline.created_at = datetime.now(UTC)
    pipeline.updated_at = datetime.now(UTC)
    pipeline.team = team
    pipeline.team_id = team_id
    pipeline.fields = []
    pipeline.airflow_status = None
    return pipeline


def make_grant(
    *,
    grantee_team_id: uuid.UUID | None = None,
    grantee_user_id: uuid.UUID | None = None,
    pipeline_id: uuid.UUID | None = None,
    source_team_id: uuid.UUID | None = None,
    grant_level: str = "viewer",
    granted_by: str = "Admin",
) -> VisibilityGrant:
    """Create a VisibilityGrant ORM-like object for testing."""
    grant = MagicMock(spec=VisibilityGrant)
    grant.id = uuid.uuid4()
    grant.grantee_team_id = grantee_team_id
    grant.grantee_user_id = grantee_user_id
    grant.pipeline_id = pipeline_id
    grant.source_team_id = source_team_id
    grant.grant_level = grant_level
    grant.granted_by = granted_by
    grant.created_at = datetime.now(UTC)
    grant.grantee_team = None
    grant.grantee_user = None
    grant.source_team = None
    return grant


# ---------------------------------------------------------------------------
# Async session mock
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """Return a mock AsyncSession with common methods pre-configured."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.expire = MagicMock()
    session.begin_nested = MagicMock()
    # Make begin_nested work as async context manager
    nested_ctx = AsyncMock()
    nested_ctx.__aenter__ = AsyncMock()
    nested_ctx.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested.return_value = nested_ctx
    return session
