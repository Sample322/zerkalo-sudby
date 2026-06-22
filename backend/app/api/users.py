"""``GET /api/me`` + ``PATCH /api/me/settings`` — the authenticated user's profile (AUTH-04 /
PROF-01 / PROF-02, TZ §14.2).

Both routes are protected by ``get_current_user`` (Bearer JWT). ``GET /api/me`` returns the same
``{user, limits, settings}`` projection as the auth response, minus the token (no schema change —
PROF-01). ``PATCH /api/me/settings`` is the settings write path (PROF-02 / D-09): a partial update
of the three boolean flags, always scoped to the JWT user (never the request body — T-05-SPOOF).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.auth import MeResponse, SettingsOut, SettingsPatch
from app.services.telegram_auth import get_user_limits, project_limits

router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    limits = await get_user_limits(session, current_user.id)
    return MeResponse(
        user=current_user,
        limits=project_limits(limits, current_user.telegram_id),
        settings=current_user,
    )


@router.patch("/me/settings", response_model=SettingsOut)
async def patch_settings(
    body: SettingsPatch,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SettingsOut:
    """Partially update the authenticated user's settings flags (PROF-02 / D-09).

    Applies ONLY the keys actually present in the request body (``exclude_unset``) to the JWT
    user's row, so an omitted flag is left untouched — the partial-update invariant. The target
    is always ``current_user`` (the JWT ``sub``); the body carries no identity, so a forged
    ``user_id`` has no effect (threat T-05-SPOOF). An empty body is a no-op that returns the
    current settings (200). Returns the full ``SettingsOut`` reflecting the new state.
    """
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await session.commit()
    return SettingsOut.model_validate(current_user)


__all__ = ["router"]
