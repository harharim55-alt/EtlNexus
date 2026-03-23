"""Tests for BouncerService — bouncer listing and downstream topology traversal."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.cache import bouncer_cache, bouncer_topology_cache
from app.services.bouncer_service import BouncerService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_bouncer_orm(
    *,
    bouncer_name: str = "SwitchBouncer",
    display_name: str | None = None,
    team: str = "Dagger",
    volume_per_day: int = 10000,
    status: str = "success",
    dag_ids: list[str] | None = None,
    description: str | None = None,
):
    b = MagicMock()
    b.id = uuid.uuid4()
    b.bouncer_name = bouncer_name
    b.display_name = display_name or bouncer_name
    b.description = description
    b.team = team
    b.volume_per_day = volume_per_day
    b.status = status
    b.dag_ids = dag_ids or ["network_recon"]
    return b


def make_dag_task(
    *,
    dag_id: str = "network_recon",
    task_id: str = "PortScanCollector",
    downstream_task_ids: list[str] | None = None,
    bouncer_name: str | None = None,
    pipeline_id: uuid.UUID | None = None,
):
    dt = MagicMock()
    dt.dag_id = dag_id
    dt.task_id = task_id
    dt.downstream_task_ids = downstream_task_ids or []
    dt.bouncer_name = bouncer_name
    dt.pipeline_id = pipeline_id or uuid.uuid4()
    return dt


def make_pipeline_lightweight(*, task_id: str, name: str = "Pipeline", status: str = "success"):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.task_id = task_id
    p.name = name
    p.status = status
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bouncer_repo():
    return AsyncMock()


@pytest.fixture
def dag_task_repo():
    return AsyncMock()


@pytest.fixture
def pipeline_repo():
    return AsyncMock()


@pytest.fixture
def service(bouncer_repo, dag_task_repo, pipeline_repo):
    return BouncerService(bouncer_repo, dag_task_repo, pipeline_repo)


@pytest.fixture(autouse=True)
def clear_caches():
    bouncer_cache.clear()
    bouncer_topology_cache.clear()
    yield
    bouncer_cache.clear()
    bouncer_topology_cache.clear()


# ---------------------------------------------------------------------------
# get_all_bouncers
# ---------------------------------------------------------------------------


class TestGetAllBouncers:
    async def test_returns_all_bouncers(self, service, bouncer_repo):
        b1 = make_bouncer_orm(bouncer_name="SwitchBouncer", team="Dagger")
        b2 = make_bouncer_orm(bouncer_name="FirewallBouncer", team="Vault")
        bouncer_repo.get_all.return_value = [b1, b2]
        bouncer_repo.get_all_teams.return_value = ["Dagger", "Vault"]

        result = await service.get_all_bouncers()

        assert len(result.bouncers) == 2
        assert result.bouncers[0].bouncer_name == "SwitchBouncer"
        assert result.bouncers[1].bouncer_name == "FirewallBouncer"
        assert set(result.teams) == {"Dagger", "Vault"}

    async def test_filters_by_team(self, service, bouncer_repo):
        b1 = make_bouncer_orm(bouncer_name="SwitchBouncer", team="Dagger")
        bouncer_repo.get_by_team.return_value = [b1]
        bouncer_repo.get_all_teams.return_value = ["Dagger", "Vault"]

        result = await service.get_all_bouncers(team="Dagger")

        bouncer_repo.get_by_team.assert_awaited_once_with("Dagger")
        bouncer_repo.get_all.assert_not_awaited()
        assert len(result.bouncers) == 1
        assert result.bouncers[0].team == "Dagger"

    async def test_returns_empty_for_unknown_team(self, service, bouncer_repo):
        bouncer_repo.get_by_team.return_value = []
        bouncer_repo.get_all_teams.return_value = ["Dagger"]

        result = await service.get_all_bouncers(team="UnknownTeam")

        assert result.bouncers == []

    async def test_caches_result(self, service, bouncer_repo):
        bouncer_repo.get_all.return_value = []
        bouncer_repo.get_all_teams.return_value = []

        await service.get_all_bouncers()
        await service.get_all_bouncers()

        # Second call should hit cache, not the repo
        assert bouncer_repo.get_all.await_count == 1

    async def test_separate_cache_keys_for_all_vs_team(self, service, bouncer_repo):
        b1 = make_bouncer_orm(team="Dagger")
        bouncer_repo.get_all.return_value = [b1]
        bouncer_repo.get_by_team.return_value = []
        bouncer_repo.get_all_teams.return_value = ["Dagger"]

        await service.get_all_bouncers()
        await service.get_all_bouncers(team="Dagger")

        assert bouncer_repo.get_all.await_count == 1
        assert bouncer_repo.get_by_team.await_count == 1

    async def test_bouncer_response_fields(self, service, bouncer_repo):
        b = make_bouncer_orm(
            bouncer_name="TrafficBouncer",
            display_name="Traffic Bouncer",
            team="Relay",
            volume_per_day=50000,
            status="failed",
            dag_ids=["peering_audit"],
            description="Collects traffic data",
        )
        bouncer_repo.get_all.return_value = [b]
        bouncer_repo.get_all_teams.return_value = ["Relay"]

        result = await service.get_all_bouncers()

        item = result.bouncers[0]
        assert item.bouncer_name == "TrafficBouncer"
        assert item.display_name == "Traffic Bouncer"
        assert item.team == "Relay"
        assert item.volume_per_day == 50000
        assert item.status == "failed"
        assert item.dag_ids == ["peering_audit"]
        assert item.description == "Collects traffic data"


# ---------------------------------------------------------------------------
# get_bouncer_topology
# ---------------------------------------------------------------------------


class TestGetBouncerTopology:
    async def test_union_mode_collects_all_downstream(
        self, service, bouncer_repo, dag_task_repo, pipeline_repo
    ):
        """Union mode: ETLs reachable from any selected bouncer."""
        bouncer_dt = make_dag_task(
            dag_id="dag1", task_id="SwitchBouncer",
            bouncer_name="SwitchBouncer",
            downstream_task_ids=["EtlA", "EtlB"],
        )
        etl_a = make_dag_task(dag_id="dag1", task_id="EtlA", downstream_task_ids=[])
        etl_b = make_dag_task(dag_id="dag1", task_id="EtlB", downstream_task_ids=[])

        dag_task_repo.get_all_entries.return_value = [bouncer_dt, etl_a, etl_b]

        pipeline_a = make_pipeline_lightweight(task_id="EtlA", name="ETL A")
        pipeline_b = make_pipeline_lightweight(task_id="EtlB", name="ETL B")
        pipeline_repo.get_task_id_map.return_value = {
            "EtlA": pipeline_a,
            "EtlB": pipeline_b,
        }

        result = await service.get_bouncer_topology(
            bouncer_names=["SwitchBouncer"], mode="union"
        )

        assert result.total_etl_count == 2
        task_ids = {n.task_id for n in result.downstream_etls}
        assert task_ids == {"EtlA", "EtlB"}

    async def test_intersection_mode_only_shared_downstream(
        self, service, bouncer_repo, dag_task_repo, pipeline_repo
    ):
        """Intersection mode: only ETLs reachable from ALL selected bouncers."""
        # Bouncer1 -> EtlA, EtlB; Bouncer2 -> EtlB, EtlC
        b1 = make_dag_task(
            dag_id="dag1", task_id="Bouncer1",
            bouncer_name="Bouncer1",
            downstream_task_ids=["EtlA", "EtlB"],
        )
        b2 = make_dag_task(
            dag_id="dag1", task_id="Bouncer2",
            bouncer_name="Bouncer2",
            downstream_task_ids=["EtlB", "EtlC"],
        )
        etl_a = make_dag_task(dag_id="dag1", task_id="EtlA")
        etl_b = make_dag_task(dag_id="dag1", task_id="EtlB")
        etl_c = make_dag_task(dag_id="dag1", task_id="EtlC")

        dag_task_repo.get_all_entries.return_value = [b1, b2, etl_a, etl_b, etl_c]

        pipeline_b = make_pipeline_lightweight(task_id="EtlB", name="ETL B")
        pipeline_repo.get_task_id_map.return_value = {
            "EtlA": make_pipeline_lightweight(task_id="EtlA"),
            "EtlB": pipeline_b,
            "EtlC": make_pipeline_lightweight(task_id="EtlC"),
        }

        result = await service.get_bouncer_topology(
            bouncer_names=["Bouncer1", "Bouncer2"], mode="intersection"
        )

        # Only EtlB is reachable from both bouncers
        assert result.total_etl_count == 1
        assert result.downstream_etls[0].task_id == "EtlB"

    async def test_empty_bouncer_names_returns_empty_result(
        self, service, bouncer_repo, dag_task_repo, pipeline_repo
    ):
        dag_task_repo.get_all_entries.return_value = []
        pipeline_repo.get_task_id_map.return_value = {}

        result = await service.get_bouncer_topology(bouncer_names=[], mode="union")

        assert result.total_etl_count == 0
        assert result.downstream_etls == []
        assert result.selected_bouncers == []

    async def test_topology_result_is_cached(
        self, service, bouncer_repo, dag_task_repo, pipeline_repo
    ):
        dag_task_repo.get_all_entries.return_value = []
        pipeline_repo.get_task_id_map.return_value = {}

        await service.get_bouncer_topology(bouncer_names=["Bouncer1"], mode="union")
        await service.get_bouncer_topology(bouncer_names=["Bouncer1"], mode="union")

        assert dag_task_repo.get_all_entries.await_count == 1

    async def test_bfs_traverses_multi_hop_downstream(
        self, service, bouncer_repo, dag_task_repo, pipeline_repo
    ):
        """Bouncer -> EtlA -> EtlB: both should be discovered via BFS."""
        bouncer_dt = make_dag_task(
            dag_id="dag1", task_id="DataBouncer",
            bouncer_name="DataBouncer",
            downstream_task_ids=["EtlA"],
        )
        etl_a = make_dag_task(dag_id="dag1", task_id="EtlA", downstream_task_ids=["EtlB"])
        etl_b = make_dag_task(dag_id="dag1", task_id="EtlB", downstream_task_ids=[])

        dag_task_repo.get_all_entries.return_value = [bouncer_dt, etl_a, etl_b]

        pipeline_repo.get_task_id_map.return_value = {
            "EtlA": make_pipeline_lightweight(task_id="EtlA"),
            "EtlB": make_pipeline_lightweight(task_id="EtlB"),
        }

        result = await service.get_bouncer_topology(
            bouncer_names=["DataBouncer"], mode="union"
        )

        task_ids = {n.task_id for n in result.downstream_etls}
        assert "EtlA" in task_ids
        assert "EtlB" in task_ids

    async def test_nodes_include_pipeline_name_from_map(
        self, service, bouncer_repo, dag_task_repo, pipeline_repo
    ):
        bouncer_dt = make_dag_task(
            dag_id="dag1", task_id="NetBouncer",
            bouncer_name="NetBouncer",
            downstream_task_ids=["EtlX"],
        )
        etl_x = make_dag_task(dag_id="dag1", task_id="EtlX")
        dag_task_repo.get_all_entries.return_value = [bouncer_dt, etl_x]

        pipeline_x = make_pipeline_lightweight(task_id="EtlX", name="Network Collector")
        pipeline_repo.get_task_id_map.return_value = {"EtlX": pipeline_x}

        result = await service.get_bouncer_topology(
            bouncer_names=["NetBouncer"], mode="union"
        )

        assert result.downstream_etls[0].pipeline_name == "Network Collector"
        assert result.downstream_etls[0].pipeline_id == str(pipeline_x.id)

    async def test_deduplicates_tasks_appearing_in_multiple_dags(
        self, service, bouncer_repo, dag_task_repo, pipeline_repo
    ):
        """The same task_id in two DAGs should only appear once in results."""
        b1 = make_dag_task(
            dag_id="dag1", task_id="NetBouncer",
            bouncer_name="NetBouncer",
            downstream_task_ids=["EtlShared"],
        )
        b2 = make_dag_task(
            dag_id="dag2", task_id="NetBouncer",
            bouncer_name="NetBouncer",
            downstream_task_ids=["EtlShared"],
        )
        etl1 = make_dag_task(dag_id="dag1", task_id="EtlShared")
        etl2 = make_dag_task(dag_id="dag2", task_id="EtlShared")

        dag_task_repo.get_all_entries.return_value = [b1, b2, etl1, etl2]

        pipeline_repo.get_task_id_map.return_value = {
            "EtlShared": make_pipeline_lightweight(task_id="EtlShared"),
        }

        result = await service.get_bouncer_topology(
            bouncer_names=["NetBouncer"], mode="union"
        )

        # Deduplicated by task_id
        assert result.total_etl_count == 1
        assert result.downstream_etls[0].task_id == "EtlShared"
