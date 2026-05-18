"""Research digest router with NDJSON streaming."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.auth import get_current_user_email
from app.core.database import get_db
from app.core.models import ResearchDigest
from app.schemas.research import ResearchDigestRequest, ResearchDigestHistoryResponse, ResearchDigestHistoryItem
from app.services.auth_service import AuthService
from app.services.conversation_service import ConversationService
from app.services.research_digest_cache import get_research_digest_cache
from app.services.research_digest_service import get_research_digest_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])


def _to_ndjson_line(event: dict) -> str:
    return json.dumps(event, ensure_ascii=False) + "\n"


@router.post("/digest/stream")
async def stream_research_digest(
    request: ResearchDigestRequest,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream autonomous research digest events as NDJSON."""

    service = get_research_digest_service()
    cache = get_research_digest_cache()
    user = AuthService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user_id = int(user.id)

    if request.date_from and request.date_to and request.date_from > request.date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be earlier than or equal to date_to",
        )

    if request.conversation_id:
        try:
            conversation = ConversationService.get_conversation(db, request.conversation_id, user_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    else:
        title = ConversationService.generate_title_from_message(f"Research Digest: {request.query}")
        conversation = ConversationService.create_conversation(db, user_id, title=title)

    conversation_id = conversation.id

    cache_key = cache.build_key(
        {
            "query": request.query.strip().lower(),
            "batch_size": request.batch_size,
            "max_rounds": request.max_rounds,
            "categories": sorted([c.strip().lower() for c in request.categories if c.strip()]),
            "date_from": request.date_from.isoformat() if request.date_from else None,
            "date_to": request.date_to.isoformat() if request.date_to else None,
            "min_relevance_score": request.min_relevance_score,
            "min_quality_score": request.min_quality_score,
        }
    )

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield _to_ndjson_line(
                {
                    "type": "status",
                    "stage": "conversation",
                    "message": "Research digest linked to conversation.",
                    "data": {"conversation_id": conversation_id},
                }
            )

            cached = cache.get(cache_key)
            if cached:
                logger.info("[ResearchDigest] Cache hit for user=%s", user_email)
                cached_payload = {**cached, "cached": True, "conversation_id": conversation_id}
                digest_row = ResearchDigest(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    query=request.query,
                    filters_json=json.dumps(
                        {
                            "categories": request.categories,
                            "date_from": request.date_from.isoformat() if request.date_from else None,
                            "date_to": request.date_to.isoformat() if request.date_to else None,
                            "min_relevance_score": request.min_relevance_score,
                            "min_quality_score": request.min_quality_score,
                        },
                        ensure_ascii=False,
                    ),
                    result_json=json.dumps(cached_payload, ensure_ascii=False),
                    decision=str(cached_payload.get("decision", "sufficient_evidence")),
                    high_quality_papers_found=int(cached_payload.get("high_quality_papers_found", 0)),
                    total_unique_papers_scanned=int(cached_payload.get("total_unique_papers_scanned", 0)),
                )
                db.add(digest_row)
                db.commit()
                db.refresh(digest_row)
                cached_payload["digest_id"] = digest_row.id

                yield _to_ndjson_line(
                    {
                        "type": "status",
                        "stage": "cache",
                        "message": "Returning cached research digest result.",
                    }
                )
                yield _to_ndjson_line(
                    {
                        "type": "final",
                        "stage": "complete",
                        "data": cached_payload,
                    }
                )
                return

            final_payload = None
            async for event in service.generate_digest_events(
                query=request.query,
                batch_size=request.batch_size,
                max_rounds=request.max_rounds,
                categories=request.categories,
                date_from=request.date_from,
                date_to=request.date_to,
                min_relevance_score=request.min_relevance_score,
                min_quality_score=request.min_quality_score,
            ):
                if event.get("type") == "final":
                    final_payload = event.get("data")
                    continue
                yield _to_ndjson_line(event)

            if isinstance(final_payload, dict):
                final_payload["conversation_id"] = conversation_id

                digest_row = ResearchDigest(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    query=request.query,
                    filters_json=json.dumps(
                        {
                            "categories": request.categories,
                            "date_from": request.date_from.isoformat() if request.date_from else None,
                            "date_to": request.date_to.isoformat() if request.date_to else None,
                            "min_relevance_score": request.min_relevance_score,
                            "min_quality_score": request.min_quality_score,
                        },
                        ensure_ascii=False,
                    ),
                    result_json=json.dumps(final_payload, ensure_ascii=False),
                    decision=str(final_payload.get("decision", "sufficient_evidence")),
                    high_quality_papers_found=int(final_payload.get("high_quality_papers_found", 0)),
                    total_unique_papers_scanned=int(final_payload.get("total_unique_papers_scanned", 0)),
                )
                db.add(digest_row)
                db.commit()
                db.refresh(digest_row)
                final_payload["digest_id"] = digest_row.id
                cache.set(cache_key, final_payload)
                yield _to_ndjson_line(
                    {
                        "type": "final",
                        "stage": "complete",
                        "data": final_payload,
                    }
                )

        except Exception as exc:
            logger.error("[ResearchDigest] Stream failed: %s", str(exc), exc_info=True)
            error_event = {
                "type": "error",
                "stage": "failed",
                "message": "Research digest generation failed.",
                "data": {"error": str(exc)},
            }
            yield _to_ndjson_line(error_event)

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@router.get("/digests", response_model=ResearchDigestHistoryResponse)
async def get_research_digest_history(
    page: int = 1,
    page_size: int = 10,
    conversation_id: int | None = None,
    user_email: str = Depends(get_current_user_email),
    db: Session = Depends(get_db),
) -> ResearchDigestHistoryResponse:
    """Fetch paginated persisted research digest history for current user."""
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
    if page_size > 50:
        page_size = 50

    user = AuthService.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    user_id = int(user.id)

    query = db.query(ResearchDigest).filter(ResearchDigest.user_id == user_id)
    if conversation_id:
        query = query.filter(ResearchDigest.conversation_id == conversation_id)

    total = query.count()
    rows = (
        query.order_by(desc(ResearchDigest.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items: list[ResearchDigestHistoryItem] = []
    for row in rows:
        rendered = None
        try:
            parsed = json.loads(row.result_json) if row.result_json else {}
            rendered = parsed.get("rendered_digest_text")
        except Exception:
            rendered = None

        items.append(
            ResearchDigestHistoryItem(
                id=row.id,
                conversation_id=row.conversation_id,
                query=row.query,
                decision=row.decision,
                high_quality_papers_found=row.high_quality_papers_found,
                total_unique_papers_scanned=row.total_unique_papers_scanned,
                created_at=row.created_at.isoformat() if row.created_at else "",
                rendered_digest_text=rendered,
            )
        )

    return ResearchDigestHistoryResponse(
        page=page,
        page_size=page_size,
        total=total,
        items=items,
    )
