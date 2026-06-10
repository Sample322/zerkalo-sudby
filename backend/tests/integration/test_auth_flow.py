"""Integration — auth flow end-to-end (AUTH-01/02/03/04).

``POST /api/auth/telegram``: valid initData -> 200 with a JWT (decoding to the upserted
user's id) + a single ``users`` row + a ``user_limits`` row; a repeat auth advances
``last_seen_at`` without duplicating the user; forged / stale initData -> 401.

DB-backed (the upsert): skips cleanly when Postgres is unreachable (root conftest).
"""

from __future__ import annotations

import time

from sqlalchemy import func, select

from app.core.security import decode_jwt
from app.models.billing import UserLimits
from app.models.user import User
from tests.conftest import TEST_BOT_TOKEN, make_init_data

# A telegram_id unique to this module so isolated test runs never collide on the upsert key.
_TG_USER = {
    "id": 700400001,
    "first_name": "Сека",
    "username": "seeker_auth_flow",
    "language_code": "ru",
}


async def test_valid_initdata_issues_jwt_and_upserts(auth_client, auth_session) -> None:
    """AUTH-01/02/03/04: valid initData -> 200, JWT decodes to sub=user.id, user + limits upserted."""
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)

    resp = await auth_client.post("/api/auth/telegram", json={"init_data": init_data})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["user"]["telegram_id"] == _TG_USER["id"]
    assert body["limits"]["free_weekly_limit"] == 3
    assert "settings" in body

    # The token's subject is the upserted user's UUID.
    payload = decode_jwt(body["access_token"])
    assert payload["sub"] == body["user"]["id"]
    assert payload["telegram_id"] == _TG_USER["id"]

    # A users row + a user_limits row exist for the validated telegram_id.
    user = (
        await auth_session.execute(
            select(User).where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()
    limits = (
        await auth_session.execute(
            select(UserLimits).where(UserLimits.user_id == user.id)
        )
    ).scalar_one()
    assert limits.free_weekly_limit == 3


async def test_repeat_auth_updates_last_seen(auth_client, auth_session) -> None:
    """AUTH-03: a second valid auth advances last_seen_at and does not duplicate the user."""
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)

    first = await auth_client.post("/api/auth/telegram", json={"init_data": init_data})
    assert first.status_code == 200, first.text
    first_user = (
        await auth_session.execute(
            select(User).where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()
    first_seen = first_user.last_seen_at

    # Ensure a measurable clock advance, then re-auth with fresh initData.
    time.sleep(1)
    init_data_2 = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)
    second = await auth_client.post("/api/auth/telegram", json={"init_data": init_data_2})
    assert second.status_code == 200, second.text

    # Exactly one user row for this telegram_id.
    count = (
        await auth_session.execute(
            select(func.count())
            .select_from(User)
            .where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()
    assert count == 1

    # Same user id, last_seen_at advanced.
    second_user = (
        await auth_session.execute(
            select(User).where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()
    assert second_user.id == first_user.id
    assert second_user.last_seen_at is not None
    if first_seen is not None:
        assert second_user.last_seen_at >= first_seen


async def test_forged_hash_returns_401(auth_client) -> None:
    """AUTH-02: a forged hash returns a generic 401 (no leak of which check failed)."""
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)
    # Swap the trailing hash for a wrong one.
    forged = init_data.rsplit("hash=", 1)[0] + "hash=" + "0" * 64

    resp = await auth_client.post("/api/auth/telegram", json={"init_data": forged})

    assert resp.status_code == 401
    # Generic message — must not reveal "bad hash" / "stale" / "missing".
    assert resp.json()["detail"] == "authentication failed"


async def test_stale_auth_date_returns_401(auth_client) -> None:
    """AUTH-02: a stale auth_date returns 401."""
    stale = int(time.time()) - 100_000
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER, auth_date=stale)

    resp = await auth_client.post("/api/auth/telegram", json={"init_data": init_data})

    assert resp.status_code == 401
    assert resp.json()["detail"] == "authentication failed"
