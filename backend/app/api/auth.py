"""``POST /api/auth/telegram`` — the auth entrypoint (AUTH-01/02/03/04).

Thin router: it parses the request, delegates to ``services.telegram_auth.authenticate``
(validate -> upsert -> JWT), and projects the result into ``AuthResponse``. There is NO
business logic here and ``telegram_id`` is NEVER read from the request body — identity comes
only from the validated ``init_data`` inside the service (threat T-04-01).

Every validation failure (bad hash / stale / missing) is collapsed into a single generic
401 so the cause is not leaked as an oracle (threat T-04-07).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.schemas.auth import AuthRequest, AuthResponse
from app.services.telegram_auth import authenticate, get_user_limits, project_limits

logger = logging.getLogger("app.auth")

router = APIRouter(tags=["auth"])


@router.post("/auth/telegram", response_model=AuthResponse)
async def auth_telegram(
    body: AuthRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    try:
        user, token = await authenticate(body.init_data, session)
    except ValueError:
        # Every validation failure collapses to a single generic 401 so the cause is never
        # leaked as an oracle (T-04-07). A terse, detail-free log marks the rejection for ops.
        logger.info("auth.initdata_rejected")
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "authentication failed"
        ) from None

    limits = await get_user_limits(session, user.id)
    return AuthResponse(
        access_token=token,
        user=user,
        limits=project_limits(limits, user.telegram_id),
        settings=user,
    )


__all__ = ["router"]
