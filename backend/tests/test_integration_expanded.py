"""Expanded integration tests — new endpoint groups not covered by test_integration.py.

Tests exercise the full FastAPI request/response cycle using httpx.AsyncClient +
ASGITransport with service-level mocks via dependency_overrides or patch.object.
"""

import uuid
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from tests.conftest import make_pipeline, make_team, make_user

# ---------------------------------------------------------------------------
# App fixture (module-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    """Import and return the FastAPI app instance."""
    from app.main import app as _app
    return _app


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------


def _override_current_user(user):
    async def _dep():
        return user
    return _dep


def _override_require_role(user):
    """Factory that returns a callable suitable for require_role override."""
    def _factory(*_args, **_kwargs):
        async def _dep():
            return user
        return _dep
    return _factory


# ---------------------------------------------------------------------------
# Client fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def admin_client(app) -> AsyncGenerator[AsyncClient, None]:
    from app.auth import get_current_user

    admin = make_user(role="admin", display_name="Integration Admin")
    app.dependency_overrides[get_current_user] = _override_current_user(admin)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def member_client(app) -> AsyncGenerator[AsyncClient, None]:
    from app.auth import get_current_user

    member = make_user(role="member", display_name="Integration Member")
    app.dependency_overrides[get_current_user] = _override_current_user(member)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# TestLineageEndpoint
# ---------------------------------------------------------------------------


class TestLineageEndpoint:
    async def test_lineage_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_lineage_repo, get_pipeline_repo

        pipeline = make_pipeline()

        mock_pipeline_repo = AsyncMock()
        mock_pipeline_repo.get_by_id.return_value = pipeline

        mock_lineage_repo = AsyncMock()
        mock_lineage_repo.get_by_pipeline_id.return_value = {
            "reads_from": [],
            "writes_to": [],
        }

        app.dependency_overrides[get_pipeline_repo] = lambda: mock_pipeline_repo
        app.dependency_overrides[get_lineage_repo] = lambda: mock_lineage_repo

        response = await admin_client.get(f"/api/pipelines/{pipeline.id}/lineage")

        app.dependency_overrides.pop(get_pipeline_repo, None)
        app.dependency_overrides.pop(get_lineage_repo, None)

        assert response.status_code == 200
        body = response.json()
        assert "nodes" in body
        assert "edges" in body
        assert "source_tables" in body
        assert "destination_tables" in body

    async def test_lineage_404_for_unknown_pipeline(self, admin_client: AsyncClient, app):
        from app.dependencies import get_lineage_repo, get_pipeline_repo

        mock_pipeline_repo = AsyncMock()
        mock_pipeline_repo.get_by_id.return_value = None

        mock_lineage_repo = AsyncMock()

        app.dependency_overrides[get_pipeline_repo] = lambda: mock_pipeline_repo
        app.dependency_overrides[get_lineage_repo] = lambda: mock_lineage_repo

        response = await admin_client.get(f"/api/pipelines/{uuid.uuid4()}/lineage")

        app.dependency_overrides.pop(get_pipeline_repo, None)
        app.dependency_overrides.pop(get_lineage_repo, None)

        assert response.status_code == 404

    async def test_lineage_with_source_and_destination_tables(
        self, admin_client: AsyncClient, app
    ):
        from app.dependencies import get_lineage_repo, get_pipeline_repo

        pipeline = make_pipeline(name="Switch Port Collector")

        source_edge = MagicMock()
        source_edge.source_table = "raw_switch_data"
        source_edge.source_pipeline_id = None
        source_edge.source_pipeline = None
        source_edge.edge_type = "reads"

        target_edge = MagicMock()
        target_edge.target_table = "switch_port_metrics"
        target_edge.target_pipeline_id = None
        target_edge.target_pipeline = None
        target_edge.edge_type = "writes"

        mock_pipeline_repo = AsyncMock()
        mock_pipeline_repo.get_by_id.return_value = pipeline

        mock_lineage_repo = AsyncMock()
        mock_lineage_repo.get_by_pipeline_id.return_value = {
            "reads_from": [source_edge],
            "writes_to": [target_edge],
        }

        app.dependency_overrides[get_pipeline_repo] = lambda: mock_pipeline_repo
        app.dependency_overrides[get_lineage_repo] = lambda: mock_lineage_repo

        response = await admin_client.get(f"/api/pipelines/{pipeline.id}/lineage")

        app.dependency_overrides.pop(get_pipeline_repo, None)
        app.dependency_overrides.pop(get_lineage_repo, None)

        assert response.status_code == 200
        body = response.json()
        assert "raw_switch_data" in body["source_tables"]
        assert "switch_port_metrics" in body["destination_tables"]


