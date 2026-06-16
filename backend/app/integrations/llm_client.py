"""LLM client — talks to an OpenAI-compatible endpoint via the openai SDK.

Uses streaming (the target endpoint expects ``stream=True``) and accumulates both
text content and tool-call deltas so the AI Architect's agentic MCP loop gets a
full assistant message back. TLS verification is configurable (LLM_VERIFY_SSL,
default off) for internal endpoints with self-signed certs.
"""

import logging

import httpx
import openai

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.base_url = settings.llm_api_base_url.rstrip("/") if settings.llm_api_base_url else ""
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.max_tokens = settings.llm_max_tokens
        self._client: openai.AsyncOpenAI | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    def _get_client(self) -> openai.AsyncOpenAI:
        if self._client is None:
            http_client = httpx.AsyncClient(
                verify=settings.llm_verify_ssl,
                timeout=httpx.Timeout(settings.llm_timeout_seconds),
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            )
            # api_key must be non-empty for the SDK; use a placeholder when unset.
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key or "not-set",
                base_url=self.base_url,
                http_client=http_client,
            )
        return self._client

    async def chat_raw(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> dict:
        """Stream a chat completion; return the assembled assistant message.

        The returned dict preserves ``content`` and any ``tool_calls`` so callers
        can drive an agentic tool-calling loop. On any error a synthetic assistant
        message (``content`` = error text, no ``tool_calls``) is returned so callers
        can treat it as a terminal answer.
        """
        if not self.is_configured:
            return {"role": "assistant", "content": "LLM endpoint is not configured. Set LLM_API_BASE_URL in your environment."}

        full_messages = [{"role": "system", "content": system_prompt}, *messages] if system_prompt else messages
        kwargs: dict = {
            "model": self.model,
            "messages": full_messages,
            "max_tokens": self.max_tokens,
            "stream": True,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            stream = await self._get_client().chat.completions.create(**kwargs)
            content = ""
            # Accumulate tool-call fragments by their stream index.
            tool_acc: dict[int, dict] = {}
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    content += delta.content
                for tcd in getattr(delta, "tool_calls", None) or []:
                    slot = tool_acc.setdefault(tcd.index, {"id": None, "name": "", "arguments": ""})
                    if tcd.id:
                        slot["id"] = tcd.id
                    if tcd.function and tcd.function.name:
                        slot["name"] = tcd.function.name
                    if tcd.function and tcd.function.arguments:
                        slot["arguments"] += tcd.function.arguments
        except openai.OpenAIError as e:
            logger.error("LLM API error: %s", e)
            return {"role": "assistant", "content": "LLM request failed. Please check the endpoint configuration."}
        except Exception:
            logger.exception("Unexpected LLM error")
            return {"role": "assistant", "content": "Unexpected error talking to the LLM endpoint."}

        message: dict = {"role": "assistant", "content": content or None}
        if tool_acc:
            message["tool_calls"] = [
                {
                    "id": slot["id"],
                    "type": "function",
                    "function": {"name": slot["name"], "arguments": slot["arguments"]},
                }
                for _, slot in sorted(tool_acc.items())
            ]
        return message

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Send a chat completion request. Returns the assistant message content."""
        message = await self.chat_raw(messages, system_prompt=system_prompt)
        return message.get("content") or ""

    async def close(self):
        """Close the persistent client."""
        if self._client is not None:
            await self._client.close()
            self._client = None


llm_client = LLMClient()
