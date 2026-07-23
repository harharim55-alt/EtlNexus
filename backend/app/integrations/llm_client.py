"""LLM client — talks to an OpenAI-compatible endpoint via the openai SDK.

Uses streaming (the target endpoint expects ``stream=True``) and returns the
assembled assistant text. TLS verification is configurable (LLM_VERIFY_SSL,
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
            # LLM_TIMEOUT_SECONDS <= 0 means no timeout (wait indefinitely).
            timeout = (
                httpx.Timeout(None)
                if settings.llm_timeout_seconds <= 0
                else httpx.Timeout(settings.llm_timeout_seconds)
            )
            http_client = httpx.AsyncClient(
                verify=settings.llm_verify_ssl,
                timeout=timeout,
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            )
            # api_key must be non-empty for the SDK; use a placeholder when unset.
            self._client = openai.AsyncOpenAI(
                api_key=self.api_key or "not-set",
                base_url=self.base_url,
                http_client=http_client,
            )
        return self._client

    async def chat(
        self,
        messages: list[dict],
        system_prompt: str | None = None,
    ) -> str:
        """Stream a chat completion and return the assembled assistant text."""
        if not self.is_configured:
            return "LLM endpoint is not configured. Set LLM_API_BASE_URL in your environment."

        full_messages = [{"role": "system", "content": system_prompt}, *messages] if system_prompt else messages
        kwargs: dict = {
            "model": self.model,
            "messages": full_messages,
            "stream": True,
        }
        # LLM_MAX_TOKENS <= 0 means unlimited — omit the cap so the model uses its max.
        if self.max_tokens and self.max_tokens > 0:
            kwargs["max_tokens"] = self.max_tokens

        try:
            stream = await self._get_client().chat.completions.create(**kwargs)
            content = ""
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    content += delta.content
        except openai.OpenAIError as e:
            logger.error("LLM API error: %s", e)
            return "LLM request failed. Please check the endpoint configuration."
        except Exception:
            logger.exception("Unexpected LLM error")
            return "Unexpected error talking to the LLM endpoint."

        return content

    async def close(self):
        """Close the persistent client."""
        if self._client is not None:
            await self._client.close()
            self._client = None


llm_client = LLMClient()
