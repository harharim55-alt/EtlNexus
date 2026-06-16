"""LLMClient streaming accumulation — mocked openai stream, no network."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.integrations.llm_client import llm_client


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self):
        self._i = 0
        return self

    async def __anext__(self):
        if self._i >= len(self._chunks):
            raise StopAsyncIteration
        c = self._chunks[self._i]
        self._i += 1
        return c


def _chunk(content=None, tool_calls=None):
    delta = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(delta=delta)])


def _tcd(index, id=None, name=None, args=None):
    return SimpleNamespace(index=index, id=id, function=SimpleNamespace(name=name, arguments=args))


def _fake_client(chunks):
    client = SimpleNamespace()
    client.chat = SimpleNamespace()
    client.chat.completions = SimpleNamespace()
    client.chat.completions.create = AsyncMock(return_value=_FakeStream(chunks))
    return client


async def test_streams_text_content(monkeypatch):
    monkeypatch.setattr(llm_client, "base_url", "http://llm.local")
    chunks = [_chunk(content="Hel"), _chunk(content="lo"), _chunk(content=" world")]
    with patch.object(llm_client, "_get_client", return_value=_fake_client(chunks)):
        msg = await llm_client.chat_raw([{"role": "user", "content": "hi"}])
    assert msg["content"] == "Hello world"
    assert "tool_calls" not in msg


async def test_accumulates_tool_call_deltas(monkeypatch):
    monkeypatch.setattr(llm_client, "base_url", "http://llm.local")
    chunks = [
        _chunk(tool_calls=[_tcd(0, id="t1", name="execute_sql", args='{"sql":')]),
        _chunk(tool_calls=[_tcd(0, args='"select 1"}')]),
    ]
    with patch.object(llm_client, "_get_client", return_value=_fake_client(chunks)):
        msg = await llm_client.chat_raw([{"role": "user", "content": "q"}], tools=[{"type": "function"}])
    assert msg["content"] is None
    assert msg["tool_calls"] == [
        {"id": "t1", "type": "function", "function": {"name": "execute_sql", "arguments": '{"sql":"select 1"}'}}
    ]


async def test_not_configured_returns_message(monkeypatch):
    monkeypatch.setattr(llm_client, "base_url", "")
    out = await llm_client.chat([{"role": "user", "content": "hi"}])
    assert "not configured" in out
