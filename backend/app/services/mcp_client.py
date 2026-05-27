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
import subprocess

from app.core.settings import settings

logger = logging.getLogger(__name__)


class MCPClient:
    """Thin async MCP client that talks to the local research MCP server over stdio."""

    def __init__(self) -> None:
        self._session: Any | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._lock = asyncio.Lock()

    async def _reset_session(self) -> None:
        """Safely dispose current MCP session and force a reconnect on next use."""
        async with self._lock:
            if self._exit_stack is not None:
                try:
                    await self._exit_stack.aclose()
                except Exception as exc:
                    logger.debug("[MCPClient] Error while closing MCP session: %s", exc)
            self._session = None
            self._exit_stack = None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        logger.debug(f"[MCPClient] Calling tool '{tool_name}' with arguments: {arguments}")
        base_timeout_seconds = max(settings.RESEARCH_MCP_TOOL_TIMEOUT_SECONDS, 5.0)
        timeout_retry_count = max(settings.RESEARCH_MCP_TOOL_TIMEOUT_RETRIES, 0)
        timeout_multiplier = max(settings.RESEARCH_MCP_TOOL_TIMEOUT_MULTIPLIER, 1.0)
        max_timeout_seconds = max(settings.RESEARCH_MCP_TOOL_MAX_TIMEOUT_SECONDS, base_timeout_seconds)

        result = None
        total_attempts = timeout_retry_count + 1
        last_timeout: asyncio.TimeoutError | None = None

        for attempt in range(1, total_attempts + 1):
            timeout_seconds = min(
                base_timeout_seconds * (timeout_multiplier ** (attempt - 1)),
                max_timeout_seconds,
            )
            session = await self._ensure_session()
            try:
                logger.info(
                    "[MCPClient] Calling MCP tool '%s' (attempt %d/%d, timeout=%.1fs) with args: %s",
                    tool_name,
                    attempt,
                    total_attempts,
                    timeout_seconds,
                    arguments,
                )
                result = await asyncio.wait_for(
                    session.call_tool(tool_name, arguments),
                    timeout=timeout_seconds,
                )
                logger.debug(f"[MCPClient] Raw result object: {result}, type: {type(result)}")
                break
            except asyncio.TimeoutError as exc:
                last_timeout = exc
                logger.warning(
                    "[MCPClient] Tool '%s' timed out after %.1fs on attempt %d/%d",
                    tool_name,
                    timeout_seconds,
                    attempt,
                    total_attempts,
                )
                await self._reset_session()
                if attempt < total_attempts:
                    continue
                logger.error(
                    "[MCPClient] Tool '%s' timed out after %d attempts (last timeout %.1fs)",
                    tool_name,
                    total_attempts,
                    timeout_seconds,
                )
                raise RuntimeError(
                    f"MCP tool '{tool_name}' timed out after {total_attempts} attempts"
                ) from last_timeout
            except Exception as exc:
                logger.exception(f"[MCPClient] Exception calling tool '{tool_name}': {exc}")
                raise

        if result is None:
            raise RuntimeError(f"MCP tool '{tool_name}' returned no result")

        # Check for error in multiple ways - MCP protocol can use different attribute names
        is_error = (
            getattr(result, "isError", False) 
            or getattr(result, "is_error", False)
            or getattr(result, "has_error", False)
        )
        
        logger.debug(f"[MCPClient] Result attributes: isError={getattr(result, 'isError', None)}, "
                    f"is_error={getattr(result, 'is_error', None)}, has_error={getattr(result, 'has_error', None)}")
        
        if is_error:
            # Try to extract error details from the response
            error_msg = self._extract_error_message(result)
            logger.error(f"[MCPClient] Tool call failed: {error_msg}")
            raise RuntimeError(f"MCP error: {error_msg}")

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

            if not script_path.exists():
                raise RuntimeError(f"MCP server script not found: {script_path}")

            logger.info("[MCPClient] Starting MCP server via stdio: %s %s (cwd=%s)", command, script_path, cwd)

            max_retries = 3
            last_error = None
            
            for attempt in range(max_retries):
                self._exit_stack = AsyncExitStack()
                try:
                    server_params = StdioServerParameters(
                        command=command,
                        args=[str(script_path)],
                        cwd=str(cwd),
                        env=env,
                    )
                    logger.debug(f"[MCPClient] Attempt {attempt + 1}/{max_retries} to start MCP server")
                    read_stream, write_stream = await self._exit_stack.enter_async_context(stdio_client(server_params))
                    logger.info("[MCPClient] MCP server stdio streams established")
                    
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
                    logger.info("[MCPClient] ClientSession created, initializing...")
                    
                    await asyncio.wait_for(self._session.initialize(), timeout=10.0)
                    logger.info("[MCPClient] MCP session initialized successfully")

                    tools = await asyncio.wait_for(self._session.list_tools(), timeout=5.0)
                    logger.info("[MCPClient] MCP tools available: %s", [tool.name for tool in tools.tools])

                    return self._session
                    
                except (asyncio.TimeoutError, RuntimeError, Exception) as exc:
                    last_error = exc
                    logger.warning(f"[MCPClient] Attempt {attempt + 1}/{max_retries} failed: {exc}")
                    
                    try:
                        await self._exit_stack.aclose()
                    except Exception as cleanup_exc:
                        logger.debug(f"[MCPClient] Error during cleanup: {cleanup_exc}")
                    
                    self._exit_stack = None
                    self._session = None
                    
                    if attempt < max_retries - 1:
                        # Wait before retrying
                        await asyncio.sleep(0.5 * (attempt + 1))
                    else:
                        logger.error("[MCPClient] MCP server initialization failed after %d attempts", max_retries)
                        raise RuntimeError(f"Failed to initialize MCP server: {last_error}") from last_error

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

    @staticmethod
    def _extract_error_message(result: Any) -> str:
        """Extract error message from MCP error response."""
        # Try content field first (common for text-based errors)
        content = getattr(result, "content", None)
        if content:
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    text = getattr(item, "text", None)
                    if text:
                        text_parts.append(text)
                if text_parts:
                    return " ".join(text_parts)
            elif isinstance(content, str):
                return content
        
        # Try to get error text directly
        error_text = getattr(result, "error", None)
        if error_text:
            return str(error_text)
        
        # Fallback to generic message
        return "Unknown error"



_mcp_client: MCPClient | None = None


def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client