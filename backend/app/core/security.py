"""JWT session tokens (AUTH-04) — PyJWT HS256.

The backend issues a short-lived JWT after a successful ``initData`` validation; the
frontend echoes it as a ``Bearer`` on later requests (RESEARCH Pattern 5). ``decode_jwt``
**pins** ``algorithms=["HS256"]`` so an attacker cannot downgrade to ``alg:none`` and strip
the signature (threat T-04-03). ``exp`` is verified automatically by PyJWT on decode;
``ExpiredSignatureError`` / ``InvalidTokenError`` propagate so callers can map them to 401.

Secrets come only from ``settings`` (env) — never hardcoded (threat T-04-08).
"""

from __future__ import annotations

import time

import jwt

from app.core.config import settings

_ALGORITHM = "HS256"


def encode_jwt(
    sub: str,
    telegram_id: int,
    expires_in: int | None = None,
) -> str:
    """Sign a session token.

    Claims: ``sub`` (user UUID as str), ``telegram_id`` (int, convenience), ``iat``, ``exp``.
    ``expires_in`` defaults to ``settings.JWT_EXPIRE_SECONDS``; a negative value yields an
    already-expired token (used in tests).
    """
    if expires_in is None:
        expires_in = settings.JWT_EXPIRE_SECONDS

    now = int(time.time())
    payload = {
        "sub": sub,
        "telegram_id": telegram_id,
        "iat": now,
        "exp": now + expires_in,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=_ALGORITHM)


def decode_jwt(token: str) -> dict:
    """Verify + decode a session token.

    Pins ``algorithms=["HS256"]`` (rejects ``alg:none``) and verifies the signature + ``exp``.
    Raises ``jwt.ExpiredSignatureError`` on expiry and ``jwt.InvalidTokenError`` (its base
    class) on any other failure — including an unsigned ``none`` token.
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[_ALGORITHM])


__all__ = ["encode_jwt", "decode_jwt"]
