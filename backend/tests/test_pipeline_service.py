"""Tests for PipelineService — business logic with visibility and caching."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.cache import pipeline_list_cache
from app.services.pipeline_service import PipelineService
from tests.conftest import make_pipeline


@pytest.fixture
def pipeline_repo():
    return AsyncMock()


@pytest.fixture
def lineage_repo():
    return AsyncMock()


@pytest.fixture
def service(pipeline_repo, lineage_repo):
    return PipelineService(pipeline_repo, lineage_repo)


@pytest.fixture(autouse=True)
def clear_cache():
    """Ensure pipeline list cache is clean before each test."""
    pipeline_list_cache.clear()
    yield
    pipeline_list_cache.clear()


class TestListPipelines:
    async def test_returns_list_response(self, service, pipeline_repo):
        p1 = make_pipeline(name="Pipeline A")
        p2 = make_pipeline(name="Pipeline B")
        pipeline_repo.list_visible.return_value = ([p1, p2], 2)
        pipeline_repo.get_success_rates.return_value = {}

        result = await service.list_pipelines(is_admin=True)
        assert len(result.items) == 2
        assert result.total == 2
        assert result.items[0].name == "Pipeline A"

    async def test_admin_cache_key(self, service, pipeline_repo):
        pipeline_repo.list_visible.return_value = ([], 0)
        pipeline_repo.get_success_rates.return_value = {}

        # First call — hits DB
        await service.list_pipelines(is_admin=True)
        assert pipeline_repo.list_visible.await_count == 1

        # Second call — hits cache
        await service.list_pipelines(is_admin=True)
        assert pipeline_repo.list_visible.await_count == 1

    async def test_search_query_bypasses_cache(self, service, pipeline_repo):
        pipeline_repo.list_visible.return_value = ([], 0)
        pipeline_repo.get_success_rates.return_value = {}

        await service.list_pipelines(query="search", is_admin=True)
        await service.list_pipelines(query="search", is_admin=True)
        # Both calls should hit DB since search bypasses cache
        assert pipeline_repo.list_visible.await_count == 2

    async def test_team_based_cache_key(self, service, pipeline_repo):
        team_ids = {uuid.uuid4(), uuid.uuid4()}
        user_id = uuid.uuid4()
        pipeline_repo.list_visible.return_value = ([], 0)
        pipeline_repo.get_success_rates.return_value = {}

        await service.list_pipelines(
            user_id=user_id, user_team_ids=team_ids
        )
        await service.list_pipelines(
            user_id=user_id, user_team_ids=team_ids
        )
        assert pipeline_repo.list_visible.await_count == 1

    async def test_success_rates_applied(self, service, pipeline_repo):
        p = make_pipeline(name="P1")
        pipeline_repo.list_visible.return_value = ([p], 1)
        pipeline_repo.get_success_rates.return_value = {p.id: 95.5}

        result = await service.list_pipelines(is_admin=True)
        assert result.items[0].success_rate == 95.5


class TestUpdatePipelineMetadata:
    async def test_returns_response_on_success(self, service, pipeline_repo):
        from app.schemas.pipeline import PipelineUpdateRequest

        pipeline = make_pipeline()
        pipeline.description = "Updated"
        pipeline.documentation = None
        pipeline.last_updated_by = "tester"
        pipeline.last_updated_at = None

        pipeline_repo.get_by_id.return_value = pipeline
        pipeline_repo.update_metadata.return_value = pipeline

        req = PipelineUpdateRequest(description="Updated")
        result = await service.update_pipeline_metadata(pipeline.id, req, updated_by="tester")
        assert result is not None
        assert result.description == "Updated"

    async def test_returns_none_when_not_found(self, service, pipeline_repo):
        from app.schemas.pipeline import PipelineUpdateRequest

        pipeline_repo.get_by_id.return_value = None
        req = PipelineUpdateRequest(description="x")
        result = await service.update_pipeline_metadata(uuid.uuid4(), req)
        assert result is None

    async def test_clears_cache_on_update(self, service, pipeline_repo):
        from app.schemas.pipeline import PipelineUpdateRequest

        pipeline_list_cache.set("all:0:200", ["cached"])
        assert pipeline_list_cache.get("all:0:200") is not None

        pipeline = make_pipeline()
        pipeline.description = "x"
        pipeline.documentation = None
        pipeline.last_updated_by = "a"
        pipeline.last_updated_at = None
        pipeline_repo.get_by_id.return_value = pipeline
        pipeline_repo.update_metadata.return_value = pipeline

        req = PipelineUpdateRequest(description="x")
        await service.update_pipeline_metadata(pipeline.id, req)
        assert pipeline_list_cache.get("all:0:200") is None


class TestGetPipelineDetail:
    async def test_returns_detail(self, service, pipeline_repo, lineage_repo):
        pipeline = make_pipeline()
        pipeline_repo.get_by_id.return_value = pipeline
        lineage_repo.get_by_pipeline_id.return_value = {
            "reads_from": [],
            "writes_to": [],
        }

        result = await service.get_pipeline_detail(pipeline.id)
        assert result is not None
        assert result.name == pipeline.name

    async def test_returns_none_when_not_found(self, service, pipeline_repo, lineage_repo):
        pipeline_repo.get_by_id.return_value = None
        result = await service.get_pipeline_detail(uuid.uuid4())
        assert result is None


class TestGetPipelineDetailForUser:
    async def test_admin_gets_can_edit_true(self, service, pipeline_repo, lineage_repo):
        pipeline = make_pipeline(team="Dagger", team_id=uuid.uuid4())
        pipeline_repo.get_by_id.return_value = pipeline
        lineage_repo.get_by_pipeline_id.return_value = {"reads_from": [], "writes_to": []}

        grant_repo = AsyncMock()
        result = await service.get_pipeline_detail_for_user(
            pipeline.id, uuid.uuid4(), set(), is_admin=True, grant_repo=grant_repo,
        )
        assert result is not None
        assert result.can_edit is True

    async def test_unassigned_pipeline_is_editable(self, service, pipeline_repo, lineage_repo):
        pipeline = make_pipeline()
        pipeline.team_id = None
        pipeline_repo.get_by_id.return_value = pipeline
        lineage_repo.get_by_pipeline_id.return_value = {"reads_from": [], "writes_to": []}

        grant_repo = AsyncMock()
        result = await service.get_pipeline_detail_for_user(
            pipeline.id, uuid.uuid4(), set(), is_admin=False, grant_repo=grant_repo,
        )
        assert result is not None
        assert result.can_edit is True

    async def test_non_visible_pipeline_returns_none(self, service, pipeline_repo, lineage_repo):
        team_id = uuid.uuid4()
        pipeline = make_pipeline(team="Dagger", team_id=team_id)
        pipeline_repo.get_by_id.return_value = pipeline
        lineage_repo.get_by_pipeline_id.return_value = {"reads_from": [], "writes_to": []}

        grant_repo = AsyncMock()
        grant_repo.user_can_see_pipeline.return_value = False

        result = await service.get_pipeline_detail_for_user(
            pipeline.id, uuid.uuid4(), set(), is_admin=False, grant_repo=grant_repo,
        )
        assert result is None

    async def test_team_member_gets_can_edit(self, service, pipeline_repo, lineage_repo):
        team_id = uuid.uuid4()
        pipeline = make_pipeline(team="Dagger", team_id=team_id)
        pipeline_repo.get_by_id.return_value = pipeline
        lineage_repo.get_by_pipeline_id.return_value = {"reads_from": [], "writes_to": []}

        grant_repo = AsyncMock()
        grant_repo.user_can_see_pipeline.return_value = True

        result = await service.get_pipeline_detail_for_user(
            pipeline.id, uuid.uuid4(), {team_id}, is_admin=False, grant_repo=grant_repo,
        )
        assert result is not None
        assert result.can_edit is True

    async def test_editor_grant_gives_can_edit(self, service, pipeline_repo, lineage_repo):
        team_id = uuid.uuid4()
        pipeline = make_pipeline(team="Dagger", team_id=team_id)
        pipeline_repo.get_by_id.return_value = pipeline
        lineage_repo.get_by_pipeline_id.return_value = {"reads_from": [], "writes_to": []}

        grant_repo = AsyncMock()
        grant_repo.user_can_see_pipeline.return_value = True
        grant_repo.get_grant_level_for_pipeline.return_value = "editor"

        other_team = uuid.uuid4()
        result = await service.get_pipeline_detail_for_user(
            pipeline.id, uuid.uuid4(), {other_team}, is_admin=False, grant_repo=grant_repo,
        )
        assert result is not None
        assert result.can_edit is True

    async def test_viewer_grant_no_can_edit(self, service, pipeline_repo, lineage_repo):
        team_id = uuid.uuid4()
        pipeline = make_pipeline(team="Dagger", team_id=team_id)
        pipeline_repo.get_by_id.return_value = pipeline
        lineage_repo.get_by_pipeline_id.return_value = {"reads_from": [], "writes_to": []}

        grant_repo = AsyncMock()
        grant_repo.user_can_see_pipeline.return_value = True
        grant_repo.get_grant_level_for_pipeline.return_value = "viewer"

        other_team = uuid.uuid4()
        result = await service.get_pipeline_detail_for_user(
            pipeline.id, uuid.uuid4(), {other_team}, is_admin=False, grant_repo=grant_repo,
        )
        assert result is not None
        assert result.can_edit is False


class TestGetJoinSuggestions:
    async def test_returns_suggestions(self, service, pipeline_repo):
        from app.cache import join_suggestions_cache
        join_suggestions_cache.clear()

        pipeline = make_pipeline(name="P1")
        pipeline_repo.get_by_id.return_value = pipeline
        pipeline_repo.get_shared_field_pipelines.return_value = [
            {"pipeline_id": uuid.uuid4(), "pipeline_name": "P2", "shared_fields": ["ip_address"]},
        ]

        result = await service.get_join_suggestions(pipeline.id)
        assert result is not None
        assert len(result.schema_matches) == 1
        assert "ip_address" in result.schema_matches[0].shared_fields

        join_suggestions_cache.clear()

    async def test_returns_none_when_pipeline_not_found(self, service, pipeline_repo):
        from app.cache import join_suggestions_cache
        join_suggestions_cache.clear()

        pipeline_repo.get_by_id.return_value = None
        result = await service.get_join_suggestions(uuid.uuid4())
        assert result is None

        join_suggestions_cache.clear()
