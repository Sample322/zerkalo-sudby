"""Client analytics sink — ``POST /api/events`` (ANALYTICS-01).

Bearer-authenticated; ``user_id`` comes from the JWT subject ONLY (never the body — ``EventIn`` is
``extra="forbid"`` and carries no user field). The event name is validated against the allowlist
inside ``record_event`` (unknown → dropped). Best-effort: the write is isolated (its own session,
swallow-all) and the endpoint ALWAYS returns 202 — even for an unknown name, an over-cap burst, or a
write failure — so a client analytics call can never surface an error or block the UI.

Hardening (SEC-01): analytics is a low-value write that opens its own pooled connection per call, so
an authenticated client could otherwise bloat ``app_events`` or exhaust the DB pool. Two cheap guards
keep it from becoming a DoS/bloat vector WITHOUT ever breaking the client: a per-user fail-open burst
cap (its own ``events`` Redis bucket, generous), and a bound on the ``properties`` payload (oversized
payloads are dropped — the event name is still counted, the JSONB stays small).
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.core.redis import throttle_ok
from app.models import User
from app.schemas.events import EventIn
from app.services.analytics import record_event

logger = logging.getLogger("app.events")

router = APIRouter(prefix="/events", tags=["events"])

# Generous per-user burst cap (a real session emits far fewer) — blocks bloat/DoS bursts only.
_EVENTS_WINDOW_S = 60
_EVENTS_BURST_CAP = 60
# Keep event_properties tiny (it is non-PII slugs/enums/counts) — drop anything abusive.
_MAX_PROPERTY_KEYS = 20
_MAX_PROPERTY_BYTES = 2048


def _bounded(properties: dict | None) -> dict | None:
    """Return ``properties`` if within the size bounds, else ``None`` (drop the payload, keep event)."""
    if not properties:
        return properties
    if len(properties) > _MAX_PROPERTY_KEYS:
        return None
    try:
        if len(json.dumps(properties, ensure_ascii=False)) > _MAX_PROPERTY_BYTES:
            return None
    except (TypeError, ValueError):
        return None
    return properties


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def track_event(
    body: EventIn,
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    """Record one client product event (best-effort, JWT-scoped). Always 202."""
    # Per-user fail-open burst cap: a Redis outage must not break analytics OR the client, so any
    # error here allows the write (the write itself is best-effort downstream).
    try:
        allowed = await throttle_ok(
            user.id, bucket="events", window_s=_EVENTS_WINDOW_S, burst_cap=_EVENTS_BURST_CAP
        )
    except Exception:  # noqa: BLE001 - fail open, never surface Redis trouble to the client
        logger.warning("events_throttle_unavailable_fail_open")
        allowed = True
    if not allowed:
        return {"ok": True}  # silently drop the over-cap event — never 429 a fire-and-forget call

    await record_event(user.id, body.event_name, _bounded(body.properties))
    return {"ok": True}


__all__ = ["router"]
