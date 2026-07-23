"""Tests for AIService — chat with data-product catalog context."""

from unittest.mock import AsyncMock, patch

import pytest

from app.cache import catalog_context_cache
from app.services.ai_service import AIService
from tests.conftest import make_product


@pytest.fixture(autouse=True)
def clear_cache():
    catalog_context_cache.clear()
    yield
    catalog_context_cache.clear()


@pytest.fixture
def repo():
    r = AsyncMock()
    r.get_all.return_value = []
    return r


@pytest.fixture
def service(repo):
    return AIService(repo)


class TestChat:
    async def test_calls_llm_with_message_and_history(self, service, repo):
        with patch(
            "app.services.ai_service.llm_client.chat",
            new_callable=AsyncMock,
            return_value="Here is an answer.",
        ) as mock_chat:
            result = await service.chat(
                message="What data products exist?",
                history=[{"role": "user", "content": "Hello"}],
            )

        assert result == "Here is an answer."
        messages = mock_chat.call_args.args[0]
        assert any(m["role"] == "user" and m["content"] == "What data products exist?" for m in messages)

    async def test_history_prepended_before_new_message(self, service, repo):
        with patch("app.services.ai_service.llm_client.chat", new_callable=AsyncMock, return_value="OK") as mock_chat:
            await service.chat(
                message="Follow-up",
                history=[
                    {"role": "user", "content": "First"},
                    {"role": "assistant", "content": "Reply"},
                ],
            )
        messages = mock_chat.call_args.args[0]
        user_messages = [m for m in messages if m["role"] == "user"]
        assert user_messages[-1]["content"] == "Follow-up"

    async def test_system_prompt_includes_catalog_context(self, service, repo):
        product = make_product(name="Login Events", description="Auth logins.", tables=["vault.logins"])
        repo.get_all.return_value = [product]

        with patch(
            "app.services.ai_service.llm_client.chat", new_callable=AsyncMock, return_value="Response"
        ) as mock_chat:
            await service.chat(message="Help me", history=[])

        system_prompt = mock_chat.call_args.kwargs.get("system_prompt", "")
        assert "Login Events" in system_prompt
        assert "vault.logins" in system_prompt

    async def test_empty_catalog_message(self, service, repo):
        repo.get_all.return_value = []
        with patch("app.services.ai_service.llm_client.chat", new_callable=AsyncMock, return_value="x") as mock_chat:
            await service.chat(message="Any products?", history=[])
        system_prompt = mock_chat.call_args.kwargs.get("system_prompt", "")
        assert "No data products currently in the catalog" in system_prompt


class TestBuildCatalogContext:
    async def test_empty_returns_message(self, service, repo):
        repo.get_all.return_value = []
        context = await service._build_catalog_context()
        assert "No data products" in context

    async def test_single_product_with_tables_and_schedule(self, service, repo):
        product = make_product(
            name="Route Table Sync",
            description="Syncs routing tables.",
            schedule_type="hourly",
            tables=["prism.routes", "prism.peers"],
        )
        repo.get_all.return_value = [product]

        context = await service._build_catalog_context()
        assert "Route Table Sync" in context
        assert "Syncs routing tables." in context
        assert "schedule: hourly" in context
        assert "prism.routes" in context
        assert "prism.peers" in context

    async def test_all_products_listed(self, service, repo):
        products = [make_product(name=f"Product {i}", description=f"Desc {i}", tables=[]) for i in range(20)]
        repo.get_all.return_value = products
        context = await service._build_catalog_context()
        lines = [line for line in context.split("\n") if line.startswith("- Product")]
        assert len(lines) == 20
