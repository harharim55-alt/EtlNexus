"""Integration tests using httpx.AsyncClient + ASGITransport.

These tests exercise the full FastAPI request/response cycle without a real
database by overriding ``get_current_user`` and related dependencies.
"""

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import make_user

# ---------------------------------------------------------------------------
# App import (deferred so settings are already loaded)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    """Import and return the FastAPI app instance."""
    from app.main import app as _app
    return _app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _override_current_user(user):
    """Return an async callable that yields ``user`` as the current user."""
    async def _dep():
        return user
    return _dep


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(app) -> AsyncGenerator[AsyncClient, None]:
    """Yield an AsyncClient bound to the app without starting the lifespan.

    The underlying ``app`` is accessible via ``client.app`` (set below).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        # Stash the app reference so tests can manipulate dependency_overrides
        ac.app = app  # type: ignore[attr-defined]
        yield ac


@pytest_asyncio.fixture
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with an admin user injected via dependency override."""
    from app.auth import get_current_user

    admin = make_user(role="admin", display_name="Test Admin")
    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def member_client(app) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with a regular member user injected."""
    from app.auth import get_current_user

    member = make_user(role="member", display_name="Test Member")
    app.dependency_overrides[get_current_user] = _override_current_user(member)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Health check — no auth required
# ---------------------------------------------------------------------------

class TestHealthCheck:
    async def test_health_returns_200(self, client: AsyncClient):
        """Health endpoint must respond 200 without authentication."""
        from app.database import get_db_session

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        async def _fake_session():
            yield mock_session

        client.app.dependency_overrides[get_db_session] = _fake_session  # type: ignore[attr-defined]
        with patch("app.routers.health.airflow_client.check_health", new_callable=AsyncMock, return_value=True):
            response = await client.get("/api/health")
        client.app.dependency_overrides.pop(get_db_session, None)  # type: ignore[attr-defined]

        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "services" in body

    async def test_health_includes_request_id_header(self, client: AsyncClient):
        """Request ID middleware must inject X-Request-ID on every response."""
        from app.database import get_db_session

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        async def _fake_session():
            yield mock_session

        client.app.dependency_overrides[get_db_session] = _fake_session  # type: ignore[attr-defined]
        with patch("app.routers.health.airflow_client.check_health", new_callable=AsyncMock, return_value=False):
            response = await client.get("/api/health")
        client.app.dependency_overrides.pop(get_db_session, None)  # type: ignore[attr-defined]

        assert "x-request-id" in response.headers


# ---------------------------------------------------------------------------
# Auth config — public endpoint, no auth required
# ---------------------------------------------------------------------------

class TestAuthConfig:
    async def test_auth_config_returns_200(self, client: AsyncClient):
        """Auth config endpoint must be accessible without a token."""
        response = await client.get("/api/auth/config")
        assert response.status_code == 200

    async def test_auth_config_schema(self, client: AsyncClient):
        """Auth config response must contain the expected fields."""
        response = await client.get("/api/auth/config")
        body = response.json()
        assert "sso_enabled" in body
        assert "issuer_url" in body
        assert "client_id" in body
        assert "audience" in body

    async def test_auth_config_sso_disabled_by_default(self, client: AsyncClient):
        """In test environment SSO is disabled — sso_enabled must be False."""
        response = await client.get("/api/auth/config")
        body = response.json()
        # SSO is off in test settings (settings.sso_enabled defaults to False)
        assert body["sso_enabled"] is False


# ---------------------------------------------------------------------------
# Pipeline list — requires auth
# ---------------------------------------------------------------------------

class TestPipelineList:
    async def test_pipeline_list_with_mocked_user(self, admin_client: AsyncClient):
        """Pipeline list endpoint returns the expected shape with a mocked admin."""
        from app.schemas.pipeline import PipelineListResponse
        from app.services.pipeline_service import PipelineService

        with patch.object(
            PipelineService,
            "list_pipelines",
            new_callable=AsyncMock,
            return_value=PipelineListResponse(items=[], total=0),
        ):
            response = await admin_client.get("/api/pipelines")
        assert response.status_code == 200

    async def test_pipeline_list_returns_list_shape(self, admin_client: AsyncClient):
        """Pipeline list response must contain items and total."""
        from app.schemas.pipeline import PipelineListResponse
        from app.services.pipeline_service import PipelineService

        with patch.object(
            PipelineService,
            "list_pipelines",
            new_callable=AsyncMock,
            return_value=PipelineListResponse(items=[], total=0),
        ):
            response = await admin_client.get("/api/pipelines")

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] == 0

    async def test_pipeline_list_member_user(self, member_client: AsyncClient):
        """Pipeline list must work for regular members."""
        from app.schemas.pipeline import PipelineListResponse
        from app.services.pipeline_service import PipelineService

        with patch.object(
            PipelineService,
            "list_pipelines",
            new_callable=AsyncMock,
            return_value=PipelineListResponse(items=[], total=0),
        ):
            response = await member_client.get("/api/pipelines")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Pipeline detail 404
# ---------------------------------------------------------------------------

class TestPipelineDetail:
    async def test_pipeline_detail_404_unknown_id(self, admin_client: AsyncClient):
        """GET /api/pipelines/{unknown_id} must return 404."""
        from app.services.pipeline_service import PipelineService

        with patch.object(
            PipelineService,
            "get_pipeline_detail_for_user",
            new_callable=AsyncMock,
            return_value=None,
        ):
            unknown_id = uuid.uuid4()
            response = await admin_client.get(f"/api/pipelines/{unknown_id}")

        assert response.status_code == 404
        body = response.json()
        assert "detail" in body

    async def test_pipeline_detail_invalid_uuid_returns_422(self, admin_client: AsyncClient):
        """GET /api/pipelines/{non-uuid} must return 422 (validation error)."""
        response = await admin_client.get("/api/pipelines/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Visibility grants — admin only
# ---------------------------------------------------------------------------

class TestVisibilityGrants:
    async def test_list_grants_requires_admin(self, member_client: AsyncClient):
        """Visibility grants list must be restricted to admins."""
        response = await member_client.get("/api/visibility/grants")
        assert response.status_code == 403

    async def test_list_grants_admin_ok(self, admin_client: AsyncClient):
        """Admin may list visibility grants."""
        from app.services.visibility_service import VisibilityService

        with patch.object(
            VisibilityService,
            "list_grants",
            new_callable=AsyncMock,
            return_value=([], 0),
        ):
            response = await admin_client.get("/api/visibility/grants")

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body

    async def test_create_grant_invalid_body_returns_422(self, admin_client: AsyncClient):
        """Creating a grant with neither pipeline_id nor source_team_id must fail."""
        payload = {
            "grantee_team_id": str(uuid.uuid4()),
            "grant_level": "viewer",
            # Missing: pipeline_id or source_team_id
        }
        response = await admin_client.post("/api/visibility/grants", json=payload)
        assert response.status_code == 422

    async def test_create_grant_both_target_fields_returns_422(self, admin_client: AsyncClient):
        """Specifying both pipeline_id and source_team_id must fail validation."""
        payload = {
            "pipeline_id": str(uuid.uuid4()),
            "source_team_id": str(uuid.uuid4()),
            "grantee_team_id": str(uuid.uuid4()),
            "grant_level": "viewer",
        }
        response = await admin_client.post("/api/visibility/grants", json=payload)
        assert response.status_code == 422

    async def test_create_grant_non_admin_returns_403(self, member_client: AsyncClient):
        """Non-admin users must not be able to create visibility grants."""
        payload = {
            "pipeline_id": str(uuid.uuid4()),
            "grantee_team_id": str(uuid.uuid4()),
            "grant_level": "viewer",
        }
        response = await member_client.post("/api/visibility/grants", json=payload)
        assert response.status_code == 403
