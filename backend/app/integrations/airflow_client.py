"""Airflow REST API client with retry, graceful degradation, and TTL caching."""

import logging
import time
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
_CACHE_TTL = 300


class _TTLCache:
    """Simple TTL cache for Airflow API responses."""

    def __init__(self, ttl: int = _CACHE_TTL):
        self._ttl = ttl
        self._store: dict[str, tuple[float, object]] = {}

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, value = entry
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: object) -> None:
        self._store[key] = (time.monotonic(), value)

    def clear(self) -> None:
        self._store.clear()


class AirflowClient:
    def __init__(self):
        self.base_url = settings.airflow_base_url.rstrip("/")
        self.auth = (settings.airflow_username, settings.airflow_password)
        self.timeout = httpx.Timeout(10.0)
        self._connected = False
        self._cache = _TTLCache()

    async def _request(self, method: str, path: str, **kwargs) -> dict | None:
        url = f"{self.base_url}{path}"
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.request(
                        method, url, auth=self.auth, **kwargs
                    )
                    resp.raise_for_status()
                    self._connected = True
                    return resp.json()
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                logger.warning(
                    "Airflow request failed (attempt %d): %s %s -> %s",
                    attempt + 1, method, path, e,
                )
                if attempt == 1:
                    self._connected = False
                    return None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def check_health(self) -> bool:
        result = await self._request("GET", "/health")
        return result is not None

    async def get_dag_runs(self, dag_id: str, limit: int = 1) -> list[dict]:
        """Get recent DAG runs for a specific DAG."""
        result = await self._request(
            "GET",
            f"/dags/{dag_id}/dagRuns",
            params={"order_by": "-execution_date", "limit": limit},
        )
        if result and "dag_runs" in result:
            return result["dag_runs"]
        return []

    async def get_all_dags(self) -> list[dict]:
        """List all DAGs from Airflow with pagination. Cached for 5 minutes."""
        cached = self._cache.get("all_dags")
        if cached is not None:
            return cached

        all_dags = []
        offset = 0
        limit = 100
        while True:
            result = await self._request(
                "GET", "/dags", params={"limit": limit, "offset": offset}
            )
            if not result or "dags" not in result:
                break
            dags = result["dags"]
            all_dags.extend(dags)
            if len(dags) < limit:
                break
            offset += limit

        if all_dags:
            self._cache.set("all_dags", all_dags)
        return all_dags

    async def get_task_instances(self, dag_id: str, dag_run_id: str) -> list[dict]:
        """Get task instances for a specific DAG run."""
        result = await self._request(
            "GET",
            f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances",
        )
        if result and "task_instances" in result:
            return result["task_instances"]
        return []

    async def get_dag_tasks(self, dag_id: str) -> list[dict]:
        """Get task definitions for a DAG (includes downstream_task_ids). Cached for 5 minutes."""
        cache_key = f"dag_tasks:{dag_id}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        result = await self._request("GET", f"/dags/{dag_id}/tasks")
        tasks = result.get("tasks", []) if result else []
        if tasks:
            self._cache.set(cache_key, tasks)
        return tasks

    async def get_task_log(
        self, dag_id: str, dag_run_id: str, task_id: str, try_number: int = 1
    ) -> str:
        """Fetch the log content for a specific task instance attempt."""
        url = (
            f"{self.base_url}/dags/{dag_id}/dagRuns/{dag_run_id}"
            f"/taskInstances/{task_id}/logs/{try_number}"
        )
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    url,
                    auth=self.auth,
                    headers={"Accept": "text/plain"},
                )
                resp.raise_for_status()
                return resp.text
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.debug("Failed to fetch task log %s/%s/%s: %s", dag_id, dag_run_id, task_id, e)
            return ""

    async def get_latest_dag_run_status(self, dag_id: str) -> dict:
        """Get the latest run status for a DAG. Returns status dict."""
        runs = await self.get_dag_runs(dag_id, limit=1)
        if runs:
            run = runs[0]
            state = run.get("state", "unknown")
            exec_date_str = run.get("execution_date")
            exec_date = None
            if exec_date_str:
                try:
                    exec_date = datetime.fromisoformat(exec_date_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            return {
                "status": state,
                "execution_date": exec_date,
                "dag_id": dag_id,
            }
        return {"status": "unknown", "execution_date": None, "dag_id": dag_id}


airflow_client = AirflowClient()
