"""Tests for batch pipeline upsert methods (PERF-H05).

Covers:
- PipelineRepository.bulk_upsert_pipelines()
- PipelineRepository.bulk_set_teams()
- LineageRepository.delete_by_pipeline_ids()

All tests use mock AsyncSession and ORM objects so no real DB is needed.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.models.lineage import LineageEdge
from app.models.pipeline import Pipeline
from app.repositories.lineage_repo import LineageRepository
from app.repositories.pipeline_repo import PipelineRepository
from tests.conftest import make_pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scalars_result(objects: list) -> MagicMock:
    """Return a mock execute() result whose .scalars().all() yields ``objects``."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = objects
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    return result_mock


# ---------------------------------------------------------------------------
# PipelineRepository.bulk_upsert_pipelines
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def pipeline_repo(mock_session):
    return PipelineRepository(mock_session)


@pytest.fixture
def lineage_repo(mock_session):
    return LineageRepository(mock_session)


class TestBulkUpsertPipelinesEmpty:
    async def test_returns_empty_dict_for_no_entries(self, pipeline_repo):
        result = await pipeline_repo.bulk_upsert_pipelines([])
        assert result == {}
        pipeline_repo.session.execute.assert_not_called()
        pipeline_repo.session.flush.assert_not_called()

    async def test_no_db_calls_for_empty_input(self, pipeline_repo):
        """Verify we short-circuit before any SQL when entries is empty."""
        await pipeline_repo.bulk_upsert_pipelines([])
        assert pipeline_repo.session.execute.await_count == 0


class TestBulkUpsertPipelinesAllExistByName:
    async def test_updates_existing_pipelines_in_memory(self, pipeline_repo):
        existing = make_pipeline(name="Port Scan Collector", task_id="PortScanCollector")
        existing.description = "Old description"
        existing.description_edited_by_user = False
        existing.category = "Old"
        existing.schedule = "weekly"
        # __table__ must exist for apply_updates column guard
        existing.__table__ = MagicMock()
        existing.__table__.columns = [
            MagicMock(key="task_id"),
            MagicMock(key="description"),
            MagicMock(key="category"),
            MagicMock(key="schedule"),
        ]

        # First execute (by name) returns existing; second (by task_id for unmatched) not called
        pipeline_repo.session.execute.return_value = _make_scalars_result([existing])

        entries = [{
            "name": "Port Scan Collector",
            "task_id": "PortScanCollector",
            "description": "New description",
            "category": "Network",
            "schedule": "daily",
        }]
        result = await pipeline_repo.bulk_upsert_pipelines(entries)

        assert "PortScanCollector" in result
        assert result["PortScanCollector"] is existing
        # flush was called once after updates
        pipeline_repo.session.flush.assert_awaited_once()

    async def test_preserves_user_edited_description(self, pipeline_repo):
        """description_edited_by_user=True must block overwriting the description."""
        existing = make_pipeline(name="My Pipeline", task_id="MyPipeline")
        existing.description = "Manually written by user"
        existing.description_edited_by_user = True
        existing.__table__ = MagicMock()
        existing.__table__.columns = [
            MagicMock(key="task_id"),
            MagicMock(key="description"),
            MagicMock(key="category"),
            MagicMock(key="schedule"),
        ]

        pipeline_repo.session.execute.return_value = _make_scalars_result([existing])

        entries = [{
            "name": "My Pipeline",
            "task_id": "MyPipeline",
            "description": "Airflow-sourced description",
            "category": "Analytics",
            "schedule": "daily",
        }]
        await pipeline_repo.bulk_upsert_pipelines(entries)

        # Description must NOT be overwritten
        assert existing.description == "Manually written by user"

    async def test_skips_entries_without_task_id(self, pipeline_repo):
        existing = make_pipeline(name="No Task Pipeline", task_id=None)
        existing.description_edited_by_user = False
        existing.__table__ = MagicMock()
        existing.__table__.columns = [MagicMock(key="description")]

        pipeline_repo.session.execute.return_value = _make_scalars_result([existing])

        entries = [{"name": "No Task Pipeline", "description": "desc"}]
        result = await pipeline_repo.bulk_upsert_pipelines(entries)

        # No task_id key means nothing appears in the returned map
        assert result == {}


