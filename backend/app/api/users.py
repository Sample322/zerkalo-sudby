"""``GET /api/me`` — the authenticated user's profile (AUTH-04, TZ §14.2).

Protected by ``get_current_user`` (Bearer JWT). Returns the same ``{user, limits, settings}``
projection as the auth response, minus the token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.user import User
from app.schemas.auth import MeResponse
from app.services.telegram_auth import get_user_limits

router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    limits = await get_user_limits(session, current_user.id)
    return MeResponse(
        user=current_user,
        limits=limits,
        settings=current_user,
    )


__all__ = ["router"]
