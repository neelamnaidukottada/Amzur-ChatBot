"""Schemas for research digest agent API."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class ResearchDigestRequest(BaseModel):
    """Input request for research digest generation."""

    query: str = Field(..., min_length=3, description="Research topic or question")
    conversation_id: Optional[int] = Field(default=None, ge=1)
    batch_size: int = Field(default=10, ge=5, le=25)
    max_rounds: int = Field(default=3, ge=1, le=6)
    categories: List[str] = Field(default_factory=list)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_relevance_score: float = Field(default=0.70, ge=0.0, le=1.0)
    min_quality_score: float = Field(default=0.68, ge=0.0, le=1.0)


class ResearchStreamEvent(BaseModel):
    """Generic NDJSON stream event."""

    type: str
    stage: str | None = None
    message: str | None = None
    data: dict | list | str | None = None


class ResearchDigestHistoryItem(BaseModel):
    id: int
    conversation_id: int
    query: str
    decision: str
    high_quality_papers_found: int
    total_unique_papers_scanned: int
    created_at: str
    rendered_digest_text: str | None = None


class ResearchDigestHistoryResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[ResearchDigestHistoryItem]
