"""Best-effort product-analytics writer for ``app_events`` (ANALYTICS-01).

``record_event`` NEVER shares the caller's transaction and NEVER breaks the core flow: it opens its
OWN short-lived session, inserts one row, commits, and swallows ALL errors — a down/slow analytics
write must never 500 a reading or a payment (the same lesson as the P6 throttle fail-open). Unknown
event names are dropped silently (the allowlist). ``event_properties`` are expected to be tiny and
NON-PII (slugs / enums / counts) — NEVER the question text, names, or any personal content.
"""

from __future__ import annotations

import logging
import uuid

from app.core.db import SessionLocal
from app.models.analytics import AppEvent

logger = logging.getLogger("app.analytics")

# The key product funnel (ANALYTICS-01 / ROADMAP criterion 3). Client-emitted via POST /api/events
# (the reading + payment outcomes are emitted from the client flow, which observes the response /
# the return from the payment page). Anything not in this set is dropped.
EVENT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "app_opened",
        "onboarding_started",
        "onboarding_completed",
        "question_entered",
        "topic_selected",
        "deck_selected",
        "spread_selected",
        "card_revealed",
        "summary_viewed",
        "history_opened",
        "paywall_viewed",
        "product_clicked",
        "settings_changed",
        "reading_started",
        "reading_completed",
        "reading_failed",
        "payment_succeeded",
        "subscription_started",
        "payment_failed",
    }
)


async def record_event(
    user_id: uuid.UUID | None,
    event_name: str,
    properties: dict | None = None,
) -> None:
    """Write one ``app_events`` row, best-effort. Unknown names are a no-op; all errors are swallowed."""
    if event_name not in EVENT_ALLOWLIST:
        return
    try:
        async with SessionLocal() as session:
            session.add(
                AppEvent(
                    user_id=user_id,
                    event_name=event_name,
                    event_properties=properties or {},
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001 - best-effort: analytics must never break the core flow
        logger.warning("app_event_write_failed", extra={"event_name": event_name})


__all__ = ["record_event", "EVENT_ALLOWLIST"]
