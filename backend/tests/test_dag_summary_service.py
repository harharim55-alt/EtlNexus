"""Tests for DagSummaryService — per-DAG statistics and aggregate metrics."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cache import dag_summary_cache
from app.services.dag_summary_service import DagSummaryService, _period_label

# patch target for ResourceStatsBuilder used inside DagSummaryService
_STATS_PATCH = "app.services.dag_summary_service.ResourceStatsBuilder"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_airflow_dag_info(
    *,
    dag_id: str = "network_recon",
    is_paused: bool = False,
    description: str | None = None,
    schedule_interval: str | None = "0 6 * * *",
):
    return {
        "dag_id": dag_id,
        "is_paused": is_paused,
        "description": description,
        "schedule_interval": schedule_interval,
    }


def make_run_history(
    *,
    pipeline_id: str | None = None,
    duration_seconds: float | None = 120.0,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    status: str = "success",
    dag_id: str = "network_recon",
):
    r = MagicMock()
    r.pipeline_id = pipeline_id
    r.duration_seconds = duration_seconds
    r.start_date = start_date or datetime(2024, 1, 1, 6, 0, tzinfo=UTC)
    r.end_date = end_date or datetime(2024, 1, 1, 6, 2, tzinfo=UTC)
    r.status = status
    r.dag_id = dag_id
    return r


def make_dag_task_with_pipeline(
    *,
    task_id: str = "PortScanCollector",
    dag_id: str = "network_recon",
    pipeline_id: str | None = None,
    task_group_id: str | None = "DaggerCollection",
    pipeline_name: str = "Port Scan Collector",
):
    dt = MagicMock()
    dt.task_id = task_id
    dt.dag_id = dag_id
    dt.pipeline_id = pipeline_id
    dt.task_group_id = task_group_id
    pipeline = MagicMock()
    pipeline.name = pipeline_name
    dt.pipeline = pipeline
    return dt


def make_airflow_status(*, pipeline_id: str, status: str = "success"):
    s = MagicMock()
    s.pipeline_id = pipeline_id
    s.status = status
    return s


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dag_task_repo():
    return AsyncMock()


@pytest.fixture
def resource_repo():
    return AsyncMock()


@pytest.fixture
def airflow_repo():
    return AsyncMock()


@pytest.fixture
def stats_builder():
    return AsyncMock()


@pytest.fixture
def service(dag_task_repo, resource_repo, airflow_repo, stats_builder):
    with patch(_STATS_PATCH, return_value=stats_builder):
        svc = DagSummaryService(dag_task_repo, resource_repo, airflow_repo)
    return svc


@pytest.fixture(autouse=True)
def clear_cache():
    dag_summary_cache.clear()
    yield
    dag_summary_cache.clear()


# ---------------------------------------------------------------------------
# _period_label helper
# ---------------------------------------------------------------------------


class TestPeriodLabel:
    def test_no_date_from_returns_30d(self):
        assert _period_label(None, None) == "30d"

    def test_no_date_to_returns_custom(self):
        assert _period_label(datetime(2024, 1, 1, tzinfo=UTC), None) == "custom"

    def test_24h_range(self):
        d1 = datetime(2024, 1, 1, tzinfo=UTC)
        d2 = datetime(2024, 1, 1, 23, 59, tzinfo=UTC)
        assert _period_label(d1, d2) == "24h"

    def test_7d_range(self):
        d1 = datetime(2024, 1, 1, tzinfo=UTC)
        d2 = datetime(2024, 1, 7, tzinfo=UTC)
        assert _period_label(d1, d2) == "7d"

    def test_30d_range(self):
        d1 = datetime(2024, 1, 1, tzinfo=UTC)
        d2 = datetime(2024, 1, 30, tzinfo=UTC)
        assert _period_label(d1, d2) == "30d"

    def test_90d_range(self):
        d1 = datetime(2024, 1, 1, tzinfo=UTC)
        d2 = datetime(2024, 3, 31, tzinfo=UTC)  # 89 days — within 90d bucket
        assert _period_label(d1, d2) == "90d"

    def test_over_90d_returns_custom(self):
        d1 = datetime(2024, 1, 1, tzinfo=UTC)
        d2 = datetime(2024, 12, 31, tzinfo=UTC)
        assert _period_label(d1, d2) == "custom"


# ---------------------------------------------------------------------------
# get_dag_summaries
# ---------------------------------------------------------------------------


class TestGetDagSummaries:
    async def test_returns_empty_when_no_dags(
        self, service, dag_task_repo, resource_repo, airflow_repo
    ):
        dag_task_repo.get_all_dag_ids.return_value = []
        dag_task_repo.count_tasks_per_dag.return_value = {}
        dag_task_repo.count_pipelines_per_dag.return_value = {}
        airflow_repo.get_all.return_value = []

        with patch(
            "app.services.dag_summary_service.airflow_client.get_all_dags",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_dag_summaries()

        assert result.aggregate.total_dags == 0
        assert result.dags == []

    async def test_returns_per_dag_stats(
        self, service, dag_task_repo, resource_repo, airflow_repo, stats_builder
    ):
        dag_task_repo.get_all_dag_ids.return_value = ["network_recon"]
        dag_task_repo.count_tasks_per_dag.return_value = {"network_recon": 5}
        dag_task_repo.count_pipelines_per_dag.return_value = {"network_recon": 4}

        task = make_dag_task_with_pipeline()
        dag_task_repo.get_tasks_for_dags_with_pipeline.return_value = {"network_recon": [task]}

        run = make_run_history()
        stats_builder.get_dag_run_stats_batch.return_value = {
            "network_recon": {
                "dag_run_count": 10,
                "avg_duration": 120.0,
                "success_rate": 90.0,
            },
        }
        resource_repo.get_latest_runs_by_dags.return_value = {"network_recon": [run]}
        stats_builder.get_typical_finish_hours_batch.return_value = {"network_recon": "06:00"}

        airflow_repo.get_all.return_value = []

        with patch(
            "app.services.dag_summary_service.airflow_client.get_all_dags",
            new_callable=AsyncMock,
            return_value=[make_airflow_dag_info(dag_id="network_recon")],
        ):
            result = await service.get_dag_summaries()

        assert result.aggregate.total_dags == 1
        assert result.aggregate.total_pipelines == 4
        assert len(result.dags) == 1
        dag = result.dags[0]
        assert dag.dag_id == "network_recon"
        assert dag.task_count == 5
        assert dag.pipeline_count == 4
        assert dag.total_runs_30d == 10

    async def test_calculates_success_rate(
        self, service, dag_task_repo, resource_repo, airflow_repo, stats_builder
    ):
        dag_task_repo.get_all_dag_ids.return_value = ["test_dag"]
        dag_task_repo.count_tasks_per_dag.return_value = {"test_dag": 4}
        dag_task_repo.count_pipelines_per_dag.return_value = {"test_dag": 4}

        # 3 of 4 tasks are success
        import uuid as _uuid
        pid1 = str(_uuid.uuid4())
        pid2 = str(_uuid.uuid4())
        pid3 = str(_uuid.uuid4())
        pid4 = str(_uuid.uuid4())

        tasks = [
            make_dag_task_with_pipeline(task_id=f"Task{i}", pipeline_id=p)
            for i, p in enumerate([pid1, pid2, pid3, pid4], 1)
        ]
        dag_task_repo.get_tasks_for_dags_with_pipeline.return_value = {"test_dag": tasks}

        statuses = [
            make_airflow_status(pipeline_id=pid1, status="success"),
            make_airflow_status(pipeline_id=pid2, status="success"),
            make_airflow_status(pipeline_id=pid3, status="success"),
            make_airflow_status(pipeline_id=pid4, status="failed"),
        ]
        airflow_repo.get_all.return_value = statuses

        stats_builder.get_dag_run_stats_batch.return_value = {
            "test_dag": {"dag_run_count": 5, "avg_duration": None, "success_rate": None},
        }
        resource_repo.get_latest_runs_by_dags.return_value = {"test_dag": []}
        stats_builder.get_typical_finish_hours_batch.return_value = {"test_dag": None}

        with patch(
            "app.services.dag_summary_service.airflow_client.get_all_dags",
            new_callable=AsyncMock,
            return_value=[make_airflow_dag_info(dag_id="test_dag")],
        ):
            result = await service.get_dag_summaries()

        dag = result.dags[0]
        assert dag.success_rate == 75.0

    async def test_paused_dags_excluded_from_active_count(
        self, service, dag_task_repo, resource_repo, airflow_repo, stats_builder
    ):
        dag_task_repo.get_all_dag_ids.return_value = ["active_dag", "paused_dag"]
        dag_task_repo.count_tasks_per_dag.return_value = {
            "active_dag": 3, "paused_dag": 2,
        }
        dag_task_repo.count_pipelines_per_dag.return_value = {
            "active_dag": 3, "paused_dag": 2,
        }
        dag_task_repo.get_tasks_for_dags_with_pipeline.return_value = {}
        airflow_repo.get_all.return_value = []
        stats_builder.get_dag_run_stats_batch.return_value = {}
        resource_repo.get_latest_runs_by_dags.return_value = {}
        stats_builder.get_typical_finish_hours_batch.return_value = {}

        with patch(
            "app.services.dag_summary_service.airflow_client.get_all_dags",
            new_callable=AsyncMock,
            return_value=[
                make_airflow_dag_info(dag_id="active_dag", is_paused=False),
                make_airflow_dag_info(dag_id="paused_dag", is_paused=True),
            ],
        ):
            result = await service.get_dag_summaries()

        assert result.aggregate.total_dags == 2
        assert result.aggregate.active_dags == 1

    async def test_result_is_cached(
        self, service, dag_task_repo, resource_repo, airflow_repo, stats_builder
    ):
        dag_task_repo.get_all_dag_ids.return_value = []
        dag_task_repo.count_tasks_per_dag.return_value = {}
        dag_task_repo.count_pipelines_per_dag.return_value = {}
        airflow_repo.get_all.return_value = []
        stats_builder.get_dag_run_stats_batch.return_value = {}
        resource_repo.get_latest_runs_by_dags.return_value = {}
        stats_builder.get_typical_finish_hours_batch.return_value = {}
        dag_task_repo.get_tasks_for_dags_with_pipeline.return_value = {}

        with patch(
            "app.services.dag_summary_service.airflow_client.get_all_dags",
            new_callable=AsyncMock,
            return_value=[],
        ):
            await service.get_dag_summaries()
            await service.get_dag_summaries()

        assert dag_task_repo.get_all_dag_ids.await_count == 1

    async def test_schedule_interval_dict_format(
        self, service, dag_task_repo, resource_repo, airflow_repo, stats_builder
    ):
        dag_task_repo.get_all_dag_ids.return_value = ["test_dag"]
        dag_task_repo.count_tasks_per_dag.return_value = {"test_dag": 0}
        dag_task_repo.count_pipelines_per_dag.return_value = {"test_dag": 0}
        dag_task_repo.get_tasks_for_dags_with_pipeline.return_value = {}
        airflow_repo.get_all.return_value = []
        stats_builder.get_dag_run_stats_batch.return_value = {}
        resource_repo.get_latest_runs_by_dags.return_value = {}
        stats_builder.get_typical_finish_hours_batch.return_value = {}

        with patch(
            "app.services.dag_summary_service.airflow_client.get_all_dags",
            new_callable=AsyncMock,
            return_value=[{
                "dag_id": "test_dag",
                "is_paused": False,
                "description": None,
                "schedule_interval": {"value": "0 0 * * *", "__type": "CronDataIntervalTimetable"},
            }],
        ):
            result = await service.get_dag_summaries()

        assert result.dags[0].schedule_interval == "0 0 * * *"

    async def test_period_label_propagated_to_response(
        self, service, dag_task_repo, resource_repo, airflow_repo
    ):
        dag_task_repo.get_all_dag_ids.return_value = []
        dag_task_repo.count_tasks_per_dag.return_value = {}
        dag_task_repo.count_pipelines_per_dag.return_value = {}
        airflow_repo.get_all.return_value = []

        date_from = datetime(2024, 1, 1, tzinfo=UTC)
        date_to = datetime(2024, 1, 7, tzinfo=UTC)

        with patch(
            "app.services.dag_summary_service.airflow_client.get_all_dags",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await service.get_dag_summaries(date_from=date_from, date_to=date_to)

        assert result.aggregate.period_label == "7d"
