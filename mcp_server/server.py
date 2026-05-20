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


@server.tool(description="Search arXiv and return normalized paper metadata.")
async def search_arxiv(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    """Search arXiv papers.
    
    Args:
        query: The search query to use for arXiv
        max_results: Maximum number of results to return (default: 10)
    
    Returns:
        List of paper dictionaries with normalized metadata
    """
    logger.info(
        "[MCPServer] search_arxiv invoked with query='%s', max_results=%s (type=%s)",
        query,
        max_results,
        type(max_results).__name__
    )
    try:
        result = await search_arxiv_impl(query=query, max_results=max_results)
        logger.info("[MCPServer] search_arxiv returning %d papers", len(result))
        return result
    except Exception as exc:
        logger.exception("[MCPServer] search_arxiv failed with exception: %s", exc)
        raise


if __name__ == "__main__":
    server.run(transport="stdio")