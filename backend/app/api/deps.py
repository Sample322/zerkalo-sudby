"""Shared FastAPI dependencies.

Re-exports the DB + Redis providers and adds the auth dependencies (RESEARCH Pattern 5):

* ``get_current_user`` — extracts + verifies the ``Bearer`` JWT and loads the user; any
  expired / invalid / unknown token yields 401 (threat T-04-03).
* ``require_admin`` — server-side ``ADMIN_TELEGRAM_IDS`` allowlist; a non-allowlisted
  ``telegram_id`` yields 403 (threat T-04-04). The frontend guard is cosmetic only.
"""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.redis import get_redis
from app.core.security import decode_jwt
from app.models.user import User

# auto_error=True -> a missing/malformed Authorization header is a 403 from the security
# scheme itself; an invalid *token* is mapped to 401 below.
_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    cred: HTTPAuthorizationCredentials = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Resolve the authenticated user from a verified ``Bearer`` JWT.

    Raises 401 on an expired token, an otherwise-invalid token (bad signature, ``alg:none``),
    or a ``sub`` that no longer maps to a user.
    """
    try:
        payload = decode_jwt(cred.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "token expired"
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "invalid token"
        ) from exc

    user = await session.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown user")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Server-side admin allowlist gate (deny-by-default)."""
    if user.telegram_id not in settings.ADMIN_TELEGRAM_IDS:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    return user


async def throttle_gate(user: User = Depends(get_current_user)) -> None:
    """GATE 0 for ``POST /api/readings`` — anti-burst throttle before any PG/LLM work (LIMIT-05).

    Over the burst cap → HTTP 429 (retryable, the FE's ``kind:"throttle"`` discriminant, D-08);
    under the cap it is a no-op. Depends ONLY on ``get_current_user`` so it keys off the verified
    JWT ``user.id`` (never a request-body field, T-06 spoofing) and — deliberately — does NOT
    open a DB session, so the 429 short-circuits BEFORE any Postgres transaction opens (success-
    criterion 4). The atomic Lua throttle lives in ``core.redis``; the import is local to keep the
    Redis dependency off this module's import-time surface.
    """
    from app.core.redis import throttle_ok

    if not await throttle_ok(user.id):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "throttled")


__all__ = [
    "get_session",
    "get_redis",
    "get_current_user",
    "require_admin",
    "throttle_gate",
]
