"""Tests for CatalogSyncService — Iceberg schema sync to pipelines."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.catalog_sync_service import CatalogSyncService


def make_iceberg_schema(table_name: str, fields: list[dict] | None = None):
    """Create a mock IcebergTableSchema."""
    schema = MagicMock()
    schema.table_name = table_name
    schema.namespace = "dagger"
    schema.fields = fields or []
    return schema


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def service(mock_session):
    return CatalogSyncService(mock_session)


class TestSyncFromCatalog:
    @patch("app.services.catalog_sync_service.iceberg_client")
    async def test_returns_zero_when_no_schemas(self, mock_iceberg, service):
        mock_iceberg.get_all_dagger_schemas.return_value = []
        result = await service.sync_from_catalog()
        assert result == 0

    @patch("app.services.catalog_sync_service.iceberg_client")
    async def test_skips_pipelines_not_in_db(self, mock_iceberg, service, mock_session):
        mock_iceberg.get_all_dagger_schemas.return_value = [
            make_iceberg_schema("UnknownPipeline", [{"name": "col1", "type": "STRING"}]),
        ]
        # Pipeline lookup returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await service.sync_from_catalog()
        assert result == 0

    @patch("app.services.catalog_sync_service.iceberg_client")
    async def test_syncs_fields_for_found_pipeline(self, mock_iceberg, service, mock_session):
        pipeline = MagicMock()
        pipeline.id = uuid.uuid4()
        pipeline.fields = []

        mock_iceberg.get_all_dagger_schemas.return_value = [
            make_iceberg_schema("SwitchPortCollector", [
                {"name": "port_id", "type": "STRING"},
                {"name": "speed_mbps", "type": "INT"},
            ]),
        ]
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pipeline
        mock_session.execute.return_value = mock_result

        result = await service.sync_from_catalog()
        assert result == 1
        # Should have added 2 PipelineField objects
        assert mock_session.add.call_count == 2


class TestTableToDisplayName:
    def test_converts_snake_case(self):
        assert CatalogSyncService._table_to_display_name("shopify_sales_sync") == "Shopify Sales Sync"

    def test_single_word(self):
        assert CatalogSyncService._table_to_display_name("inventory") == "Inventory"
