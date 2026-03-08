"""Airflow REST API client with retry and graceful degradation."""

import logging
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AirflowClient:
    def __init__(self):
        self.base_url = settings.airflow_base_url.rstrip("/")
        self.auth = (settings.airflow_username, settings.airflow_password)
        self.timeout = httpx.Timeout(10.0)
        self._connected = False

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
        """List all DAGs from Airflow."""
        result = await self._request(
            "GET", "/dags", params={"limit": 100}
        )
        if result and "dags" in result:
            return result["dags"]
        return []

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
