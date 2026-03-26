"""Tests for ResourceService — resource metrics, execution plans, and run history."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.resource_service import ResourceService
from tests.conftest import make_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_resource_config(
    *,
    dag_id: str = "network_recon",
    spark_driver_memory: str = "4g",
    spark_executor_memory: str = "8g",
    spark_executor_cores: int = 4,
    spark_num_executors: int = 3,
    is_dag_override: bool = False,
):
    c = MagicMock()
    c.dag_id = dag_id
    c.spark_driver_memory = spark_driver_memory
    c.spark_executor_memory = spark_executor_memory
    c.spark_executor_cores = spark_executor_cores
    c.spark_num_executors = spark_num_executors
    c.is_dag_override = is_dag_override
    return c


def make_run(
    *,
    dag_id: str = "network_recon",
    dag_run_id: str = "run_20240101",
    status: str = "success",
    duration_seconds: float | None = 120.5,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    spark_application_id: str | None = None,
    metrics_source: str | None = "sparkmeasure",
    execution_plan: str | None = None,
):
    r = MagicMock()
    r.dag_id = dag_id
    r.dag_run_id = dag_run_id
    r.status = status
    r.duration_seconds = duration_seconds
    r.start_date = start_date or datetime.now(UTC)
    r.end_date = end_date
    r.spark_application_id = spark_application_id
    r.metrics_source = metrics_source
    r.execution_plan = execution_plan
    return r


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def resource_repo():
    return AsyncMock()


@pytest.fixture
def pipeline_repo():
    return AsyncMock()


@pytest.fixture
def stats_builder():
    return AsyncMock()


@pytest.fixture
def service(resource_repo, pipeline_repo, stats_builder):
    with patch("app.services.resource_service.ResourceStatsBuilder", return_value=stats_builder):
        svc = ResourceService(resource_repo, pipeline_repo)
    return svc


# ---------------------------------------------------------------------------
# get_resource_metrics
# ---------------------------------------------------------------------------


class TestGetResourceMetrics:
    async def test_returns_none_when_pipeline_not_found(self, service, pipeline_repo):
        pipeline_repo.get_by_id.return_value = None

        result = await service.get_resource_metrics(uuid.uuid4())

        assert result is None

    async def test_returns_metrics_with_configs_and_runs(
        self, service, pipeline_repo, resource_repo, stats_builder
    ):
        pipeline = make_pipeline(task_id="PortScanCollector")
        pipeline_repo.get_by_id.return_value = pipeline

        config = make_resource_config()
        resource_repo.get_configs_by_pipeline.return_value = [config]

        run = make_run(duration_seconds=90.0)
        resource_repo.get_recent_runs.return_value = [run]
        stats_builder.get_run_stats.return_value = {
            "avg_duration": 90.0,
            "min_duration": 80.0,
            "max_duration": 100.0,
            "run_count": 5,
            "success_rate": 80.0,
            "avg_driver_mem_used_mb": None,
            "avg_executor_mem_peak_mb": None,
            "avg_cpu_pct": None,
            "avg_executors_active": None,
            "avg_jvm_gc_time_ms": None,
            "avg_shuffle_read_bytes": None,
            "avg_shuffle_write_bytes": None,
            "avg_input_bytes": None,
            "avg_output_bytes": None,
            "avg_memory_bytes_spilled": None,
            "avg_disk_bytes_spilled": None,
            "avg_peak_execution_memory": None,
        }

        result = await service.get_resource_metrics(pipeline.id)

        assert result is not None
        assert result.avg_duration_seconds == 90.0
        assert result.run_count == 5
        assert result.success_rate == 80.0
        assert len(result.resource_configs) == 1
        assert result.resource_configs[0].dag_id == "network_recon"

    async def test_empty_configs_returns_empty_resource_configs(
        self, service, pipeline_repo, resource_repo, stats_builder
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        resource_repo.get_configs_by_pipeline.return_value = []
        resource_repo.get_recent_runs.return_value = []
        stats_builder.get_run_stats.return_value = {
            "avg_duration": None,
            "min_duration": None,
            "max_duration": None,
            "run_count": 0,
            "success_rate": None,
            "avg_driver_mem_used_mb": None,
            "avg_executor_mem_peak_mb": None,
            "avg_cpu_pct": None,
            "avg_executors_active": None,
            "avg_jvm_gc_time_ms": None,
            "avg_shuffle_read_bytes": None,
            "avg_shuffle_write_bytes": None,
            "avg_input_bytes": None,
            "avg_output_bytes": None,
            "avg_memory_bytes_spilled": None,
            "avg_disk_bytes_spilled": None,
            "avg_peak_execution_memory": None,
        }

        result = await service.get_resource_metrics(pipeline.id)

        assert result is not None
        assert result.resource_configs == []
        assert result.recent_runs == []
        assert result.capacity == []

    async def test_skips_runs_with_no_duration(
        self, service, pipeline_repo, resource_repo, stats_builder
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        resource_repo.get_configs_by_pipeline.return_value = []
        # run has no duration_seconds
        run = make_run(duration_seconds=None)
        resource_repo.get_recent_runs.return_value = [run]
        stats_builder.get_run_stats.return_value = {
            "avg_duration": None,
            "min_duration": None,
            "max_duration": None,
            "run_count": 1,
            "success_rate": 0.0,
            "avg_driver_mem_used_mb": None,
            "avg_executor_mem_peak_mb": None,
            "avg_cpu_pct": None,
            "avg_executors_active": None,
            "avg_jvm_gc_time_ms": None,
            "avg_shuffle_read_bytes": None,
            "avg_shuffle_write_bytes": None,
            "avg_input_bytes": None,
            "avg_output_bytes": None,
            "avg_memory_bytes_spilled": None,
            "avg_disk_bytes_spilled": None,
            "avg_peak_execution_memory": None,
        }

        result = await service.get_resource_metrics(pipeline.id)

        assert result is not None
        # run without duration is excluded
        assert result.recent_runs == []
        assert result.latest_duration_seconds is None

    async def test_date_filtering_passed_to_repo(
        self, service, pipeline_repo, resource_repo, stats_builder
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        resource_repo.get_configs_by_pipeline.return_value = []
        resource_repo.get_recent_runs.return_value = []
        stats_builder.get_run_stats.return_value = {
            "avg_duration": None, "min_duration": None, "max_duration": None,
            "run_count": 0, "success_rate": None,
            "avg_driver_mem_used_mb": None, "avg_executor_mem_peak_mb": None,
            "avg_cpu_pct": None, "avg_executors_active": None,
            "avg_jvm_gc_time_ms": None, "avg_shuffle_read_bytes": None,
            "avg_shuffle_write_bytes": None, "avg_input_bytes": None,
            "avg_output_bytes": None, "avg_memory_bytes_spilled": None,
            "avg_disk_bytes_spilled": None, "avg_peak_execution_memory": None,
        }

        date_from = datetime(2024, 1, 1, tzinfo=UTC)
        date_to = datetime(2024, 1, 31, tzinfo=UTC)

        await service.get_resource_metrics(pipeline.id, date_from=date_from, date_to=date_to)

        resource_repo.get_recent_runs.assert_awaited_once_with(
            pipeline.id, limit=20, date_from=date_from, date_to=date_to,
        )
        stats_builder.get_run_stats.assert_awaited_once_with(
            pipeline.id, date_from=date_from, date_to=date_to,
        )

    async def test_latest_duration_from_first_run_with_duration(
        self, service, pipeline_repo, resource_repo, stats_builder
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        resource_repo.get_configs_by_pipeline.return_value = []
        run1 = make_run(duration_seconds=300.0)
        run2 = make_run(duration_seconds=200.0)
        resource_repo.get_recent_runs.return_value = [run1, run2]
        stats_builder.get_run_stats.return_value = {
            "avg_duration": 250.0, "min_duration": 200.0, "max_duration": 300.0,
            "run_count": 2, "success_rate": 100.0,
            "avg_driver_mem_used_mb": None, "avg_executor_mem_peak_mb": None,
            "avg_cpu_pct": None, "avg_executors_active": None,
            "avg_jvm_gc_time_ms": None, "avg_shuffle_read_bytes": None,
            "avg_shuffle_write_bytes": None, "avg_input_bytes": None,
            "avg_output_bytes": None, "avg_memory_bytes_spilled": None,
            "avg_disk_bytes_spilled": None, "avg_peak_execution_memory": None,
        }

        result = await service.get_resource_metrics(pipeline.id)

        # First run with a duration becomes latest
        assert result.latest_duration_seconds == 300.0

    async def test_dominant_metrics_source_determined(
        self, service, pipeline_repo, resource_repo, stats_builder
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        resource_repo.get_configs_by_pipeline.return_value = []
        runs = [
            make_run(metrics_source="sparkmeasure"),
            make_run(metrics_source="sparkmeasure"),
            make_run(metrics_source="log"),
        ]
        resource_repo.get_recent_runs.return_value = runs
        stats_builder.get_run_stats.return_value = {
            "avg_duration": 100.0, "min_duration": 90.0, "max_duration": 110.0,
            "run_count": 3, "success_rate": 100.0,
            "avg_driver_mem_used_mb": None, "avg_executor_mem_peak_mb": None,
            "avg_cpu_pct": None, "avg_executors_active": None,
            "avg_jvm_gc_time_ms": None, "avg_shuffle_read_bytes": None,
            "avg_shuffle_write_bytes": None, "avg_input_bytes": None,
            "avg_output_bytes": None, "avg_memory_bytes_spilled": None,
            "avg_disk_bytes_spilled": None, "avg_peak_execution_memory": None,
        }

        result = await service.get_resource_metrics(pipeline.id)

        assert result.actual_usage.metrics_source == "sparkmeasure"


# ---------------------------------------------------------------------------
# get_execution_plan
# ---------------------------------------------------------------------------


class TestGetExecutionPlan:
    async def test_returns_none_when_pipeline_not_found(self, service, pipeline_repo):
        pipeline_repo.get_by_id.return_value = None

        result = await service.get_execution_plan(uuid.uuid4())

        assert result is None

    async def test_returns_none_when_no_latest_plan(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        resource_repo.get_latest_execution_plan.return_value = None

        result = await service.get_execution_plan(pipeline.id)

        assert result is None

    async def test_returns_none_when_plan_field_is_none(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        run = make_run(execution_plan=None)
        resource_repo.get_latest_execution_plan.return_value = run

        result = await service.get_execution_plan(pipeline.id)

        assert result is None

    async def test_returns_plan_dict_when_valid_json(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline(task_id="PortScanCollector")
        pipeline_repo.get_by_id.return_value = pipeline

        plan_data = {"type": "Scan", "children": []}
        run = make_run(execution_plan=json.dumps(plan_data))
        resource_repo.get_latest_execution_plan.return_value = run

        result = await service.get_execution_plan(pipeline.id)

        assert result is not None
        assert result["task_id"] == "PortScanCollector"
        assert result["execution_plan"] == plan_data
        assert result["dag_id"] == run.dag_id
        assert result["status"] == run.status

    async def test_returns_none_when_execution_plan_invalid_json(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        run = make_run(execution_plan="{not valid json")
        resource_repo.get_latest_execution_plan.return_value = run

        result = await service.get_execution_plan(pipeline.id)

        assert result is None

    async def test_fetches_specific_run_when_dag_run_id_given(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline

        plan_data = {"type": "Filter", "children": []}
        specific_run = make_run(dag_run_id="specific_run", execution_plan=json.dumps(plan_data))
        resource_repo.get_execution_plan_by_run.return_value = specific_run

        result = await service.get_execution_plan(pipeline.id, dag_run_id="specific_run")

        assert result is not None
        assert result["dag_run_id"] == "specific_run"
        resource_repo.get_execution_plan_by_run.assert_awaited_once_with(
            pipeline.id, "specific_run",
        )
        resource_repo.get_latest_execution_plan.assert_not_awaited()

    async def test_falls_back_to_name_when_task_id_none(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline(name="My Pipeline", task_id=None)
        pipeline.task_id = None
        pipeline_repo.get_by_id.return_value = pipeline

        plan_data = {"type": "Scan", "children": []}
        run = make_run(execution_plan=json.dumps(plan_data))
        resource_repo.get_latest_execution_plan.return_value = run

        result = await service.get_execution_plan(pipeline.id)

        assert result is not None
        assert result["task_id"] == "My Pipeline"


# ---------------------------------------------------------------------------
# get_execution_plan_runs
# ---------------------------------------------------------------------------


class TestGetExecutionPlanRuns:
    async def test_returns_empty_when_pipeline_not_found(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline_repo.get_by_id.return_value = None

        result = await service.get_execution_plan_runs(uuid.uuid4())

        assert result == {"items": [], "total": 0}
        resource_repo.get_execution_plan_runs.assert_not_awaited()

    async def test_returns_paginated_runs(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline

        run1 = make_run(dag_run_id="run_001")
        run2 = make_run(dag_run_id="run_002")
        resource_repo.get_execution_plan_runs.return_value = ([run1, run2], 5)

        result = await service.get_execution_plan_runs(pipeline.id, skip=0, limit=20)

        assert result["total"] == 5
        assert len(result["items"]) == 2

    async def test_passes_skip_and_limit_to_repo(
        self, service, pipeline_repo, resource_repo
    ):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        resource_repo.get_execution_plan_runs.return_value = ([], 0)

        await service.get_execution_plan_runs(pipeline.id, skip=10, limit=5)

        resource_repo.get_execution_plan_runs.assert_awaited_once_with(
            pipeline.id, skip=10, limit=5,
        )


# ---------------------------------------------------------------------------
# _parse_memory_gb (static helper)
# ---------------------------------------------------------------------------


class TestParseMemoryGb:
    def test_parses_gigabytes(self):
        assert ResourceService._parse_memory_gb("8g") == 8.0

    def test_parses_megabytes(self):
        assert ResourceService._parse_memory_gb("512m") == pytest.approx(0.5, rel=1e-3)

    def test_parses_terabytes(self):
        assert ResourceService._parse_memory_gb("2t") == 2048.0

    def test_defaults_to_gigabytes_when_no_unit(self):
        assert ResourceService._parse_memory_gb("16") == 16.0

    def test_returns_zero_for_invalid_format(self):
        assert ResourceService._parse_memory_gb("bad") == 0

    def test_handles_decimal_value(self):
        assert ResourceService._parse_memory_gb("1.5g") == 1.5
