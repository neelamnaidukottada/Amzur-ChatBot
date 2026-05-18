"""In-memory cache for research digest results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import hashlib
import json
import logging

from app.core.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CachedResearchDigest:
    """Represents a cached research digest payload."""

    created_at: datetime
    payload: Dict[str, Any]

    def is_expired(self, ttl_minutes: int) -> bool:
        return datetime.utcnow() - self.created_at > timedelta(minutes=ttl_minutes)


class ResearchDigestCache:
    """Simple in-memory cache for research digest outputs."""

    def __init__(self, ttl_minutes: int = 60):
        self.ttl_minutes = ttl_minutes
        self._cache: Dict[str, CachedResearchDigest] = {}

    @staticmethod
    def build_key(payload: Dict[str, Any]) -> str:
        normalized = {k: payload[k] for k in sorted(payload.keys())}
        encoded = json.dumps(normalized, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        cached = self._cache.get(key)
        if not cached:
            return None

        if cached.is_expired(self.ttl_minutes):
            del self._cache[key]
            logger.info("[ResearchDigestCache] Expired key removed")
            return None

        return cached.payload

    def set(self, key: str, payload: Dict[str, Any]) -> None:
        self._cache[key] = CachedResearchDigest(created_at=datetime.utcnow(), payload=payload)
        logger.info("[ResearchDigestCache] Stored digest result")


_research_digest_cache: Optional[ResearchDigestCache] = None


def get_research_digest_cache() -> ResearchDigestCache:
    global _research_digest_cache
    if _research_digest_cache is None:
        _research_digest_cache = ResearchDigestCache(ttl_minutes=settings.RESEARCH_CACHE_TTL_MINUTES)
    return _research_digest_cache
