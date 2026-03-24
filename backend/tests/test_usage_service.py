"""Tests for UsageService — downstream consumer discovery with oasis_prod metrics."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.oasis_prod_client import ConsumerMetric, UsageMetrics
from app.services.usage_service import UsageService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_dag_entry(
    *,
    dag_id: str = "network_recon",
    task_id: str = "PortScanCollector",
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
    category: str = "Network Infrastructure",
    team: str = "dagger",
):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.task_id = task_id
    p.name = name
    p.status = status
    p.category = category
    p.team = team
    p.description = f"Description of {name}"
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
def mock_oasis_client():
    with patch("app.services.usage_service.oasis_prod_client") as mock:
        mock.get_usage_metrics = AsyncMock(return_value=None)
        mock.get_batch_usage_metrics = AsyncMock(return_value={})
        yield mock


@pytest.fixture
def service(pipeline_repo, dag_task_repo, mock_oasis_client):
    return UsageService(pipeline_repo, dag_task_repo)


# ---------------------------------------------------------------------------
# get_pipeline_usage
# ---------------------------------------------------------------------------


class TestGetPipelineUsage:
    async def test_returns_empty_when_no_dag_entries(
        self, service, dag_task_repo
    ):
        dag_task_repo.get_dags_for_task.return_value = []

        result = await service.get_pipeline_usage("UnknownEtl")

        assert result.usages == []

    async def test_current_pipeline_is_first_entry_with_is_current_true(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="PortScanCollector",
            downstream_task_ids=["RoutingAnalyzer"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current_pipeline = make_pipeline_summary(task_id="PortScanCollector", name="Port Scan Collector")
        downstream_pipeline = make_pipeline_summary(task_id="RoutingAnalyzer", name="Routing Analyzer")
        pipeline_repo.get_task_id_map.return_value = {
            "PortScanCollector": current_pipeline,
            "RoutingAnalyzer": downstream_pipeline,
        }

        result = await service.get_pipeline_usage("PortScanCollector")

        assert len(result.usages) == 2
        first = result.usages[0]
        assert first.is_current is True
        assert first.consumer_name == "Port Scan Collector"

    async def test_downstream_consumers_follow_current_pipeline(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="PortScanCollector",
            downstream_task_ids=["RoutingAnalyzer", "BandwidthTracker"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(task_id="PortScanCollector", name="Port Scan Collector")
        down1 = make_pipeline_summary(task_id="RoutingAnalyzer", name="Routing Analyzer")
        down2 = make_pipeline_summary(task_id="BandwidthTracker", name="Bandwidth Tracker")
        pipeline_repo.get_task_id_map.return_value = {
            "PortScanCollector": current,
            "RoutingAnalyzer": down1,
            "BandwidthTracker": down2,
        }

        result = await service.get_pipeline_usage("PortScanCollector")

        assert len(result.usages) == 3
        assert result.usages[0].is_current is True
        consumer_names = {u.consumer_name for u in result.usages[1:]}
        assert "Routing Analyzer" in consumer_names
        assert "Bandwidth Tracker" in consumer_names

    async def test_live_metrics_applied_to_current_pipeline(
        self, service, dag_task_repo, pipeline_repo, mock_oasis_client
    ):
        dag_entry = make_dag_entry(task_id="PortScanCollector")
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(task_id="PortScanCollector", team="dagger")
        pipeline_repo.get_task_id_map.return_value = {"PortScanCollector": current}

        mock_oasis_client.get_usage_metrics.return_value = UsageMetrics(
            unique_reads=5,
            total_reads=42,
            consumers=[
                ConsumerMetric(principal="user1", total_reads=30, last_accessed_at=datetime(2024, 1, 15, tzinfo=UTC)),
                ConsumerMetric(principal="user2", total_reads=12, last_accessed_at=datetime(2024, 1, 10, tzinfo=UTC)),
            ],
        )

        result = await service.get_pipeline_usage("PortScanCollector")

        assert result.usages[0].unique_reads == 5
        assert result.usages[0].total_reads == 42

    async def test_batch_metrics_applied_to_downstream_consumers(
        self, service, dag_task_repo, pipeline_repo, mock_oasis_client
    ):
        dag_entry = make_dag_entry(
            task_id="PortScanCollector",
            downstream_task_ids=["RoutingAnalyzer", "BandwidthTracker"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(task_id="PortScanCollector", team="dagger")
        down1 = make_pipeline_summary(task_id="RoutingAnalyzer", name="Routing Analyzer", team="dagger")
        down2 = make_pipeline_summary(task_id="BandwidthTracker", name="Bandwidth Tracker", team="dagger")
        pipeline_repo.get_task_id_map.return_value = {
            "PortScanCollector": current,
            "RoutingAnalyzer": down1,
            "BandwidthTracker": down2,
        }

        mock_oasis_client.get_batch_usage_metrics.return_value = {
            "dagger.RoutingAnalyzer": UsageMetrics(unique_reads=3, total_reads=210, consumers=[]),
            "dagger.BandwidthTracker": UsageMetrics(unique_reads=2, total_reads=140, consumers=[]),
        }

        result = await service.get_pipeline_usage("PortScanCollector")

        consumers = {u.consumer_name: u for u in result.usages[1:]}
        assert consumers["Routing Analyzer"].unique_reads == 3
        assert consumers["Routing Analyzer"].total_reads == 210
        assert consumers["Bandwidth Tracker"].unique_reads == 2
        assert consumers["Bandwidth Tracker"].total_reads == 140

    async def test_api_category_usage_type(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="NetworkInsightsApi",
            downstream_task_ids=["DownstreamApi"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(
            task_id="NetworkInsightsApi",
            name="Network Insights API",
            category="Network APIs",
        )
        downstream = make_pipeline_summary(
            task_id="DownstreamApi",
            name="Downstream API",
            category="Network APIs",
        )
        pipeline_repo.get_task_id_map.return_value = {
            "NetworkInsightsApi": current,
            "DownstreamApi": downstream,
        }

        result = await service.get_pipeline_usage("NetworkInsightsApi")

        assert result.usages[0].usage_type == "api"
        assert result.usages[1].usage_type == "api"

    async def test_network_filter_limits_downstream_consumers(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag1 = make_dag_entry(
            dag_id="dag_alpha",
            task_id="PortScanCollector",
            downstream_task_ids=["RoutingAnalyzer"],
        )
        dag2 = make_dag_entry(
            dag_id="dag_beta",
            task_id="PortScanCollector",
            downstream_task_ids=["BandwidthTracker"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag1, dag2]

        current = make_pipeline_summary(task_id="PortScanCollector")
        down1 = make_pipeline_summary(task_id="RoutingAnalyzer", name="Routing Analyzer")
        down2 = make_pipeline_summary(task_id="BandwidthTracker", name="Bandwidth Tracker")
        pipeline_repo.get_task_id_map.return_value = {
            "PortScanCollector": current,
            "RoutingAnalyzer": down1,
            "BandwidthTracker": down2,
        }

        result = await service.get_pipeline_usage("PortScanCollector", network="dag_alpha")

        assert len(result.usages) == 2
        assert result.usages[1].consumer_name == "Routing Analyzer"

    async def test_task_not_in_pipeline_map_uses_formatted_name(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(
            task_id="PortScanCollector",
            downstream_task_ids=["UnknownEtlTask"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(task_id="PortScanCollector")
        pipeline_repo.get_task_id_map.return_value = {"PortScanCollector": current}

        result = await service.get_pipeline_usage("PortScanCollector")

        assert len(result.usages) == 2
        consumer = result.usages[1]
        assert "Unknown Etl Task" in consumer.consumer_name

    async def test_deduplicates_downstream_across_multiple_dags(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag1 = make_dag_entry(
            dag_id="dag1",
            task_id="PortScanCollector",
            downstream_task_ids=["RoutingAnalyzer"],
        )
        dag2 = make_dag_entry(
            dag_id="dag2",
            task_id="PortScanCollector",
            downstream_task_ids=["RoutingAnalyzer"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag1, dag2]

        current = make_pipeline_summary(task_id="PortScanCollector")
        downstream = make_pipeline_summary(task_id="RoutingAnalyzer")
        pipeline_repo.get_task_id_map.return_value = {
            "PortScanCollector": current,
            "RoutingAnalyzer": downstream,
        }

        result = await service.get_pipeline_usage("PortScanCollector")

        assert len(result.usages) == 2

    async def test_current_pipeline_not_in_map_uses_task_id_as_fallback(
        self, service, dag_task_repo, pipeline_repo
    ):
        dag_entry = make_dag_entry(task_id="OrphanedTask")
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]
        pipeline_repo.get_task_id_map.return_value = {}

        result = await service.get_pipeline_usage("OrphanedTask")

        assert len(result.usages) >= 1
        assert result.usages[0].is_current is True
