"""Admin routes — guarded by the server-side ``ADMIN_TELEGRAM_IDS`` allowlist (AUTH-05).

``GET /api/admin/ping`` is the testable allowlist probe: it exists so the ``require_admin``
gate is exercised before the real admin bodies arrive in Phase 8. A non-allowlisted
``telegram_id`` gets 403; an allowlisted one gets 200 ``{"ok": true}`` (threat T-04-04).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
async def admin_ping(admin: User = Depends(require_admin)) -> dict[str, bool]:
    """Allowlist probe — reachable only by an admin ``telegram_id`` (else 403)."""
    return {"ok": True}


__all__ = ["router"]