# ---------------------------------------------------------------------------
# TestTopologyEndpoint
# ---------------------------------------------------------------------------


class TestTopologyEndpoint:
    async def test_topology_returns_200(self, admin_client: AsyncClient, app):
        from app.database import get_db_session
        from app.schemas.topology import TopologyGraph
        from app.services.topology_service import TopologyService

        pipeline = make_pipeline()

        mock_result = TopologyGraph(
            pipeline_task_id=pipeline.task_id,
            pipeline_status="success",
            dag_ids=[],
            upstream_needs=[],
            upstream_prefers=[],
            upstream_bouncers=[],
            downstream=[],
        )

        mock_session = AsyncMock()

        async def _fake_session():
            yield mock_session

        app.dependency_overrides[get_db_session] = _fake_session

        with patch.object(
            TopologyService,
            "build_pipeline_topology",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await admin_client.get(f"/api/pipelines/{pipeline.id}/topology")

        app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == 200
        body = response.json()
        assert "pipeline_task_id" in body
        assert "upstream_needs" in body
        assert "downstream" in body

    async def test_topology_404_for_unknown_pipeline(self, admin_client: AsyncClient, app):
        from app.database import get_db_session
        from app.services.topology_service import TopologyService

        mock_session = AsyncMock()

        async def _fake_session():
            yield mock_session

        app.dependency_overrides[get_db_session] = _fake_session

        with patch.object(
            TopologyService,
            "build_pipeline_topology",
            new_callable=AsyncMock,
            return_value=None,
        ):
            response = await admin_client.get(f"/api/pipelines/{uuid.uuid4()}/topology")

        app.dependency_overrides.pop(get_db_session, None)

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestResourcesEndpoint
# ---------------------------------------------------------------------------


class TestResourcesEndpoint:
    async def test_resources_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_resource_service
        from app.schemas.resources import ActualUsage, ResourceMetricsResponse
        from app.services.resource_service import ResourceService

        pipeline = make_pipeline()
        mock_result = ResourceMetricsResponse(
            run_count=5,
            success_rate=80.0,
            resource_configs=[],
            recent_runs=[],
            actual_usage=ActualUsage(),
            capacity=[],
        )

        mock_service = AsyncMock(spec=ResourceService)
        mock_service.get_resource_metrics.return_value = mock_result

        app.dependency_overrides[get_resource_service] = lambda: mock_service

        response = await admin_client.get(f"/api/pipelines/{pipeline.id}/resources")

        app.dependency_overrides.pop(get_resource_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "run_count" in body
        assert "resource_configs" in body
        assert "actual_usage" in body

    async def test_resources_404_for_unknown_pipeline(self, admin_client: AsyncClient, app):
        from app.dependencies import get_resource_service
        from app.services.resource_service import ResourceService

        mock_service = AsyncMock(spec=ResourceService)
        mock_service.get_resource_metrics.return_value = None

        app.dependency_overrides[get_resource_service] = lambda: mock_service

        response = await admin_client.get(f"/api/pipelines/{uuid.uuid4()}/resources")

        app.dependency_overrides.pop(get_resource_service, None)

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestBouncerEndpoints
# ---------------------------------------------------------------------------


class TestBouncerEndpoints:
    async def test_list_bouncers_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_bouncer_service
        from app.schemas.bouncer import BouncerListResponse
        from app.services.bouncer_service import BouncerService

        mock_result = BouncerListResponse(bouncers=[], teams=["Dagger", "Vault"])
        mock_service = AsyncMock(spec=BouncerService)
        mock_service.get_all_bouncers.return_value = mock_result

        app.dependency_overrides[get_bouncer_service] = lambda: mock_service

        response = await admin_client.get("/api/bouncers")

        app.dependency_overrides.pop(get_bouncer_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "bouncers" in body
        assert "teams" in body

    async def test_list_bouncers_with_team_filter(self, admin_client: AsyncClient, app):
        from app.dependencies import get_bouncer_service
        from app.schemas.bouncer import BouncerListResponse
        from app.services.bouncer_service import BouncerService

        mock_result = BouncerListResponse(bouncers=[], teams=["Dagger"])
        mock_service = AsyncMock(spec=BouncerService)
        mock_service.get_all_bouncers.return_value = mock_result

        app.dependency_overrides[get_bouncer_service] = lambda: mock_service

        response = await admin_client.get("/api/bouncers?team=Dagger")

        app.dependency_overrides.pop(get_bouncer_service, None)

        assert response.status_code == 200
        mock_service.get_all_bouncers.assert_awaited_once_with(team="Dagger")

    async def test_bouncer_topology_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_bouncer_service
        from app.schemas.bouncer import BouncerTopologyResponse
        from app.services.bouncer_service import BouncerService

        mock_result = BouncerTopologyResponse(
            selected_bouncers=["SwitchBouncer"],
            downstream_etls=[],
            total_etl_count=0,
        )
        mock_service = AsyncMock(spec=BouncerService)
        mock_service.get_bouncer_topology.return_value = mock_result

        app.dependency_overrides[get_bouncer_service] = lambda: mock_service

        response = await admin_client.get(
            "/api/bouncers/topology?bouncers=SwitchBouncer&mode=union"
        )

        app.dependency_overrides.pop(get_bouncer_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "selected_bouncers" in body
        assert "downstream_etls" in body
        assert "total_etl_count" in body

    async def test_bouncer_topology_requires_bouncers_param(self, admin_client: AsyncClient, app):
        from app.dependencies import get_bouncer_service
        from app.services.bouncer_service import BouncerService

        mock_service = AsyncMock(spec=BouncerService)
        app.dependency_overrides[get_bouncer_service] = lambda: mock_service

        # No ?bouncers=... param
        response = await admin_client.get("/api/bouncers/topology")

        app.dependency_overrides.pop(get_bouncer_service, None)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# TestSchemaMatrixEndpoint
# ---------------------------------------------------------------------------


class TestSchemaMatrixEndpoint:
    async def test_schema_matrix_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_schema_matrix_service
        from app.schemas.schema_matrix import SchemaMatrixResponse
        from app.services.schema_matrix_service import SchemaMatrixService

        mock_result = SchemaMatrixResponse(fields=[], total=0)
        mock_service = AsyncMock(spec=SchemaMatrixService)
        mock_service.get_schema_matrix.return_value = mock_result

        app.dependency_overrides[get_schema_matrix_service] = lambda: mock_service

        response = await admin_client.get("/api/schema-matrix")

        app.dependency_overrides.pop(get_schema_matrix_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "fields" in body
        assert "total" in body
        assert body["total"] == 0

    async def test_schema_matrix_accepts_pagination(self, admin_client: AsyncClient, app):
        from app.dependencies import get_schema_matrix_service
        from app.schemas.schema_matrix import SchemaMatrixResponse
        from app.services.schema_matrix_service import SchemaMatrixService

        mock_result = SchemaMatrixResponse(fields=[], total=100)
        mock_service = AsyncMock(spec=SchemaMatrixService)
        mock_service.get_schema_matrix.return_value = mock_result

        app.dependency_overrides[get_schema_matrix_service] = lambda: mock_service

        response = await admin_client.get("/api/schema-matrix?skip=50&limit=50")

        app.dependency_overrides.pop(get_schema_matrix_service, None)

        assert response.status_code == 200
        mock_service.get_schema_matrix.assert_awaited_once_with(skip=50, limit=50)

    async def test_schema_matrix_member_can_access(self, member_client: AsyncClient, app):
        """Regular members must be able to access the schema matrix endpoint."""
        from app.dependencies import get_schema_matrix_service
        from app.schemas.schema_matrix import SchemaMatrixResponse
        from app.services.schema_matrix_service import SchemaMatrixService

        mock_result = SchemaMatrixResponse(fields=[], total=0)
        mock_service = AsyncMock(spec=SchemaMatrixService)
        mock_service.get_schema_matrix.return_value = mock_result

        app.dependency_overrides[get_schema_matrix_service] = lambda: mock_service

        response = await member_client.get("/api/schema-matrix")

        app.dependency_overrides.pop(get_schema_matrix_service, None)

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TestDagSummaryEndpoint
# ---------------------------------------------------------------------------


class TestDagSummaryEndpoint:
    async def test_dag_summary_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_dag_summary_service
        from app.schemas.dag_summary import DagSummaryAggregate, DagSummaryResponse
        from app.services.dag_summary_service import DagSummaryService

        mock_result = DagSummaryResponse(
            aggregate=DagSummaryAggregate(
                total_dags=6,
                total_pipelines=30,
                active_dags=6,
                overall_success_rate=88.0,
                total_runs_30d=120,
                period_label="30d",
            ),
            dags=[],
        )
        mock_service = AsyncMock(spec=DagSummaryService)
        mock_service.get_dag_summaries.return_value = mock_result

        app.dependency_overrides[get_dag_summary_service] = lambda: mock_service

        response = await admin_client.get("/api/dags/summary")

        app.dependency_overrides.pop(get_dag_summary_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "aggregate" in body
        assert "dags" in body
        assert body["aggregate"]["total_dags"] == 6

    async def test_dag_summary_accepts_date_range(self, admin_client: AsyncClient, app):
        from app.dependencies import get_dag_summary_service
        from app.schemas.dag_summary import DagSummaryAggregate, DagSummaryResponse
        from app.services.dag_summary_service import DagSummaryService

        mock_result = DagSummaryResponse(
            aggregate=DagSummaryAggregate(),
            dags=[],
        )
        mock_service = AsyncMock(spec=DagSummaryService)
        mock_service.get_dag_summaries.return_value = mock_result

        app.dependency_overrides[get_dag_summary_service] = lambda: mock_service

        response = await admin_client.get(
            "/api/dags/summary?date_from=2024-01-01&date_to=2024-01-31"
        )

        app.dependency_overrides.pop(get_dag_summary_service, None)

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# TestUsageEndpoints
# ---------------------------------------------------------------------------


class TestUsageEndpoints:
    async def test_get_usage_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_usage_service
        from app.schemas.usage import PipelineUsageResponse
        from app.services.usage_service import UsageService

        mock_result = PipelineUsageResponse(usages=[])
        mock_service = AsyncMock(spec=UsageService)
        mock_service.get_pipeline_usage.return_value = mock_result

        app.dependency_overrides[get_usage_service] = lambda: mock_service

        response = await admin_client.get("/api/usage/SwitchPortCollector")

        app.dependency_overrides.pop(get_usage_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "usages" in body

    async def test_get_consumers_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_consumer_service
        from app.schemas.consumer import PipelineConsumersResponse
        from app.services.consumer_service import ConsumerService

        mock_result = PipelineConsumersResponse(consumers=[])
        mock_service = AsyncMock(spec=ConsumerService)
        mock_service.get_pipeline_consumers.return_value = mock_result

        app.dependency_overrides[get_consumer_service] = lambda: mock_service

        response = await admin_client.get("/api/consumers/SwitchPortCollector")

        app.dependency_overrides.pop(get_consumer_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "consumers" in body

    async def test_get_usage_passes_etl_name(self, admin_client: AsyncClient, app):
        from app.dependencies import get_usage_service
        from app.schemas.usage import PipelineUsageResponse
        from app.services.usage_service import UsageService

        mock_result = PipelineUsageResponse(usages=[])
        mock_service = AsyncMock(spec=UsageService)
        mock_service.get_pipeline_usage.return_value = mock_result

        app.dependency_overrides[get_usage_service] = lambda: mock_service

        response = await admin_client.get("/api/usage/RouteTableSync")

        app.dependency_overrides.pop(get_usage_service, None)

        assert response.status_code == 200
        called_with = mock_service.get_pipeline_usage.call_args
        assert called_with.args[0] == "RouteTableSync" or called_with.kwargs.get("etl_name") == "RouteTableSync"


# ---------------------------------------------------------------------------
# TestTeamEndpoints
# ---------------------------------------------------------------------------


class TestTeamEndpoints:
    async def test_list_teams_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_team_service
        from app.services.team_service import TeamService

        team = make_team(name="Dagger", source="sso")
        team.members = []

        mock_service = AsyncMock(spec=TeamService)
        mock_service.list_teams.return_value = [team]

        app.dependency_overrides[get_team_service] = lambda: mock_service

        response = await admin_client.get("/api/teams")

        app.dependency_overrides.pop(get_team_service, None)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["name"] == "Dagger"

    async def test_list_teams_returns_empty_list(self, admin_client: AsyncClient, app):
        from app.dependencies import get_team_service
        from app.services.team_service import TeamService

        mock_service = AsyncMock(spec=TeamService)
        mock_service.list_teams.return_value = []

        app.dependency_overrides[get_team_service] = lambda: mock_service

        response = await admin_client.get("/api/teams")

        app.dependency_overrides.pop(get_team_service, None)

        assert response.status_code == 200
        assert response.json() == []

    async def test_get_team_returns_200_for_admin(self, admin_client: AsyncClient, app):
        from app.dependencies import get_team_service
        from app.services.team_service import TeamService

        team_id = uuid.uuid4()
        team = make_team(name="Dagger")
        team.id = team_id
        team.description = "Network backbone team"
        team.source = "sso"
        team.members = []

        mock_service = AsyncMock(spec=TeamService)
        mock_service.get_team_detail.return_value = team
        mock_service.user_can_access_team.return_value = True

        app.dependency_overrides[get_team_service] = lambda: mock_service

        response = await admin_client.get(f"/api/teams/{team_id}")

        app.dependency_overrides.pop(get_team_service, None)

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Dagger"
        assert "members" in body

    async def test_get_team_404_for_unknown_team(self, admin_client: AsyncClient, app):
        from app.dependencies import get_team_service
        from app.services.team_service import TeamService

        mock_service = AsyncMock(spec=TeamService)
        mock_service.get_team_detail.return_value = None

        app.dependency_overrides[get_team_service] = lambda: mock_service

        response = await admin_client.get(f"/api/teams/{uuid.uuid4()}")

        app.dependency_overrides.pop(get_team_service, None)

        assert response.status_code == 404

    async def test_get_team_403_for_non_member(self, member_client: AsyncClient, app):
        from app.dependencies import get_team_service
        from app.services.team_service import TeamService

        team_id = uuid.uuid4()
        team = make_team(name="Vault")
        team.id = team_id
        team.members = []

        mock_service = AsyncMock(spec=TeamService)
        mock_service.get_team_detail.return_value = team
        # Member does not belong to this team
        mock_service.user_can_access_team.return_value = False

        app.dependency_overrides[get_team_service] = lambda: mock_service

        response = await member_client.get(f"/api/teams/{team_id}")

        app.dependency_overrides.pop(get_team_service, None)

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# TestUserEndpoints
# ---------------------------------------------------------------------------


class TestUserEndpoints:
    async def test_update_role_returns_200_for_admin(self, app):
        from app.auth import get_current_user
        from app.dependencies import get_user_repo

        target_user_id = uuid.uuid4()
        admin = make_user(role="admin")
        admin.id = uuid.uuid4()  # Different from target

        mock_repo = AsyncMock()
        target_user = make_user(role="member")
        target_user.id = target_user_id
        mock_repo.get_by_id.return_value = target_user
        mock_repo.update_role.return_value = target_user

        app.dependency_overrides[get_current_user] = _override_current_user(admin)
        app.dependency_overrides[get_user_repo] = lambda: mock_repo

        with patch("app.routers.users.invalidate_user_cache", new_callable=AsyncMock):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://testserver",
            ) as ac:
                response = await ac.patch(
                    f"/api/users/{target_user_id}/role",
                    json={"role": "viewer"},
                )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_repo, None)

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    async def test_update_role_403_for_non_admin(self, member_client: AsyncClient):
        response = await member_client.patch(
            f"/api/users/{uuid.uuid4()}/role",
            json={"role": "viewer"},
        )
        assert response.status_code == 403

    async def test_update_active_returns_200_for_admin(self, app):
        from app.auth import get_current_user
        from app.dependencies import get_user_repo

        target_user_id = uuid.uuid4()
        admin = make_user(role="admin")
        admin.id = uuid.uuid4()  # Different from target

        mock_repo = AsyncMock()
        target_user = make_user(role="member")
        target_user.id = target_user_id
        mock_repo.update_active.return_value = target_user

        app.dependency_overrides[get_current_user] = _override_current_user(admin)
        app.dependency_overrides[get_user_repo] = lambda: mock_repo

        with patch("app.routers.users.invalidate_user_cache", new_callable=AsyncMock):
            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://testserver",
            ) as ac:
                response = await ac.patch(
                    f"/api/users/{target_user_id}/active",
                    json={"is_active": False},
                )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_repo, None)

        assert response.status_code == 200
        assert response.json() == {"ok": True}

    async def test_update_active_403_for_non_admin(self, member_client: AsyncClient):
        response = await member_client.patch(
            f"/api/users/{uuid.uuid4()}/active",
            json={"is_active": False},
        )
        assert response.status_code == 403

    async def test_update_role_400_when_demoting_self(self, app):
        """Admin cannot change their own role."""
        from app.auth import get_current_user
        from app.dependencies import get_user_repo

        admin = make_user(role="admin")

        mock_repo = AsyncMock()
        app.dependency_overrides[get_current_user] = _override_current_user(admin)
        app.dependency_overrides[get_user_repo] = lambda: mock_repo

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            response = await ac.patch(
                f"/api/users/{admin.id}/role",
                json={"role": "member"},  # Changing own role
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_repo, None)

        assert response.status_code == 400

    async def test_update_active_400_when_deactivating_self(self, app):
        """Admin cannot deactivate their own account."""
        from app.auth import get_current_user
        from app.dependencies import get_user_repo

        admin = make_user(role="admin")

        mock_repo = AsyncMock()
        app.dependency_overrides[get_current_user] = _override_current_user(admin)
        app.dependency_overrides[get_user_repo] = lambda: mock_repo

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            response = await ac.patch(
                f"/api/users/{admin.id}/active",
                json={"is_active": False},
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_repo, None)

        assert response.status_code == 400

    async def test_update_role_404_for_unknown_user(self, app):
        from app.auth import get_current_user
        from app.dependencies import get_user_repo

        admin = make_user(role="admin")
        admin.id = uuid.uuid4()
        target_id = uuid.uuid4()

        mock_repo = AsyncMock()
        # Simulate get_by_id returning a non-admin user to avoid last-admin check
        non_admin_user = make_user(role="member")
        non_admin_user.id = target_id
        mock_repo.get_by_id.return_value = non_admin_user
        mock_repo.update_role.return_value = None  # Not found on update

        app.dependency_overrides[get_current_user] = _override_current_user(admin)
        app.dependency_overrides[get_user_repo] = lambda: mock_repo

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            response = await ac.patch(
                f"/api/users/{target_id}/role",
                json={"role": "viewer"},
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_user_repo, None)

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# TestAIChatEndpoint
# ---------------------------------------------------------------------------


class TestAIChatEndpoint:
    async def test_ai_chat_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_ai_service
        from app.services.ai_service import AIService

        mock_service = AsyncMock(spec=AIService)
        mock_service.chat.return_value = "Here is my analysis of the pipeline topology."

        app.dependency_overrides[get_ai_service] = lambda: mock_service

        response = await admin_client.post(
            "/api/ai/chat",
            json={
                "message": "What pipelines are in the Dagger team?",
                "history": [],
            },
        )

        app.dependency_overrides.pop(get_ai_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "content" in body
        assert body["content"] == "Here is my analysis of the pipeline topology."

    async def test_ai_chat_passes_history(self, admin_client: AsyncClient, app):
        from app.dependencies import get_ai_service
        from app.services.ai_service import AIService

        mock_service = AsyncMock(spec=AIService)
        mock_service.chat.return_value = "Follow-up answer"

        app.dependency_overrides[get_ai_service] = lambda: mock_service

        response = await admin_client.post(
            "/api/ai/chat",
            json={
                "message": "Tell me more",
                "history": [
                    {"role": "user", "content": "What is ETL?"},
                    {"role": "assistant", "content": "ETL stands for..."},
                ],
            },
        )

        app.dependency_overrides.pop(get_ai_service, None)

        assert response.status_code == 200
        call_args = mock_service.chat.call_args
        history = call_args.args[1] if len(call_args.args) > 1 else call_args.kwargs.get("history", [])
        assert len(history) == 2

    async def test_ai_chat_returns_response_role(self, admin_client: AsyncClient, app):
        from app.dependencies import get_ai_service
        from app.services.ai_service import AIService

        mock_service = AsyncMock(spec=AIService)
        mock_service.chat.return_value = "Analysis complete."

        app.dependency_overrides[get_ai_service] = lambda: mock_service

        response = await admin_client.post(
            "/api/ai/chat",
            json={"message": "Analyze", "history": []},
        )

        app.dependency_overrides.pop(get_ai_service, None)

        assert response.status_code == 200
        body = response.json()
        assert body.get("role") == "assistant"

    async def test_ai_chat_requires_message_field(self, admin_client: AsyncClient, app):
        from app.dependencies import get_ai_service
        from app.services.ai_service import AIService

        mock_service = AsyncMock(spec=AIService)
        app.dependency_overrides[get_ai_service] = lambda: mock_service

        # Missing required 'message' field
        response = await admin_client.post(
            "/api/ai/chat",
            json={"history": []},
        )

        app.dependency_overrides.pop(get_ai_service, None)

        assert response.status_code == 422

    async def test_ai_join_insight_returns_200(self, admin_client: AsyncClient, app):
        from app.dependencies import get_ai_service
        from app.services.ai_service import AIService

        pipeline_id = uuid.uuid4()
        mock_service = AsyncMock(spec=AIService)
        mock_service.get_join_insight.return_value = "Join ip_address with route_table."

        app.dependency_overrides[get_ai_service] = lambda: mock_service

        response = await admin_client.get(f"/api/pipelines/{pipeline_id}/joins/ai")

        app.dependency_overrides.pop(get_ai_service, None)

        assert response.status_code == 200
        body = response.json()
        assert "insight" in body
        assert body["insight"] == "Join ip_address with route_table."
