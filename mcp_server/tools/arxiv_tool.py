"""Async arXiv MCP tool implementation."""

from __future__ import annotations

import asyncio
from datetime import datetime
import logging
import os
import random
import re
from typing import Any
import xml.etree.ElementTree as ET

import httpx

logger = logging.getLogger(__name__)

ARXIV_API_URL = "https://export.arxiv.org/api/query"
_arxiv_lock = asyncio.Lock()
_last_arxiv_request_monotonic = 0.0


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


async def search_arxiv(query: str, max_results: int) -> list[dict[str, Any]]:
    """Search arXiv and return normalized paper records for the MCP server."""

    normalized_query = query.strip()
    if not normalized_query:
        return []

    capped_results = max(1, min(int(max_results or 1), 100))
    headers = {
        "User-Agent": os.getenv(
            "RESEARCH_ARXIV_USER_AGENT",
            "amzur-research-digest/1.0 (mailto:support@example.com)",
        ),
        "Accept": "application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    params = {
        "search_query": normalized_query,
        "start": 0,
        "max_results": capped_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    max_retries = max(_env_int("RESEARCH_ARXIV_MAX_RETRIES", 3), 1)
    backoff = max(_env_float("RESEARCH_ARXIV_BACKOFF_SECONDS", 1.0), 0.1)
    min_interval = max(_env_float("RESEARCH_ARXIV_MIN_REQUEST_INTERVAL_SECONDS", 3.5), 0.0)
    timeout_seconds = max(_env_float("RESEARCH_ARXIV_TIMEOUT_SECONDS", 30.0), 5.0)

    response: httpx.Response | None = None

    for attempt in range(max_retries):
        try:
            async with _arxiv_lock:
                global _last_arxiv_request_monotonic

                now = asyncio.get_running_loop().time()
                wait_for = (_last_arxiv_request_monotonic + min_interval) - now
                if wait_for > 0:
                    await asyncio.sleep(wait_for)

                async with httpx.AsyncClient(timeout=timeout_seconds, headers=headers) as client:
                    response = await client.get(ARXIV_API_URL, params=params)

                _last_arxiv_request_monotonic = asyncio.get_running_loop().time()
                response.raise_for_status()
            break
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if attempt == max_retries - 1:
                if status_code == 429:
                    logger.warning(
                        "[MCP arXiv] Rate limited after %s attempts for query '%s'. Returning empty result.",
                        max_retries,
                        normalized_query,
                    )
                    return []
                raise

            retry_after_seconds = 0.0
            if exc.response is not None:
                retry_after = exc.response.headers.get("Retry-After", "").strip()
                if retry_after:
                    try:
                        retry_after_seconds = float(retry_after)
                    except ValueError:
                        retry_after_seconds = 0.0

            delay = max(retry_after_seconds, backoff * (2 ** attempt)) + random.uniform(0.0, 0.5)
            logger.warning(
                "[MCP arXiv] HTTP error on attempt %s/%s (status=%s): %s. Retrying in %.2fs",
                attempt + 1,
                max_retries,
                status_code,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
        except (httpx.HTTPError, httpx.TimeoutException) as exc:
            if attempt == max_retries - 1:
                raise

            delay = backoff * (2 ** attempt) + random.uniform(0.0, 0.3)
            logger.warning(
                "[MCP arXiv] Request failure on attempt %s/%s: %s. Retrying in %.2fs",
                attempt + 1,
                max_retries,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    if response is None:
        return []

    papers = _parse_arxiv_feed(response.text)
    logger.info("[MCP arXiv] Returning %s normalized papers for query '%s'", len(papers), normalized_query)
    return papers


def _parse_arxiv_feed(xml_text: str) -> list[dict[str, Any]]:
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    root = ET.fromstring(xml_text)
    papers: list[dict[str, Any]] = []

    for entry in root.findall("atom:entry", ns):
        paper_id = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
        title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
        published = (entry.findtext("atom:published", default="", namespaces=ns) or "").strip()
        authors = [
            author.findtext("atom:name", default="", namespaces=ns)
            for author in entry.findall("atom:author", ns)
        ]
        categories = [category.attrib.get("term", "") for category in entry.findall("atom:category", ns)]

        if not paper_id or not title:
            continue

        normalized_published = published
        if published:
            try:
                normalized_published = datetime.fromisoformat(published.replace("Z", "+00:00")).isoformat()
            except ValueError:
                normalized_published = published

        papers.append(
            {
                "id": paper_id,
                "title": re.sub(r"\s+", " ", title),
                "authors": [author for author in authors if author],
                "summary": re.sub(r"\s+", " ", summary),
                "published": normalized_published,
                "url": paper_id,
                "categories": [category for category in categories if category],
            }
        )

    return papers