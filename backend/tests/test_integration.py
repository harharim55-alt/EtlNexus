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

from tests.conftest import make_auth_user

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
    """Yield an AsyncClient bound to the app without starting the lifespan."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        ac.app = app  # type: ignore[attr-defined]
        yield ac


@pytest_asyncio.fixture
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with an admin user injected via dependency override."""
    from app.auth import get_current_user

    admin = make_auth_user(role="admin", username="test-admin")
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

    member = make_auth_user(role="member", username="test-member")
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
        response = await client.get("/api/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"

    async def test_health_includes_request_id_header(self, client: AsyncClient):
        """Request ID middleware must inject X-Request-ID on every response."""
        response = await client.get("/api/health")

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
        """Auth config response must contain the fields the SPA OIDC client needs."""
        response = await client.get("/api/auth/config")
        body = response.json()
        assert {"sso_enabled", "issuer_url", "client_id", "audience", "ai_greeting"} <= body.keys()

    async def test_auth_config_sso_disabled_by_default(self, client: AsyncClient):
        """In the test environment SSO is disabled — sso_enabled must be False."""
        response = await client.get("/api/auth/config")
        body = response.json()
        assert body["sso_enabled"] is False


# ---------------------------------------------------------------------------
# Data product list — requires auth
# ---------------------------------------------------------------------------


class TestDataProductList:
    async def test_list_with_mocked_admin(self, admin_client: AsyncClient):
        """Data product list returns the expected shape with a mocked admin."""
        from app.schemas.data_product import DataProductListResponse
        from app.services.data_product_service import DataProductService

        with patch.object(
            DataProductService,
            "list_products",
            new_callable=AsyncMock,
            return_value=DataProductListResponse(items=[], total=0),
        ):
            response = await admin_client.get("/api/data-products")

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] == 0

    async def test_list_member_user(self, member_client: AsyncClient):
        """Data product list must work for regular members."""
        from app.schemas.data_product import DataProductListResponse
        from app.services.data_product_service import DataProductService

        with patch.object(
            DataProductService,
            "list_products",
            new_callable=AsyncMock,
            return_value=DataProductListResponse(items=[], total=0),
        ):
            response = await member_client.get("/api/data-products")

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Data product detail
# ---------------------------------------------------------------------------


class TestDataProductDetail:
    async def test_detail_404_unknown_id(self, admin_client: AsyncClient):
        """GET /api/data-products/{unknown_id} must return 404."""
        from app.services.data_product_service import DataProductService

        with patch.object(
            DataProductService,
            "get_product_detail_for_user",
            new_callable=AsyncMock,
            return_value=None,
        ):
            unknown_id = uuid.uuid4()
            response = await admin_client.get(f"/api/data-products/{unknown_id}")

        assert response.status_code == 404
        body = response.json()
        assert "detail" in body

    async def test_detail_invalid_uuid_returns_422(self, admin_client: AsyncClient):
        """GET /api/data-products/{non-uuid} must return 422 (validation error)."""
        response = await admin_client.get("/api/data-products/not-a-uuid")
        assert response.status_code == 422
