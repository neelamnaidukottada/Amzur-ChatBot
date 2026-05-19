"""Local MCP server exposing research tools over stdio."""

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from tools.arxiv_tool import search_arxiv as search_arxiv_impl


logging.basicConfig(
    level=getattr(logging, os.getenv("RESEARCH_MCP_LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

logger = logging.getLogger(__name__)
server = FastMCP("research-digest-mcp")


@server.tool(name="search_arxiv", description="Search arXiv and return normalized paper metadata.")
async def search_arxiv(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    logger.info("[MCPServer] search_arxiv invoked with max_results=%s", max_results)
    return await search_arxiv_impl(query=query, max_results=max_results)


if __name__ == "__main__":
    server.run(transport="stdio")