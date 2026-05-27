"""Reusable helpers for sending events to n8n webhooks."""

from __future__ import annotations

import logging
from datetime import datetime

import httpx

from app.core.models import User
from app.core.settings import settings

logger = logging.getLogger(__name__)


def _format_created_at(created_at: datetime | None) -> str:
    """Format a timestamp for the webhook payload."""
    value = created_at or datetime.utcnow()
    if value.tzinfo is None:
        return value.isoformat() + "Z"
    return value.isoformat()


async def triggerUserOnboardingWebhook(user: User) -> None:
    """Send the user registration event to n8n without blocking the request."""
    webhook_url = settings.N8N_WEBHOOK_URL.strip()
    if not webhook_url:
        logger.info("Skipping user onboarding webhook because N8N_WEBHOOK_URL is not configured")
        return

    payload = {
        "event": "user_registered",
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name or "",
        "auth_provider": user.auth_provider or "email",
        "created_at": _format_created_at(user.created_at),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
        logger.info(
            "User onboarding webhook sent successfully for user_id=%s email=%s provider=%s",
            user.id,
            user.email,
            payload["auth_provider"],
        )
    except httpx.HTTPStatusError as exc:
        logger.exception(
            "User onboarding webhook returned HTTP %s for user_id=%s email=%s",
            exc.response.status_code,
            user.id,
            user.email,
        )
    except httpx.RequestError:
        logger.exception(
            "User onboarding webhook request failed for user_id=%s email=%s",
            user.id,
            user.email,
        )
    except Exception:
        logger.exception(
            "Unexpected error while sending user onboarding webhook for user_id=%s email=%s",
            user.id,
            user.email,
        )
