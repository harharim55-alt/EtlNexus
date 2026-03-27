"""Tests for AirflowClient — retry behavior, caching, and response parsing."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.integrations.airflow_client import AirflowClient, strip_group_prefix


class TestStripGroupPrefix:
    def test_strips_single_prefix(self):
        assert strip_group_prefix("Dagger.PortScanCollector") == "PortScanCollector"

    def test_strips_compound_prefix(self):
        assert strip_group_prefix("Dagger - Collection.PortScanCollector") == "PortScanCollector"

    def test_no_prefix_passthrough(self):
        assert strip_group_prefix("PortScanCollector") == "PortScanCollector"

    def test_multiple_dots_takes_last(self):
        assert strip_group_prefix("A.B.C") == "C"

    def test_empty_string(self):
        assert strip_group_prefix("") == ""


@pytest.fixture
def client():
    """Create an AirflowClient with mocked httpx client."""
    with patch.object(AirflowClient, "__init__", lambda self: None):
        c = AirflowClient.__new__(AirflowClient)
        c.base_url = "http://airflow:8080/api/v1"
        c.auth = ("admin", "admin")
        c.timeout = httpx.Timeout(10.0)
        c._connected = False
        c._cache = MagicMock()
        c._cache.get.return_value = None  # no cache hits by default
        c._client = AsyncMock()
        c._consecutive_failures = 0
        c._circuit_open_until = 0.0
        return c


def make_response(json_data: dict, status_code: int = 200):
    """Create a mock httpx Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp,
        )
    return resp


class TestRequest:
    async def test_successful_request_returns_json(self, client):
        client._client.request = AsyncMock(
            return_value=make_response({"ok": True})
        )

        result = await client._request("GET", "/health")
        assert result == {"ok": True}
        assert client._connected is True

    async def test_retries_once_on_failure(self, client):
        fail_resp = make_response({}, 500)
        ok_resp = make_response({"ok": True})
        client._client.request = AsyncMock(side_effect=[fail_resp, ok_resp])

        result = await client._request("GET", "/health")
        assert result == {"ok": True}
        assert client._client.request.await_count == 2

    async def test_returns_none_after_three_failures(self, client):
        fail_resp = make_response({}, 500)
        client._client.request = AsyncMock(side_effect=[fail_resp, fail_resp, fail_resp])

        result = await client._request("GET", "/health")
        assert result is None
        assert client._connected is False

    async def test_handles_connection_error(self, client):
        client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )

        result = await client._request("GET", "/health")
        assert result is None
        assert client._connected is False


class TestCheckHealth:
    async def test_returns_true_on_success(self, client):
        client._client.request = AsyncMock(
            return_value=make_response({"status": "healthy"})
        )
        assert await client.check_health() is True

    async def test_returns_false_on_failure(self, client):
        client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )
        assert await client.check_health() is False


class TestGetDagRuns:
    async def test_returns_dag_runs_list(self, client):
        client._client.request = AsyncMock(
            return_value=make_response({
                "dag_runs": [{"dag_run_id": "run1"}, {"dag_run_id": "run2"}]
            })
        )

        result = await client.get_dag_runs("network_recon", limit=2)
        assert len(result) == 2
        assert result[0]["dag_run_id"] == "run1"

    async def test_returns_empty_on_failure(self, client):
        client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )
        result = await client.get_dag_runs("network_recon")
        assert result == []


class TestGetAllDags:
    async def test_returns_cached_result(self, client):
        cached_dags = [{"dag_id": "dag1"}]
        client._cache.get.return_value = cached_dags

        result = await client.get_all_dags()
        assert result == cached_dags
        client._client.request.assert_not_awaited()

    async def test_fetches_and_caches_dags(self, client):
        client._client.request = AsyncMock(
            return_value=make_response({
                "dags": [{"dag_id": "dag1"}, {"dag_id": "dag2"}]
            })
        )

        result = await client.get_all_dags()
        assert len(result) == 2
        client._cache.set.assert_called_once_with(
            "all_dags", [{"dag_id": "dag1"}, {"dag_id": "dag2"}]
        )

    async def test_paginates_when_more_than_limit(self, client):
        # First page: 100 dags (full page)
        page1 = make_response({"dags": [{"dag_id": f"dag_{i}"} for i in range(100)]})
        # Second page: 5 dags (partial page = last page)
        page2 = make_response({"dags": [{"dag_id": f"dag_{100+i}"} for i in range(5)]})
        client._client.request = AsyncMock(side_effect=[page1, page2])

        result = await client.get_all_dags()
        assert len(result) == 105
        assert client._client.request.await_count == 2


class TestGetTaskInstances:
    async def test_returns_instances_list(self, client):
        client._client.request = AsyncMock(
            return_value=make_response({
                "task_instances": [{"task_id": "t1", "state": "success"}]
            })
        )

        result = await client.get_task_instances("dag1", "run1")
        assert len(result) == 1
        assert result[0]["task_id"] == "t1"

    async def test_returns_empty_on_failure(self, client):
        client._client.request = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )
        result = await client.get_task_instances("dag1", "run1")
        assert result == []


class TestGetDagTasks:
    async def test_returns_cached_tasks(self, client):
        cached = [{"task_id": "t1"}]
        client._cache.get.return_value = cached

        result = await client.get_dag_tasks("dag1")
        assert result == cached

    async def test_fetches_and_caches_tasks(self, client):
        client._client.request = AsyncMock(
            return_value=make_response({
                "tasks": [{"task_id": "t1"}, {"task_id": "t2"}]
            })
        )

        result = await client.get_dag_tasks("dag1")
        assert len(result) == 2
        client._cache.set.assert_called_once()
