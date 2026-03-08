"""OpenAPI-compatible LLM client for AI-powered features."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self):
        self.base_url = settings.llm_api_base_url.rstrip("/") if settings.llm_api_base_url else ""
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.max_tokens = settings.llm_max_tokens
        self.timeout = httpx.Timeout(30.0)

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url)

    async def chat(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
    ) -> str:
        """Send a chat completion request. Returns the assistant message content."""
        if not self.is_configured:
            return "LLM endpoint is not configured. Set LLM_API_BASE_URL in your environment."

        payload: dict = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }

        if system_prompt:
            payload["messages"] = [
                {"role": "system", "content": system_prompt},
                *messages,
            ]

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as e:
            logger.error("LLM API error: %s %s", e.response.status_code, e.response.text[:200])
            return f"LLM API error: {e.response.status_code}"
        except httpx.RequestError as e:
            logger.error("LLM connection error: %s", e)
            return "Unable to reach the LLM endpoint. Please check your configuration."
        except (KeyError, IndexError):
            logger.error("Unexpected LLM response format")
            return "Unexpected response from the LLM endpoint."


llm_client = LLMClient()
