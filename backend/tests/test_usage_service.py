"""Tests for UsageService — downstream consumer discovery with usage enrichment."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

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
    execution_date: datetime | None = None,
):
    p = MagicMock()
    p.id = uuid.uuid4()
    p.task_id = task_id
    p.name = name
    p.status = status
    p.category = category
    p.description = f"Description of {name}"
    p.execution_date = execution_date
    return p


def make_usage_enrichment(*, access_count: int = 5, description: str = "desc"):
    e = MagicMock()
    e.access_count = access_count
    e.description = description
    e.last_accessed_at = datetime(2024, 1, 15, tzinfo=UTC)
    return e


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def usage_repo():
    return AsyncMock()


@pytest.fixture
def pipeline_repo():
    return AsyncMock()


@pytest.fixture
def dag_task_repo():
    return AsyncMock()


@pytest.fixture
def service(usage_repo, pipeline_repo, dag_task_repo):
    return UsageService(usage_repo, pipeline_repo, dag_task_repo)


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
        self, service, dag_task_repo, pipeline_repo, usage_repo
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

        usage_repo.get_enrichment_map.return_value = {}

        result = await service.get_pipeline_usage("PortScanCollector")

        assert len(result.usages) == 2
        first = result.usages[0]
        assert first.is_current is True
        assert first.consumer_name == "Port Scan Collector"

    async def test_downstream_consumers_follow_current_pipeline(
        self, service, dag_task_repo, pipeline_repo, usage_repo
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
        usage_repo.get_enrichment_map.return_value = {}

        result = await service.get_pipeline_usage("PortScanCollector")

        assert len(result.usages) == 3
        assert result.usages[0].is_current is True
        consumer_names = {u.consumer_name for u in result.usages[1:]}
        assert "Routing Analyzer" in consumer_names
        assert "Bandwidth Tracker" in consumer_names

    async def test_enrichment_applied_to_current_pipeline(
        self, service, dag_task_repo, pipeline_repo, usage_repo
    ):
        dag_entry = make_dag_entry(task_id="PortScanCollector")
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(task_id="PortScanCollector")
        pipeline_repo.get_task_id_map.return_value = {"PortScanCollector": current}

        enrichment = make_usage_enrichment(access_count=42)
        usage_repo.get_enrichment_map.return_value = {"PortScanCollector": enrichment}

        result = await service.get_pipeline_usage("PortScanCollector")

        assert result.usages[0].access_count == 42

    async def test_api_category_usage_type(
        self, service, dag_task_repo, pipeline_repo, usage_repo
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
        usage_repo.get_enrichment_map.return_value = {}

        result = await service.get_pipeline_usage("NetworkInsightsApi")

        assert result.usages[0].usage_type == "api"
        assert result.usages[1].usage_type == "api"

    async def test_date_range_passed_to_usage_repo(
        self, service, dag_task_repo, pipeline_repo, usage_repo
    ):
        dag_entry = make_dag_entry(task_id="PortScanCollector")
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(task_id="PortScanCollector")
        pipeline_repo.get_task_id_map.return_value = {"PortScanCollector": current}
        usage_repo.get_enrichment_map.return_value = {}

        date_from = datetime(2024, 1, 1, tzinfo=UTC)
        date_to = datetime(2024, 1, 31, tzinfo=UTC)

        await service.get_pipeline_usage(
            "PortScanCollector", date_from=date_from, date_to=date_to
        )

        usage_repo.get_enrichment_map.assert_awaited_once_with(
            "PortScanCollector", date_from=date_from, date_to=date_to,
        )

    async def test_task_not_in_pipeline_map_uses_formatted_name(
        self, service, dag_task_repo, pipeline_repo, usage_repo
    ):
        dag_entry = make_dag_entry(
            task_id="PortScanCollector",
            downstream_task_ids=["UnknownEtlTask"],
        )
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]

        current = make_pipeline_summary(task_id="PortScanCollector")
        # UnknownEtlTask is not in the pipeline map
        pipeline_repo.get_task_id_map.return_value = {"PortScanCollector": current}
        usage_repo.get_enrichment_map.return_value = {}

        result = await service.get_pipeline_usage("PortScanCollector")

        assert len(result.usages) == 2
        # The unknown task should still appear with a formatted name
        consumer = result.usages[1]
        assert "Unknown Etl Task" in consumer.consumer_name

    async def test_deduplicates_downstream_across_multiple_dags(
        self, service, dag_task_repo, pipeline_repo, usage_repo
    ):
        # Same downstream task_id appears in two DAG entries
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
        usage_repo.get_enrichment_map.return_value = {}

        result = await service.get_pipeline_usage("PortScanCollector")

        # Should be deduplicated: 1 current + 1 downstream
        assert len(result.usages) == 2

    async def test_current_pipeline_not_in_map_uses_task_id_as_fallback(
        self, service, dag_task_repo, pipeline_repo, usage_repo
    ):
        dag_entry = make_dag_entry(task_id="OrphanedTask")
        dag_task_repo.get_dags_for_task.return_value = [dag_entry]
        pipeline_repo.get_task_id_map.return_value = {}
        usage_repo.get_enrichment_map.return_value = {}

        result = await service.get_pipeline_usage("OrphanedTask")

        # Even without pipeline data, current entry should be included
        assert len(result.usages) >= 1
        assert result.usages[0].is_current is True
