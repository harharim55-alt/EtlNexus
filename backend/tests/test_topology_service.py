"""Tests for TopologyService — pipeline dependency graph construction."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.topology_service import TopologyService
from tests.conftest import make_pipeline


def make_dag_task(
    *,
    dag_id: str = "network_recon",
    task_id: str = "PortScanCollector",
    downstream_task_ids: list | None = None,
    needs: list | None = None,
    prefers: list | None = None,
    task_group_id: str | None = None,
    bouncer_name: str | None = None,
    pipeline_id: uuid.UUID | None = None,
):
    dt = MagicMock()
    dt.dag_id = dag_id
    dt.task_id = task_id
    dt.downstream_task_ids = downstream_task_ids or []
    dt.needs = needs or []
    dt.prefers = prefers or []
    dt.task_group_id = task_group_id
    dt.bouncer_name = bouncer_name
    dt.pipeline_id = pipeline_id
    return dt


def make_bouncer(*, bouncer_name: str, display_name: str | None = None):
    b = MagicMock()
    b.id = uuid.uuid4()
    b.bouncer_name = bouncer_name
    b.display_name = display_name or bouncer_name.replace("_", " ").title()
    b.status = "success"
    b.team = "Dagger"
    b.volume_per_day = 10000
    return b


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    svc = TopologyService.__new__(TopologyService)
    svc.pipeline_repo = AsyncMock()
    svc.dag_task_repo = AsyncMock()
    svc.bouncer_repo = AsyncMock()
    return svc


class TestBuildPipelineTopology:
    async def test_returns_none_when_pipeline_not_found(self, service):
        service.pipeline_repo.get_by_id.return_value = None

        result = await service.build_pipeline_topology(uuid.uuid4())
        assert result is None

    async def test_returns_none_when_no_task_id(self, service):
        pipeline = make_pipeline()
        pipeline.task_id = None
        service.pipeline_repo.get_by_id.return_value = pipeline

        result = await service.build_pipeline_topology(pipeline.id)
        assert result is None

    async def test_returns_empty_graph_when_no_dag_entries(self, service):
        pipeline = make_pipeline()
        service.pipeline_repo.get_by_id.return_value = pipeline
        service.dag_task_repo.get_dags_for_task.return_value = []

        result = await service.build_pipeline_topology(pipeline.id)
        assert result is not None
        assert result.pipeline_task_id == pipeline.task_id
        assert result.dag_ids == []
        assert result.upstream_needs == []
        assert result.upstream_prefers == []
        assert result.downstream == []

    async def test_builds_topology_with_needs_and_downstream(self, service):
        pipeline = make_pipeline(task_id="CollectorA")
        upstream_pipeline = make_pipeline(task_id="SourceB", name="Source B")
        downstream_pipeline = make_pipeline(task_id="ConsumerC", name="Consumer C")

        # Pipeline has one DAG entry
        dag_entry = make_dag_task(
            dag_id="network_recon",
            task_id="CollectorA",
            needs=["SourceB"],
            downstream_task_ids=["ConsumerC"],
        )

        # DAG contains all three tasks
        source_dt = make_dag_task(dag_id="network_recon", task_id="SourceB",
                                  downstream_task_ids=["CollectorA"])
        consumer_dt = make_dag_task(dag_id="network_recon", task_id="ConsumerC")

        service.pipeline_repo.get_by_id.return_value = pipeline
        service.dag_task_repo.get_dags_for_task.return_value = [dag_entry]
        service.dag_task_repo.get_tasks_for_dag.return_value = [
            dag_entry, source_dt, consumer_dt,
        ]
        service.pipeline_repo.get_all.return_value = [
            pipeline, upstream_pipeline, downstream_pipeline,
        ]
        service.bouncer_repo.get_by_names.return_value = []

        result = await service.build_pipeline_topology(pipeline.id)
        assert result is not None
        assert result.pipeline_task_id == "CollectorA"
        assert len(result.upstream_needs) == 1
        assert result.upstream_needs[0].task_id == "SourceB"
        assert len(result.downstream) == 1
        assert result.downstream[0].task_id == "ConsumerC"

    async def test_discovers_upstream_bouncers_via_bfs(self, service):
        pipeline = make_pipeline(task_id="CollectorA")
        bouncer_dt = make_dag_task(
            dag_id="network_recon",
            task_id="SwitchBouncer",
            bouncer_name="SwitchBouncer",
            downstream_task_ids=["CollectorA"],
        )
        collector_dt = make_dag_task(
            dag_id="network_recon",
            task_id="CollectorA",
        )

        service.pipeline_repo.get_by_id.return_value = pipeline
        service.dag_task_repo.get_dags_for_task.return_value = [collector_dt]
        service.dag_task_repo.get_tasks_for_dag.return_value = [
            bouncer_dt, collector_dt,
        ]
        service.pipeline_repo.get_all.return_value = [pipeline]
        bouncer_obj = make_bouncer(bouncer_name="SwitchBouncer")
        service.bouncer_repo.get_by_names.return_value = [bouncer_obj]

        result = await service.build_pipeline_topology(pipeline.id)
        assert result is not None
        assert len(result.upstream_bouncers) == 1
        assert result.upstream_bouncers[0].bouncer_name == "SwitchBouncer"

    async def test_filters_by_dag_id(self, service):
        pipeline = make_pipeline(task_id="CollectorA")
        dag1_entry = make_dag_task(dag_id="dag1", task_id="CollectorA",
                                    needs=["DepA"])
        dag2_entry = make_dag_task(dag_id="dag2", task_id="CollectorA",
                                    needs=["DepB"])

        service.pipeline_repo.get_by_id.return_value = pipeline
        service.dag_task_repo.get_dags_for_task.return_value = [dag1_entry, dag2_entry]

        # Only dag1 tasks should be fetched
        dag1_dep = make_dag_task(dag_id="dag1", task_id="DepA",
                                  downstream_task_ids=["CollectorA"])
        service.dag_task_repo.get_tasks_for_dag.return_value = [
            dag1_entry, dag1_dep,
        ]
        service.pipeline_repo.get_all.return_value = [pipeline]
        service.bouncer_repo.get_by_names.return_value = []

        result = await service.build_pipeline_topology(pipeline.id, dag_id="dag1")
        assert result is not None
        assert result.dag_ids == ["dag1", "dag2"]
        assert len(result.upstream_needs) == 1
        assert result.upstream_needs[0].task_id == "DepA"


class TestBuildUpstreamTopology:
    async def test_returns_none_when_pipeline_not_found(self, service):
        service.pipeline_repo.get_by_id.return_value = None
        result = await service.build_upstream_topology(uuid.uuid4())
        assert result is None

    async def test_returns_single_node_when_no_dag_entries(self, service):
        pipeline = make_pipeline(task_id="CollectorA")
        service.pipeline_repo.get_by_id.return_value = pipeline
        service.dag_task_repo.get_dags_for_task.return_value = []

        result = await service.build_upstream_topology(pipeline.id)
        assert result is not None
        assert len(result.nodes) == 1
        assert result.nodes[0].is_current is True
        assert result.max_depth == 0

    async def test_bfs_traverses_needs_chain(self, service):
        """A -> B -> C should produce 3 nodes at depths 0, 1, 2."""
        pipeline = make_pipeline(task_id="A")

        dt_a = make_dag_task(dag_id="dag1", task_id="A", needs=["B"])
        dt_b = make_dag_task(dag_id="dag1", task_id="B", needs=["C"])
        dt_c = make_dag_task(dag_id="dag1", task_id="C")

        service.pipeline_repo.get_by_id.return_value = pipeline
        service.dag_task_repo.get_dags_for_task.return_value = [dt_a]
        service.dag_task_repo.get_tasks_for_dag.return_value = [dt_a, dt_b, dt_c]
        service.pipeline_repo.get_all.return_value = [pipeline]
        service.bouncer_repo.get_by_names.return_value = []

        result = await service.build_upstream_topology(pipeline.id)
        assert result is not None
        assert len(result.nodes) == 3
        # Edges: B->A (needs), C->B (needs)
        assert len(result.edges) == 2

        node_depths = {n.task_id: n.depth for n in result.nodes}
        assert node_depths["A"] == 0
        assert node_depths["B"] == 1
        assert node_depths["C"] == 2
        assert result.max_depth == 2


class TestEnrichBouncers:
    async def test_empty_bouncers_returns_empty(self, service):
        result = await service._enrich_bouncers({})
        assert result == []

    async def test_enriches_with_db_metadata(self, service):
        bouncer_obj = make_bouncer(
            bouncer_name="TrafficBouncer",
            display_name="Traffic Bouncer",
        )
        service.bouncer_repo.get_by_names.return_value = [bouncer_obj]

        result = await service._enrich_bouncers(
            {"TrafficBouncer": {"dag1", "dag2"}}
        )
        assert len(result) == 1
        assert result[0].bouncer_name == "TrafficBouncer"
        assert result[0].display_name == "Traffic Bouncer"
        assert sorted(result[0].dag_ids) == ["dag1", "dag2"]

    async def test_falls_back_when_bouncer_not_in_db(self, service):
        service.bouncer_repo.get_by_names.return_value = []

        result = await service._enrich_bouncers(
            {"UnknownBouncer": {"dag1"}}
        )
        assert len(result) == 1
        assert result[0].bouncer_name == "UnknownBouncer"
        assert result[0].status is None