class TestBulkUpsertPipelinesNewPipelines:
    async def test_inserts_new_pipeline_and_refetches(self, pipeline_repo):
        """Newly inserted pipelines are re-fetched and returned in the map.

        execute() call order for a fully-new pipeline:
          1. SELECT by name          -> empty
          2. SELECT by task_id       -> empty  (fallback for unmatched names)
          3. INSERT ON CONFLICT ...  -> rowcount mock
          4. SELECT re-fetch         -> [new_pipeline]
        """
        new_pipeline = make_pipeline(name="Brand New", task_id="BrandNew")
        new_pipeline.description_edited_by_user = False
        new_pipeline.__table__ = MagicMock()
        new_pipeline.__table__.columns = [
            MagicMock(key="task_id"),
            MagicMock(key="description"),
            MagicMock(key="category"),
            MagicMock(key="schedule"),
        ]

        empty_result = _make_scalars_result([])
        insert_result = MagicMock()  # pg_insert result — no .scalars() used
        refetch_result = _make_scalars_result([new_pipeline])
        pipeline_repo.session.execute.side_effect = [
            empty_result,   # 1. SELECT by name
            empty_result,   # 2. SELECT by task_id (fallback)
            insert_result,  # 3. INSERT ON CONFLICT DO NOTHING
            refetch_result, # 4. re-fetch new names
        ]

        entries = [{
            "name": "Brand New",
            "task_id": "BrandNew",
            "description": "Fresh pipeline",
            "category": "Test",
            "schedule": "hourly",
        }]
        result = await pipeline_repo.bulk_upsert_pipelines(entries)

        assert "BrandNew" in result
        assert result["BrandNew"] is new_pipeline
        pipeline_repo.session.flush.assert_awaited_once()

    async def test_bulk_insert_called_for_new_entries(self, pipeline_repo):
        """Verify pg_insert is executed when there are new pipelines."""
        empty_result = _make_scalars_result([])
        new_pipeline = make_pipeline(name="New One", task_id="NewOne")
        new_pipeline.description_edited_by_user = False
        new_pipeline.__table__ = MagicMock()
        new_pipeline.__table__.columns = [MagicMock(key="task_id"), MagicMock(key="description")]
        insert_result = MagicMock()
        refetch_result = _make_scalars_result([new_pipeline])

        pipeline_repo.session.execute.side_effect = [
            empty_result,   # 1. SELECT by name
            empty_result,   # 2. SELECT by task_id (fallback)
            insert_result,  # 3. INSERT ON CONFLICT DO NOTHING
            refetch_result, # 4. re-fetch
        ]

        entries = [{"name": "New One", "task_id": "NewOne", "description": "d"}]
        await pipeline_repo.bulk_upsert_pipelines(entries)

        # 4 execute calls total; flush called exactly once
        assert pipeline_repo.session.execute.await_count == 4
        pipeline_repo.session.flush.assert_awaited_once()


class TestBulkUpsertPipelinesMixedExistingAndNew:
    async def test_handles_mix_of_existing_and_new(self, pipeline_repo):
        """execute() call order when one pipeline exists and one is new:
          1. SELECT by name   -> [existing]
          2. SELECT by task_id for unmatched -> []  (NewOne not found by name)
          3. INSERT ON CONFLICT DO NOTHING
          4. re-fetch new names -> [new_pipeline]
        """
        existing = make_pipeline(name="Existing One", task_id="ExistingOne")
        existing.description_edited_by_user = False
        existing.__table__ = MagicMock()
        existing.__table__.columns = [MagicMock(key="task_id"), MagicMock(key="description")]

        new_pipeline = make_pipeline(name="New One", task_id="NewOne")
        new_pipeline.description_edited_by_user = False
        new_pipeline.__table__ = MagicMock()
        new_pipeline.__table__.columns = [MagicMock(key="task_id"), MagicMock(key="description")]

        by_name_result = _make_scalars_result([existing])
        by_task_id_result = _make_scalars_result([])
        insert_result = MagicMock()
        refetch_result = _make_scalars_result([new_pipeline])

        pipeline_repo.session.execute.side_effect = [
            by_name_result,   # 1. SELECT by name
            by_task_id_result, # 2. SELECT by task_id (fallback)
            insert_result,    # 3. INSERT ON CONFLICT DO NOTHING
            refetch_result,   # 4. re-fetch new names
        ]

        entries = [
            {"name": "Existing One", "task_id": "ExistingOne", "description": "old"},
            {"name": "New One", "task_id": "NewOne", "description": "brand new"},
        ]
        result = await pipeline_repo.bulk_upsert_pipelines(entries)

        assert "ExistingOne" in result
        assert result["ExistingOne"] is existing
        assert "NewOne" in result
        assert result["NewOne"] is new_pipeline


