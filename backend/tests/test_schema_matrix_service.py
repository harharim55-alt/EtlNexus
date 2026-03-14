"""Tests for SchemaMatrixService — field frequency matrix with caching."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.cache import schema_matrix_cache
from app.services.schema_matrix_service import SchemaMatrixService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def field_freq_repo():
    return AsyncMock()


@pytest.fixture
def service(field_freq_repo):
    return SchemaMatrixService(field_freq_repo)


@pytest.fixture(autouse=True)
def clear_cache():
    schema_matrix_cache.clear()
    yield
    schema_matrix_cache.clear()


# ---------------------------------------------------------------------------
# get_schema_matrix
# ---------------------------------------------------------------------------


class TestGetSchemaMatrix:
    async def test_returns_fields_and_total(self, service, field_freq_repo):
        pid = str(uuid.uuid4())
        frequencies = [
            {
                "field_name": "ip_address",
                "frequency": 5,
                "pipelines": [{"pipeline_id": pid, "pipeline_name": "Switch Port Collector"}],
            },
        ]
        field_freq_repo.get_field_frequencies.return_value = (frequencies, 1)

        result = await service.get_schema_matrix()

        assert result.total == 1
        assert len(result.fields) == 1
        assert result.fields[0].field_name == "ip_address"
        assert result.fields[0].frequency == 5
        assert len(result.fields[0].pipelines) == 1
        assert result.fields[0].pipelines[0].pipeline_id == pid

    async def test_returns_empty_list_when_no_fields(self, service, field_freq_repo):
        field_freq_repo.get_field_frequencies.return_value = ([], 0)

        result = await service.get_schema_matrix()

        assert result.total == 0
        assert result.fields == []

    async def test_passes_skip_and_limit_to_repo(self, service, field_freq_repo):
        field_freq_repo.get_field_frequencies.return_value = ([], 0)

        await service.get_schema_matrix(skip=50, limit=100)

        field_freq_repo.get_field_frequencies.assert_awaited_once_with(skip=50, limit=100)

    async def test_default_pagination_values(self, service, field_freq_repo):
        field_freq_repo.get_field_frequencies.return_value = ([], 0)

        await service.get_schema_matrix()

        field_freq_repo.get_field_frequencies.assert_awaited_once_with(skip=0, limit=200)

    async def test_result_is_cached(self, service, field_freq_repo):
        field_freq_repo.get_field_frequencies.return_value = ([], 0)

        await service.get_schema_matrix()
        await service.get_schema_matrix()

        # Second call hits cache — repo only called once
        assert field_freq_repo.get_field_frequencies.await_count == 1

    async def test_different_pagination_uses_separate_cache_keys(self, service, field_freq_repo):
        field_freq_repo.get_field_frequencies.return_value = ([], 0)

        await service.get_schema_matrix(skip=0, limit=100)
        await service.get_schema_matrix(skip=100, limit=100)

        assert field_freq_repo.get_field_frequencies.await_count == 2

    async def test_multiple_fields_in_response(self, service, field_freq_repo):
        pid1 = str(uuid.uuid4())
        pid2 = str(uuid.uuid4())
        frequencies = [
            {
                "field_name": "ip_address",
                "frequency": 8,
                "pipelines": [
                    {"pipeline_id": pid1, "pipeline_name": "Collector A"},
                    {"pipeline_id": pid2, "pipeline_name": "Collector B"},
                ],
            },
            {
                "field_name": "mac_address",
                "frequency": 3,
                "pipelines": [
                    {"pipeline_id": pid1, "pipeline_name": "Collector A"},
                ],
            },
        ]
        field_freq_repo.get_field_frequencies.return_value = (frequencies, 2)

        result = await service.get_schema_matrix()

        assert result.total == 2
        assert result.fields[0].field_name == "ip_address"
        assert result.fields[0].frequency == 8
        assert len(result.fields[0].pipelines) == 2
        assert result.fields[1].field_name == "mac_address"
        assert result.fields[1].frequency == 3
        assert len(result.fields[1].pipelines) == 1
