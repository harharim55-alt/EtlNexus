"""Tests for CatalogSyncService — projects the Postgres catalog mirror onto pipeline fields."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.catalog_sync_service import CatalogSyncService


def make_mirror_col(table_name: str, column_name: str, data_type: str, ordinal: int):
    """Create a mock CatalogColumn mirror row."""
    return SimpleNamespace(
        table_name=table_name,
        column_name=column_name,
        data_type=data_type,
        ordinal_position=ordinal,
    )


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
    @patch("app.services.catalog_sync_service.CatalogMirrorRepository")
    async def test_returns_zero_when_mirror_empty(self, mock_repo_cls, service):
        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[])
        mock_repo_cls.return_value = mock_repo

        result = await service.sync_from_catalog()
        assert result == 0

    @patch("app.services.catalog_sync_service.CatalogMirrorRepository")
    async def test_skips_pipelines_not_in_db(self, mock_repo_cls, service, mock_session):
        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[
            make_mirror_col("UnknownPipeline", "col1", "STRING", 0),
        ])
        mock_repo_cls.return_value = mock_repo

        # Bulk pipeline lookup returns empty (no matching pipelines)
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await service.sync_from_catalog()
        assert result == 0

    @patch("app.services.catalog_sync_service.CatalogMirrorRepository")
    async def test_syncs_fields_for_found_pipeline(self, mock_repo_cls, service, mock_session):
        pipeline = MagicMock()
        pipeline.id = uuid.uuid4()
        pipeline.task_id = "PortScanCollector"
        pipeline.schema_manually_edited = False
        pipeline.fields = []

        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[
            make_mirror_col("PortScanCollector", "port_id", "STRING", 0),
            make_mirror_col("PortScanCollector", "speed_mbps", "INT", 1),
        ])
        mock_repo_cls.return_value = mock_repo

        # Bulk pipeline lookup returns the matching pipeline
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [pipeline]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await service.sync_from_catalog()
        assert result == 1
        # Should have batch-added 2 PipelineField objects via add_all
        mock_session.add_all.assert_called_once()
        added_fields = mock_session.add_all.call_args[0][0]
        assert len(added_fields) == 2

    @patch("app.services.catalog_sync_service.CatalogMirrorRepository")
    async def test_skips_manually_edited_schema(self, mock_repo_cls, service, mock_session):
        pipeline = MagicMock()
        pipeline.id = uuid.uuid4()
        pipeline.task_id = "PortScanCollector"
        pipeline.schema_manually_edited = True
        pipeline.fields = []

        mock_repo = MagicMock()
        mock_repo.list_all = AsyncMock(return_value=[
            make_mirror_col("PortScanCollector", "port_id", "STRING", 0),
        ])
        mock_repo_cls.return_value = mock_repo

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [pipeline]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        result = await service.sync_from_catalog()
        assert result == 0
        mock_session.add_all.assert_not_called()


class TestTableToDisplayName:
    def test_converts_snake_case(self):
        assert CatalogSyncService._table_to_display_name("shopify_sales_sync") == "Shopify Sales Sync"

    def test_single_word(self):
        assert CatalogSyncService._table_to_display_name("inventory") == "Inventory"
