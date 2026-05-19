"""Backend MCP client for research tool calls."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Dict

from app.core.settings import settings

logger = logging.getLogger(__name__)


class MCPClient:
    """Thin async MCP client that talks to the local research MCP server over stdio."""

    def __init__(self) -> None:
        self._session: Any | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._lock = asyncio.Lock()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        session = await self._ensure_session()
        timeout_seconds = max(settings.RESEARCH_MCP_TOOL_TIMEOUT_SECONDS, 5.0)
        result = await asyncio.wait_for(session.call_tool(tool_name, arguments), timeout=timeout_seconds)

        if getattr(result, "isError", False) or getattr(result, "is_error", False):
            raise RuntimeError(f"MCP tool '{tool_name}' returned an error")

        return self._extract_payload(result)

    async def _ensure_session(self) -> Any:
        if self._session is not None:
            return self._session

        async with self._lock:
            if self._session is not None:
                return self._session

            from mcp import ClientSession, StdioServerParameters
            from mcp import types as mcp_types
            from mcp.client.stdio import stdio_client

            command = settings.RESEARCH_MCP_SERVER_COMMAND.strip() or sys.executable
            script_path = Path(settings.RESEARCH_MCP_SERVER_SCRIPT).expanduser().resolve()
            cwd = Path(settings.RESEARCH_MCP_SERVER_CWD).expanduser().resolve()
            env = os.environ.copy()
            env.setdefault("PYTHONIOENCODING", "utf-8")
            env.setdefault("RESEARCH_MCP_LOG_LEVEL", settings.RESEARCH_MCP_LOG_LEVEL)

            logger.info("[MCPClient] Starting MCP server via stdio: %s %s", command, script_path)

            self._exit_stack = AsyncExitStack()
            server_params = StdioServerParameters(
                command=command,
                args=[str(script_path)],
                cwd=str(cwd),
                env=env,
            )
            read_stream, write_stream = await self._exit_stack.enter_async_context(stdio_client(server_params))
            self._session = await self._exit_stack.enter_async_context(
                ClientSession(
                    read_stream=read_stream,
                    write_stream=write_stream,
                    client_info=mcp_types.Implementation(
                        name="research-digest-backend",
                        version="1.0.0",
                    ),
                )
            )
            await self._session.initialize()

            tools = await self._session.list_tools()
            logger.info("[MCPClient] MCP tools available: %s", [tool.name for tool in tools.tools])

            return self._session

    @staticmethod
    def _extract_payload(result: Any) -> Any:
        structured = getattr(result, "structuredContent", None)
        if structured is None:
            structured = getattr(result, "structured_content", None)
        if structured is not None:
            if isinstance(structured, dict) and "result" in structured:
                return structured["result"]
            return structured

        content = getattr(result, "content", None) or []
        text_chunks: list[str] = []
        for item in content:
            text = getattr(item, "text", None)
            if text:
                text_chunks.append(text)

        if not text_chunks:
            return []

        joined = "\n".join(text_chunks).strip()
        try:
            return json.loads(joined)
        except json.JSONDecodeError as exc:
            raise ValueError("Unable to parse MCP tool response payload as JSON") from exc


_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client