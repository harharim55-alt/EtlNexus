"""Shared test fixtures for the EtlNexus backend test suite."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.auth import AuthUser
from app.models.data_product import DataProduct

# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def make_auth_user(
    *,
    role: str = "member",
    teams: list[str] | None = None,
    username: str | None = None,
    email: str | None = None,
) -> AuthUser:
    """Create a transient AuthUser for testing."""
    username = username or "tester"
    return AuthUser(
        username=username,
        email=email or f"{username}@test.local",
        role=role,
        teams=teams or [],
    )


def make_product(
    *,
    name: str = "Login Events",
    team: str | None = None,
    tables: list[str] | None = None,
    description: str | None = None,
    schedule_type: str | None = "daily",
    created_by: str | None = None,
) -> DataProduct:
    """Create a DataProduct ORM-like mock for testing."""
    product = MagicMock(spec=DataProduct)
    product.id = uuid.uuid4()
    product.name = name
    product.description = description if description is not None else f"Test product {name}"
    product.documentation = None
    product.team = team
    product.tables = tables if tables is not None else []
    product.schedule_type = schedule_type
    product.created_by = created_by
    product.last_updated_by = None
    product.last_updated_at = None
    product.created_at = datetime.now(UTC)
    product.updated_at = datetime.now(UTC)
    return product


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
    return session
