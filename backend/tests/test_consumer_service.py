"""Tests for ConsumerService — downstream pipeline consumer discovery."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.consumer_service import ConsumerService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_dag_entry(
    *,
    dag_id: str = "backbone_core",
    task_id: str = "SwitchPortCollector",
    downstream_task_ids: list[str] | None = None,
):
    entry = MagicMock()
    entry.dag_id = dag_id
    entry.task_id = task_id
    entry.downstream_task_ids = downstream_task_ids or []
    return entry


def make_pipeline_summary(
    *,
    task_id: str,
    name: str = "Pipeline",
    status: str = "success",
    execution_date: datetime | None = None,
):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.task_id = task_id
    p.name = name
    p.status = status
    p.execution_date = execution_date
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline_repo():
    return AsyncMock()


@pytest.fixture
def dag_task_repo():
    return AsyncMock()


@pytest.fixture
def service(pipeline_repo, dag_task_repo):
    return ConsumerService(pipeline_repo, dag_task_repo)


# ---------------------------------------------------------------------------
# get_pipeline_consumers
# ---------------------------------------------------------------------------


class TestGetPipelineConsumers:
    async def test_returns_empty_when_no_dag_entries(
        self, service, dag_task_repo
    ):
        dag_task_repo.get_dags_for_task.return_value = []

        result = await service.get_pipeline_consumers("UnknownEtl")

        assert result.consumers == []

    async def test_returns_downstream_consumers(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="SwitchPortCollector",
            downstream_task_ids=["RoutingAnalyzer"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        downstream = make_pipeline_summary(task_id="RoutingAnalyzer", name="Routing Analyzer")
        pipeline_repo.get_task_id_map.return_value = {"RoutingAnalyzer": downstream}

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        assert len(result.consumers) == 1
        consumer = result.consumers[0]
        assert consumer.pipeline_name == "Routing Analyzer"
        assert consumer.dag_id == "backbone_core"
        assert consumer.airflow_status == "success"

    async def test_returns_multiple_consumers(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="SwitchPortCollector",
            downstream_task_ids=["RoutingAnalyzer", "BandwidthTracker", "TrafficReporter"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        p1 = make_pipeline_summary(task_id="RoutingAnalyzer", name="Routing Analyzer")
        p2 = make_pipeline_summary(task_id="BandwidthTracker", name="Bandwidth Tracker")
        p3 = make_pipeline_summary(task_id="TrafficReporter", name="Traffic Reporter")
        pipeline_repo.get_task_id_map.return_value = {
            "RoutingAnalyzer": p1,
            "BandwidthTracker": p2,
            "TrafficReporter": p3,
        }

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        assert len(result.consumers) == 3
        names = {c.pipeline_name for c in result.consumers}
        assert names == {"Routing Analyzer", "Bandwidth Tracker", "Traffic Reporter"}

    async def test_uses_pipeline_id_string_from_map(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="SwitchPortCollector",
            downstream_task_ids=["RoutingAnalyzer"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        downstream = make_pipeline_summary(task_id="RoutingAnalyzer")
        pipeline_repo.get_task_id_map.return_value = {"RoutingAnalyzer": downstream}

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        assert result.consumers[0].pipeline_id == str(downstream.id)

    async def test_task_not_in_pipeline_map_uses_task_id_as_fallback(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="SwitchPortCollector",
            downstream_task_ids=["UnknownEtlTask"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]
        pipeline_repo.get_task_id_map.return_value = {}

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        assert len(result.consumers) == 1
        consumer = result.consumers[0]
        # falls back to formatted task_id as name
        assert "Unknown Etl Task" in consumer.pipeline_name
        # pipeline_id falls back to task_id string
        assert consumer.pipeline_id == "UnknownEtlTask"

    async def test_consumer_status_from_pipeline_map(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="SwitchPortCollector",
            downstream_task_ids=["FailedPipeline"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        downstream = make_pipeline_summary(task_id="FailedPipeline", status="failed")
        pipeline_repo.get_task_id_map.return_value = {"FailedPipeline": downstream}

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        assert result.consumers[0].airflow_status == "failed"

    async def test_deduplicates_consumers_across_multiple_dag_entries(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag1 = make_dag_entry(
            dag_id="dag1",
            task_id="SwitchPortCollector",
            downstream_task_ids=["SharedConsumer"],
        )
        dag2 = make_dag_entry(
            dag_id="dag2",
            task_id="SwitchPortCollector",
            downstream_task_ids=["SharedConsumer"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag1, dag2]

        shared = make_pipeline_summary(task_id="SharedConsumer")
        pipeline_repo.get_task_id_map.return_value = {"SharedConsumer": shared}

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        # SharedConsumer should appear only once
        assert len(result.consumers) == 1

    async def test_last_run_at_from_execution_date(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="SwitchPortCollector",
            downstream_task_ids=["RoutingAnalyzer"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        exec_date = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
        downstream = make_pipeline_summary(
            task_id="RoutingAnalyzer",
            execution_date=exec_date,
        )
        pipeline_repo.get_task_id_map.return_value = {"RoutingAnalyzer": downstream}

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        # The service stores execution_date as isoformat string in the dict,
        # and the schema accepts either str or datetime — compare via isoformat
        last_run = result.consumers[0].last_run_at
        if isinstance(last_run, str):
            assert last_run == exec_date.isoformat()
        else:
            assert last_run == exec_date

    async def test_no_consumers_when_no_downstream_tasks(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="SwitchPortCollector",
            downstream_task_ids=[],  # Leaf node
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]
        pipeline_repo.get_task_id_map.return_value = {}

        result = await service.get_pipeline_consumers("SwitchPortCollector")

        assert result.consumers == []
