"""AIService agentic tool-call loop (MCP) — mocked LLM + MCP, no live services."""

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

from app.config import settings
from app.services.ai_service import AIService


def _make_service():
    repo = AsyncMock()
    repo.list_visible = AsyncMock(return_value=([], 0))  # empty data-product catalog
    repo.get_tables_for_products = AsyncMock(return_value={})
    return AIService(repo)


async def test_chat_runs_mcp_tool_then_answers(monkeypatch):
    svc = _make_service()

    fake_mcp = AsyncMock()
    fake_mcp.list_tools_openai = AsyncMock(
        return_value=[{"type": "function", "function": {"name": "execute_sql", "description": "", "parameters": {}}}]
    )
    fake_mcp.call_tool = AsyncMock(return_value="count=42")

    @asynccontextmanager
    async def fake_session():
        yield fake_mcp

    calls = {"n": 0}

    async def fake_chat_raw(messages, system_prompt=None, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            assert tools  # tools were offered to the model
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "t1",
                        "type": "function",
                        "function": {"name": "execute_sql", "arguments": json.dumps({"sql": "select count(*) from mcp.catalog_columns"})},
                    }
                ],
            }
        return {"role": "assistant", "content": "There are 42 columns."}

    monkeypatch.setattr(settings, "mcp_enabled", True)
    with patch("app.services.ai_service.mcp_session", fake_session), \
         patch("app.services.ai_service.llm_client.chat_raw", side_effect=fake_chat_raw):
        out = await svc.chat("how many columns?", [])

    assert out == "There are 42 columns."
    fake_mcp.call_tool.assert_awaited_once_with(
        "execute_sql", {"sql": "select count(*) from mcp.catalog_columns"}
    )


async def test_chat_disabled_uses_plain_completion(monkeypatch):
    svc = _make_service()
    monkeypatch.setattr(settings, "mcp_enabled", False)
    with patch("app.services.ai_service.llm_client.chat", new=AsyncMock(return_value="plain answer")) as plain:
        out = await svc.chat("hi", [])
    assert out == "plain answer"
    plain.assert_awaited_once()


async def test_chat_falls_back_when_mcp_unreachable(monkeypatch):
    svc = _make_service()

    @asynccontextmanager
    async def boom():
        raise RuntimeError("mcp down")
        yield  # pragma: no cover

    monkeypatch.setattr(settings, "mcp_enabled", True)
    with patch("app.services.ai_service.mcp_session", boom), \
         patch("app.services.ai_service.llm_client.chat", new=AsyncMock(return_value="fallback answer")) as plain:
        out = await svc.chat("hi", [])
    assert out == "fallback answer"
    plain.assert_awaited_once()
