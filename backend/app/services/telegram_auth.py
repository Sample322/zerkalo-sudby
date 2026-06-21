"""Telegram ``initData`` validation + auth orchestration (the auth security spine).

This module is the single most security-critical surface in the product (AUTH-01..05).
It has two layers:

* **Pure crypto (no DB):** ``validate_init_data`` implements the documented two-stage HMAC
  EXACTLY (RESEARCH Pattern 3) with a constant-time compare and an ``auth_date`` freshness
  check; ``parse_user`` extracts the validated ``user`` blob. These are unit-testable
  without a session.
* **Orchestration (DB):** ``authenticate`` validates -> derives ``telegram_id`` ONLY from
  the validated ``user`` (never the request body, threat T-04-01) -> upserts the user +
  ensures a ``user_limits`` row -> issues a JWT.

Threats mitigated here: spoofed ``telegram_id`` (T-04-01), replay of leaked initData
(T-04-02, freshness window), timing attack on the hash compare (T-04-05,
``hmac.compare_digest``), SQL injection in the upsert (T-04-09, parameterized
``on_conflict_do_update``).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from urllib.parse import parse_qsl

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import encode_jwt
from app.models.billing import UserLimits
from app.models.user import User

# The HMAC key constant fixed by Telegram for the first stage. A missing ``"WebAppData"``
# constant in the code is the canonical warning sign of a broken validator (PITFALLS 1).
_WEBAPP_DATA_KEY = b"WebAppData"

# Default weekly free allowance for a brand-new user (TZ §13.11; mirrors the model default).
_FREE_WEEKLY_LIMIT = 3


def validate_init_data(init_data: str, bot_token: str, max_age: int) -> dict[str, str]:
    """Validate a raw Telegram ``initData`` query string (two-stage HMAC + freshness).

    Returns the parsed field dict (``user`` is still a JSON *string* — call ``parse_user``).
    Raises ``ValueError`` on any failure: missing hash, signature mismatch, or stale
    ``auth_date``. The caller maps every ``ValueError`` to a single generic 401 so the
    failure cause is never leaked as an oracle (threat T-04-07).

    Algorithm (RESEARCH Pattern 3, do NOT alter):
        secret_key = HMAC_SHA256(key=b"WebAppData", msg=bot_token)
        expected   = HMAC_SHA256(key=secret_key, msg=data_check_string).hexdigest()
    where ``data_check_string`` is the ``\\n``-joined, key-sorted ``k=v`` of every field
    EXCEPT ``hash`` (``signature`` is INCLUDED — current Telegram hashes it), URL-decoded.
    """
    # strict_parsing rejects malformed pairs; keep_blank_values retains present-but-empty
    # fields (Telegram includes every received field in the hash, blank ones too).
    pairs = dict(parse_qsl(init_data, strict_parsing=True, keep_blank_values=True))

    received_hash = pairs.pop("hash", None)
    # `signature` (Telegram's Ed25519 field) MUST stay in the data-check string: current
    # Telegram computes the HMAC `hash` over EVERY field except `hash` itself — signature
    # INCLUDED. Verified against a live initData (exclude it → mismatch; keep it → match).
    if not received_hash:
        raise ValueError("missing hash")

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(_WEBAPP_DATA_KEY, bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    # Constant-time compare — never use ``==`` on the digests (threat T-04-05).
    if not hmac.compare_digest(computed, received_hash):
        raise ValueError("bad hash")

    # Replay defense: reject initData older than the freshness window (threat T-04-02).
    auth_date = int(pairs.get("auth_date", "0"))
    if time.time() - auth_date > max_age:
        raise ValueError("expired")

    return pairs


def parse_user(pairs: dict[str, str]) -> dict:
    """Parse the validated ``user`` JSON blob. ``user["id"]`` is the telegram_id."""
    raw = pairs.get("user")
    if not raw:
        raise ValueError("missing user")
    return json.loads(raw)


async def authenticate(init_data: str, session: AsyncSession) -> tuple[User, str]:
    """Validate -> upsert the user (+ ensure user_limits) -> return ``(user, jwt)``.

    ``telegram_id`` is derived ONLY from the validated ``user`` blob (threat T-04-01); the
    request body is never trusted for identity. The upsert is a single atomic Postgres
    ``INSERT ... ON CONFLICT (telegram_id) DO UPDATE`` (threat T-04-09 — no string-built SQL,
    no SELECT-then-INSERT race).
    """
    pairs = validate_init_data(
        init_data, settings.BOT_TOKEN, settings.INITDATA_MAX_AGE_SECONDS
    )
    tg = parse_user(pairs)
    telegram_id = int(tg["id"])  # validated identity — the only trusted source
    now = datetime.now(UTC)

    stmt = (
        pg_insert(User)
        .values(
            telegram_id=telegram_id,
            username=tg.get("username"),
            first_name=tg.get("first_name"),
            last_name=tg.get("last_name"),
            language_code=tg.get("language_code"),
            photo_url=tg.get("photo_url"),
            is_premium_telegram=bool(tg.get("is_premium", False)),
            last_seen_at=now,
        )
        .on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={
                "username": tg.get("username"),
                "first_name": tg.get("first_name"),
                "last_name": tg.get("last_name"),
                "language_code": tg.get("language_code"),
                "photo_url": tg.get("photo_url"),
                "last_seen_at": now,
                "updated_at": now,
            },
        )
        .returning(User)
    )
    user = (await session.execute(stmt)).scalar_one()

    await _ensure_user_limits(session, user.id)
    await session.commit()
    await session.refresh(user)

    token = encode_jwt(sub=str(user.id), telegram_id=user.telegram_id)
    return user, token


async def _ensure_user_limits(session: AsyncSession, user_id) -> None:
    """Ensure a ``user_limits`` row exists for the user (race-safe, D-02).

    A single ``INSERT ... ON CONFLICT (user_id) DO NOTHING`` (relying on the
    ``uq_user_limits_user_id`` UNIQUE constraint). Two concurrent first-logins for the same
    brand-new user therefore create exactly ONE row — no SELECT-then-INSERT race, no duplicate
    row (threat T-06-01 / Pattern 5). ``week_start`` is deliberately OMITTED so the row is
    created with ``week_start = NULL``: the rolling window anchors on the *first reading*, NOT
    an ISO-Monday date (D-01/D-02). Idempotent — a repeat login is a no-op conflict.
    """
    stmt = (
        pg_insert(UserLimits)
        .values(
            user_id=user_id,
            free_weekly_limit=_FREE_WEEKLY_LIMIT,
            free_used_this_week=0,
        )
        .on_conflict_do_nothing(index_elements=["user_id"])
    )
    await session.execute(stmt)


async def get_user_limits(session: AsyncSession, user_id) -> UserLimits | None:
    """Read the caller's ``user_limits`` row (for /api/auth/telegram + /api/me responses)."""
    return (
        await session.execute(
            select(UserLimits).where(UserLimits.user_id == user_id)
        )
    ).scalar_one_or_none()


__all__ = [
    "validate_init_data",
    "parse_user",
    "authenticate",
    "get_user_limits",
]
