"""Tests for CatalogMirrorService — refreshes the Postgres catalog mirror from Spark Connect."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.catalog_mirror_service import CatalogMirrorService


def make_spark_schema(namespace: str, table_name: str, fields: list[dict]):
    """Create a mock SparkTableSchema."""
    return SimpleNamespace(namespace=namespace, table_name=table_name, fields=fields)


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def service(mock_session):
    return CatalogMirrorService(mock_session)


class TestRefreshFromSpark:
    @patch("app.services.catalog_mirror_service.spark_connect_client")
    async def test_returns_zero_and_leaves_mirror_when_no_schemas(
        self, mock_spark, service, mock_session
    ):
        mock_spark.get_all_schemas = MagicMock(return_value=[])
        service.repo.replace_all = AsyncMock()

        result = await service.refresh_from_spark()

        assert result == 0
        # Mirror left untouched on empty Spark response — no wipe, no commit
        service.repo.replace_all.assert_not_called()
        mock_session.commit.assert_not_awaited()

    @patch("app.services.catalog_mirror_service.spark_connect_client")
    async def test_flattens_schemas_into_rows_and_commits(
        self, mock_spark, service, mock_session
    ):
        mock_spark.get_all_schemas = MagicMock(return_value=[
            make_spark_schema("dagger", "PortScanCollector", [
                {"name": "port_id", "type": "STRING"},
                {"name": "speed_mbps", "type": "INT"},
            ]),
            make_spark_schema("prism", "DeepPacketInspector", [
                {"name": "packet_id", "type": "STRING"},
            ]),
        ])
        service.repo.replace_all = AsyncMock(return_value=3)

        result = await service.refresh_from_spark()

        assert result == 3
        service.repo.replace_all.assert_awaited_once()
        rows = service.repo.replace_all.call_args[0][0]
        assert len(rows) == 3
        # Ordinal positions assigned per-table
        assert rows[0] == {
            "namespace": "dagger",
            "table_name": "PortScanCollector",
            "column_name": "port_id",
            "data_type": "STRING",
            "ordinal_position": 0,
        }
        assert rows[1]["ordinal_position"] == 1
        assert rows[2] == {
            "namespace": "prism",
            "table_name": "DeepPacketInspector",
            "column_name": "packet_id",
            "data_type": "STRING",
            "ordinal_position": 0,
        }
        mock_session.commit.assert_awaited_once()
