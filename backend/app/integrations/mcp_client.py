"""MCP client — connects the AI Architect to the Postgres MCP server over SSE.

Opens a short-lived session per chat turn: list the server's tools (mapped to the
OpenAI tool schema the LLM expects) and execute the tool calls the model requests.
The server runs read-only against the ``mcp`` schema views (see migration 048).
"""

import logging
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.sse import sse_client

from app.config import settings

logger = logging.getLogger(__name__)


class MCPSession:
    """Wraps an initialized MCP ClientSession with LLM-friendly helpers."""

    def __init__(self, session: ClientSession):
        self._session = session

    async def list_tools_openai(self) -> list[dict]:
        """Return the server's tools as OpenAI `tools` definitions."""
        result = await self._session.list_tools()
        tools: list[dict] = []
        for t in result.tools:
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema or {"type": "object", "properties": {}},
                    },
                }
            )
        return tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Execute a tool and return its textual result (errors returned as text)."""
        try:
            result = await self._session.call_tool(name, arguments=arguments)
        except Exception as exc:
            logger.warning("MCP tool %s failed: %s", name, exc)
            return f"Tool error: {exc}"

        parts = [getattr(block, "text", "") for block in (result.content or [])]
        text = "\n".join(p for p in parts if p) or "(no output)"
        if getattr(result, "isError", False):
            return f"Tool error: {text}"
        return text


@asynccontextmanager
async def mcp_session():
    """Open an initialized MCP session over SSE; closes on exit."""
    async with sse_client(settings.mcp_server_url) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        yield MCPSession(session)
