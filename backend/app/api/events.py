"""Client analytics sink — ``POST /api/events`` (ANALYTICS-01).

Bearer-authenticated; ``user_id`` comes from the JWT subject ONLY (never the body — ``EventIn`` is
``extra="forbid"`` and carries no user field). The event name is validated against the allowlist
inside ``record_event`` (unknown → dropped). Best-effort: the write is isolated (its own session,
swallow-all) and the endpoint ALWAYS returns 202 — even for an unknown name or a write failure — so a
client analytics call can never surface an error or block the UI.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user
from app.models import User
from app.schemas.events import EventIn
from app.services.analytics import record_event

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def track_event(
    body: EventIn,
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    """Record one client product event (best-effort, JWT-scoped). Always 202."""
    await record_event(user.id, body.event_name, body.properties)
    return {"ok": True}


__all__ = ["router"]
