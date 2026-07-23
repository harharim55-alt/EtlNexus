"""Tests for TableService — listing from the metrics repo + on-demand Spark schema."""

from unittest.mock import AsyncMock, patch

import pytest

from app.cache import table_schema_cache
from app.integrations.spark_connect_client import SparkTableSchema
from app.services.table_service import TableService


@pytest.fixture(autouse=True)
def clear_cache():
    table_schema_cache.clear()
    yield
    table_schema_cache.clear()


@pytest.fixture
def metrics_repo():
    return AsyncMock()


@pytest.fixture
def service(metrics_repo):
    return TableService(metrics_repo)


class TestListTables:
    async def test_maps_pairs_to_items(self, service, metrics_repo):
        metrics_repo.list_tables.return_value = [("vault", "logins"), ("prism", "events")]
        items = await service.list_tables()
        assert [(i.namespace, i.table_name) for i in items] == [
            ("vault", "logins"),
            ("prism", "events"),
        ]


class TestGetTableSchema:
    async def test_reads_live_and_caches(self, service):
        spark_schema = SparkTableSchema(
            table_name="logins",
            namespace="vault",
            fields=[{"name": "id", "type": "BIGINT"}, {"name": "ts", "type": "TIMESTAMP"}],
        )
        with patch(
            "app.services.table_service.spark_connect_client.get_table_schema",
            return_value=spark_schema,
        ) as mock_get:
            result = await service.get_table_schema("vault", "logins")
            # Second call should be served from cache (no extra Spark call).
            await service.get_table_schema("vault", "logins")

        assert [c.name for c in result.columns] == ["id", "ts"]
        assert result.consume_snippet  # rendered from the env template
        assert mock_get.call_count == 1

    async def test_returns_none_when_spark_returns_none(self, service):
        with patch(
            "app.services.table_service.spark_connect_client.get_table_schema",
            return_value=None,
        ):
            assert await service.get_table_schema("vault", "missing") is None

    async def test_unsafe_identifier_returns_none(self, service):
        with patch(
            "app.services.table_service.spark_connect_client.get_table_schema",
            side_effect=ValueError("unsafe"),
        ):
            assert await service.get_table_schema("vault", "bad;name") is None
