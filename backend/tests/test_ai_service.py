"""Tests for AIService — chat with catalog context and join insights."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_service import AIService
from tests.conftest import make_pipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_pipeline_with_fields(*, name: str = "Switch Port Collector", task_id: str = "SwitchPortCollector", fields: list[str] | None = None):
    pipeline = make_pipeline(name=name, task_id=task_id)
    mock_fields = []
    for fname in (fields or []):
        f = MagicMock()
        f.name = fname
        mock_fields.append(f)
    pipeline.fields = mock_fields
    return pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pipeline_repo():
    return AsyncMock()


@pytest.fixture
def service(pipeline_repo):
    return AIService(pipeline_repo)


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------


class TestChat:
    async def test_calls_llm_client_with_message_and_history(
        self, service, pipeline_repo
    ):
        pipeline_repo.get_task_id_map.return_value = {}

        with patch(
            "app.services.ai_service.llm_client.chat",
            new_callable=AsyncMock,
            return_value="Here is an answer.",
        ) as mock_chat:
            result = await service.chat(
                message="What pipelines exist?",
                history=[{"role": "user", "content": "Hello"}],
            )

        assert result == "Here is an answer."
        mock_chat.assert_awaited_once()

        # Verify message appears in messages list
        call_args = mock_chat.call_args
        messages = call_args.args[0]
        assert any(m["role"] == "user" and m["content"] == "What pipelines exist?" for m in messages)

    async def test_history_prepended_before_new_message(
        self, service, pipeline_repo
    ):
        pipeline_repo.get_task_id_map.return_value = {}

        with patch(
            "app.services.ai_service.llm_client.chat",
            new_callable=AsyncMock,
            return_value="OK",
        ) as mock_chat:
            await service.chat(
                message="Follow-up question",
                history=[
                    {"role": "user", "content": "First message"},
                    {"role": "assistant", "content": "First reply"},
                ],
            )

        messages = mock_chat.call_args.args[0]
        # History messages should appear before the new user message
        user_messages = [m for m in messages if m["role"] == "user"]
        assert user_messages[-1]["content"] == "Follow-up question"

    async def test_system_prompt_includes_catalog_context(
        self, service, pipeline_repo
    ):
        pipeline = make_pipeline_with_fields(name="Switch Port Collector", task_id="SwitchPortCollector")
        pipeline.category = "Network Infrastructure"
        pipeline.description = "Collects switch port data."
        pipeline_repo.get_task_id_map.return_value = {"SwitchPortCollector": pipeline}

        with patch(
            "app.services.ai_service.llm_client.chat",
            new_callable=AsyncMock,
            return_value="Response",
        ) as mock_chat:
            await service.chat(message="Help me", history=[])

        call_kwargs = mock_chat.call_args.kwargs
        system_prompt = call_kwargs.get("system_prompt", "")
        assert "Switch Port Collector" in system_prompt

    async def test_empty_history_is_allowed(
        self, service, pipeline_repo
    ):
        pipeline_repo.get_task_id_map.return_value = {}

        with patch(
            "app.services.ai_service.llm_client.chat",
            new_callable=AsyncMock,
            return_value="Answer",
        ) as mock_chat:
            result = await service.chat(message="Query", history=[])

        assert result == "Answer"
        mock_chat.assert_awaited_once()

    async def test_catalog_context_shows_no_pipelines_when_empty(
        self, service, pipeline_repo
    ):
        pipeline_repo.get_task_id_map.return_value = {}

        with patch(
            "app.services.ai_service.llm_client.chat",
            new_callable=AsyncMock,
            return_value="No pipelines response",
        ) as mock_chat:
            await service.chat(message="Any pipelines?", history=[])

        call_kwargs = mock_chat.call_args.kwargs
        system_prompt = call_kwargs.get("system_prompt", "")
        assert "No pipelines currently in the catalog" in system_prompt


# ---------------------------------------------------------------------------
# get_join_insight
# ---------------------------------------------------------------------------


class TestGetJoinInsight:
    async def test_returns_configured_message_when_llm_not_configured(
        self, service, pipeline_repo
    ):
        # Replace the module-level llm_client with a MagicMock whose
        # is_configured attribute is False (not a property — just a bool).
        mock_client = MagicMock()
        mock_client.is_configured = False
        with patch("app.services.ai_service.llm_client", mock_client):
            result = await service.get_join_insight(uuid.uuid4())

        assert "not configured" in result.lower() or "configured" in result.lower()

    async def test_returns_not_found_message_when_pipeline_missing(
        self, service, pipeline_repo
    ):
        with patch("app.services.ai_service.llm_client") as mock_client:
            mock_client.is_configured = True
            pipeline_repo.get_by_id.return_value = None

            result = await service.get_join_insight(uuid.uuid4())

        assert "not found" in result.lower()

    async def test_returns_no_overlaps_message_when_empty_catalog(
        self, service, pipeline_repo
    ):
        pipeline = make_pipeline_with_fields(fields=["ip_address", "mac_address"])
        pipeline_repo.get_by_id.return_value = pipeline
        pipeline_repo.get_shared_field_pipelines.return_value = []

        with patch("app.services.ai_service.llm_client") as mock_client:
            mock_client.is_configured = True
            result = await service.get_join_insight(pipeline.id)

        assert "no field overlaps" in result.lower()

    async def test_calls_llm_when_overlaps_exist(
        self, service, pipeline_repo
    ):
        pipeline = make_pipeline_with_fields(
            name="Switch Port Collector",
            fields=["ip_address", "mac_address", "port_id"],
        )
        pipeline_repo.get_by_id.return_value = pipeline
        pipeline_repo.get_shared_field_pipelines.return_value = [
            {
                "pipeline_name": "Route Table Sync",
                "shared_fields": ["ip_address", "mac_address"],
            }
        ]

        with patch("app.services.ai_service.llm_client") as mock_client:
            mock_client.is_configured = True
            mock_client.chat = AsyncMock(return_value="Great join opportunity!")

            result = await service.get_join_insight(pipeline.id)

        assert result == "Great join opportunity!"
        mock_client.chat.assert_awaited_once()

    async def test_prompt_includes_pipeline_name_and_fields(
        self, service, pipeline_repo
    ):
        pipeline = make_pipeline_with_fields(
            name="Switch Port Collector",
            fields=["ip_address", "vlan_id"],
        )
        pipeline_repo.get_by_id.return_value = pipeline
        pipeline_repo.get_shared_field_pipelines.return_value = [
            {"pipeline_name": "VLAN Sync", "shared_fields": ["vlan_id"]},
        ]

        with patch("app.services.ai_service.llm_client") as mock_client:
            mock_client.is_configured = True
            mock_client.chat = AsyncMock(return_value="Good join on vlan_id")

            await service.get_join_insight(pipeline.id)

        call_args = mock_client.chat.call_args
        prompt_messages = call_args.args[0]
        prompt_text = prompt_messages[0]["content"]
        assert "Switch Port Collector" in prompt_text
        assert "ip_address" in prompt_text
        assert "VLAN Sync" in prompt_text


# ---------------------------------------------------------------------------
# _build_catalog_context
# ---------------------------------------------------------------------------


class TestBuildCatalogContext:
    async def test_empty_map_returns_no_pipelines_message(
        self, service, pipeline_repo
    ):
        pipeline_repo.get_task_id_map.return_value = {}

        context = await service._build_catalog_context()

        assert "No pipelines" in context

    async def test_single_pipeline_included_in_context(
        self, service, pipeline_repo
    ):
        pipeline = make_pipeline(name="Route Table Sync")
        pipeline.category = "Network Infrastructure"
        pipeline.description = "Syncs routing tables."
        pipeline_repo.get_task_id_map.return_value = {"RouteTableSync": pipeline}

        context = await service._build_catalog_context()

        assert "Route Table Sync" in context

    async def test_limits_context_to_20_pipelines(
        self, service, pipeline_repo
    ):
        # Create 25 pipelines
        pipeline_map = {}
        for i in range(25):
            p = make_pipeline(name=f"Pipeline {i}", task_id=f"Pipeline{i}")
            p.category = "Test"
            p.description = None
            pipeline_map[f"Pipeline{i}"] = p

        pipeline_repo.get_task_id_map.return_value = pipeline_map

        context = await service._build_catalog_context()

        # Count occurrences of "Pipeline" (one per line entry)
        lines = [line for line in context.split("\n") if line.startswith("- Pipeline")]
        assert len(lines) <= 20