# ---------------------------------------------------------------------------
# PipelineRepository.bulk_set_teams
# ---------------------------------------------------------------------------


class TestBulkSetTeams:
    async def test_returns_immediately_for_empty_assignments(self, pipeline_repo):
        await pipeline_repo.bulk_set_teams([])
        pipeline_repo.session.execute.assert_not_called()
        pipeline_repo.session.flush.assert_not_called()

    async def test_updates_team_fields_on_pipeline(self, pipeline_repo):
        pipeline = make_pipeline(name="My Pipeline", task_id="MyPipeline")
        # Make team settable on the mock
        pipeline.team = None
        pipeline.team_id = None

        pipeline_repo.session.execute.return_value = _make_scalars_result([pipeline])

        team_id = uuid.uuid4()
        pid = pipeline.id
        await pipeline_repo.bulk_set_teams([(pid, "Dagger", team_id)])

        assert pipeline.team == "Dagger"
        assert pipeline.team_id == team_id
        pipeline_repo.session.flush.assert_awaited_once()

    async def test_skips_pipeline_not_in_session(self, pipeline_repo):
        """If a pipeline ID is not returned by the SELECT, it is silently skipped."""
        pipeline_repo.session.execute.return_value = _make_scalars_result([])

        unknown_id = uuid.uuid4()
        team_id = uuid.uuid4()
        # Should not raise
        await pipeline_repo.bulk_set_teams([(unknown_id, "Vault", team_id)])
        pipeline_repo.session.flush.assert_awaited_once()

    async def test_updates_multiple_pipelines_in_one_flush(self, pipeline_repo):
        p1 = make_pipeline(name="P1", task_id="P1")
        p1.team = None
        p1.team_id = None
        p2 = make_pipeline(name="P2", task_id="P2")
        p2.team = None
        p2.team_id = None

        pipeline_repo.session.execute.return_value = _make_scalars_result([p1, p2])

        tid1, tid2 = uuid.uuid4(), uuid.uuid4()
        await pipeline_repo.bulk_set_teams([
            (p1.id, "Dagger", tid1),
            (p2.id, "Vault", tid2),
        ])

        assert p1.team == "Dagger"
        assert p2.team == "Vault"
        # Only one flush regardless of how many assignments
        pipeline_repo.session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# LineageRepository.delete_by_pipeline_ids
# ---------------------------------------------------------------------------


class TestDeleteByPipelineIds:
    async def test_does_nothing_for_empty_list(self, lineage_repo):
        await lineage_repo.delete_by_pipeline_ids([])
        lineage_repo.session.execute.assert_not_called()

    async def test_issues_single_delete_for_multiple_ids(self, lineage_repo):
        ids = [uuid.uuid4(), uuid.uuid4(), uuid.uuid4()]
        await lineage_repo.delete_by_pipeline_ids(ids)
        # Exactly one execute call for the DELETE
        lineage_repo.session.execute.assert_awaited_once()

    async def test_single_id_issues_one_delete(self, lineage_repo):
        await lineage_repo.delete_by_pipeline_ids([uuid.uuid4()])
        lineage_repo.session.execute.assert_awaited_once()

    async def test_delete_is_not_called_when_list_is_none_like(self, lineage_repo):
        """Passing an empty list must not hit the DB — guards against accidental full-table delete."""
        await lineage_repo.delete_by_pipeline_ids([])
        assert lineage_repo.session.execute.await_count == 0
