"""HIST-01/02/06 — ``GET /api/readings`` history list (RED until the 05-02 list slice lands).

The list endpoint does not exist yet, so every test here is marked ``xfail(strict=False)``: a full
``uv run pytest -q`` stays green now, and each flips to ``xpass`` once ``GET /api/readings`` is
implemented (05-02). They describe the exact contract the slice must satisfy:

  * **auto-save visible** (HIST-01) — a completed reading appears in the list;
  * **light shape + newest-first order** (HIST-02) — list items carry only the light history fields
    (no full per-card ``interpretation`` / ``cards`` array), newest first;
  * **last-10 cap retains data** (HIST-06, load-bearing invariant #2) — 12 completed readings → the
    list returns exactly 10, while the 11th/12th oldest rows are STILL in the DB (retained, NOT
    pruned).

The readings are seeded through the shared ``create_completed_reading`` helper (FakeSafety+FakeLLM,
no Anthropic) for the JWT-authenticated user — never by re-driving ``POST /api/readings`` inline. The
HTTP assertions go through the in-process ``auth_client`` + a real Bearer (mirrors
``test_readings_auth.py``). Everything skips cleanly without Postgres (via ``seeded_catalog`` →
``auth_session`` → ``_db_ready``).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encode_jwt
from app.models import Reading, User
from app.models.enums import ReadingStatus
from tests.conftest import TEST_BOT_TOKEN, make_init_data
from tests.integration._history_helpers import (
    create_completed_reading,
    make_user_with_limits,
)

pytestmark = pytest.mark.xfail(
    reason="GET /api/readings pending 05-02 (history list slice)",
    strict=False,
)

# The light fields a history list item is allowed to carry (HIST-02 — date/question/deck/spread/
# thumbnails/short summary). The full per-card interpretation + cards array must NOT be present.
_LIGHT_ITEM_FIELDS = {
    "reading_id",
    "created_at",
    "question",
    "deck_name",
    "spread_name",
    "card_thumbnails",
    "summary_short",
}
# Heavy detail fields that belong to GET /{id}, never to a list item (HIST-02 light shape).
_HEAVY_ITEM_FIELDS = {"cards", "interpretation", "summary"}

_TG_USER = {
    "id": 770500050,
    "first_name": "Хранитель",
    "username": "seeker_history",
    "language_code": "ru",
}


async def _bearer(client) -> str:
    """Authenticate the sample Telegram user (upserts the User row) and return the Bearer token."""
    init_data = make_init_data(TEST_BOT_TOKEN, user=_TG_USER)
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _jwt_user(session: AsyncSession) -> User:
    """Fetch the (already-upserted) JWT user from the isolated session by ``telegram_id``."""
    return (
        await session.execute(
            select(User).where(User.telegram_id == _TG_USER["id"])
        )
    ).scalar_one()


async def test_auto_save_appears_in_list(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-01: a completed reading is auto-saved and then appears in ``GET /api/readings``."""
    token = await _bearer(auth_client)
    user = await _jwt_user(auth_session)
    created = await create_completed_reading(auth_session, user)
    assert created.status == ReadingStatus.COMPLETED.value

    resp = await auth_client.get(
        "/api/readings", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert isinstance(items, list)
    assert any(item["reading_id"] == created.reading_id for item in items)


async def test_shape_and_order(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-02: list items are light (no full cards/interpretation) and ordered newest-first."""
    token = await _bearer(auth_client)
    user = await _jwt_user(auth_session)
    first = await create_completed_reading(
        auth_session, user, question="Первый вопрос о моём ближайшем будущем сейчас?"
    )
    second = await create_completed_reading(
        auth_session, user, question="Второй вопрос о моих отношениях на этой неделе?"
    )

    resp = await auth_client.get(
        "/api/readings", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    assert len(items) >= 2

    # Light shape: every list item carries only the light fields, never the heavy detail payload.
    for item in items:
        assert _LIGHT_ITEM_FIELDS.issuperset(item.keys()), item.keys()
        assert not _HEAVY_ITEM_FIELDS.intersection(item.keys()), item.keys()

    # Newest-first: the most recently created reading is at the head of the list.
    returned_ids = [item["reading_id"] for item in items]
    assert returned_ids.index(second.reading_id) < returned_ids.index(first.reading_id)


async def test_last_ten_cap(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-06 / invariant #2: 12 completed readings → list returns 10, older rows retained by id."""
    # A user seeded with a HIGH weekly limit so all 12 readings COMPLETE (the default 3/week would
    # paywall the 4th — see _history_helpers module docstring), with a Bearer minted directly for
    # that same user so the list request resolves to the user the readings belong to.
    user = await make_user_with_limits(auth_session, free_weekly_limit=100)
    token = encode_jwt(sub=str(user.id), telegram_id=user.telegram_id)

    created = [
        await create_completed_reading(
            auth_session,
            user,
            question=f"Вопрос номер {n} о том, что меня ждёт впереди скоро?",
        )
        for n in range(12)
    ]
    assert all(r.status == ReadingStatus.COMPLETED.value for r in created)

    resp = await auth_client.get(
        "/api/readings", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200, resp.text
    items = resp.json()
    # The cap returns exactly the last 10.
    assert len(items) == 10

    # Retained, NOT pruned: the 2 oldest readings are still fetchable directly from the DB by id.
    oldest_two = [created[0].reading_id, created[1].reading_id]
    for reading_id in oldest_two:
        row = await auth_session.get(Reading, uuid.UUID(reading_id))
        assert row is not None
        assert row.deleted_at is None  # retained, not soft-deleted
