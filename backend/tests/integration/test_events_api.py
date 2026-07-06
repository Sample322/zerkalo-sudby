"""Integration — the client analytics sink ``POST /api/events`` (ANALYTICS-01).

Contract: Bearer-required; user_id is JWT-scoped (the body cannot carry one — ``extra=forbid``);
an allowlisted event is accepted (202) and written; an unknown name is still 202 but writes nothing
(best-effort, never surfaces an error). DB-backed; skips without Postgres.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.analytics import AppEvent
from tests.conftest import TEST_BOT_TOKEN, make_init_data

_USER = {"id": 700600111, "first_name": "Аналитик", "username": "evt_user"}


async def _auth(client) -> str:
    init_data = make_init_data(TEST_BOT_TOKEN, user=_USER)
    resp = await client.post("/api/auth/telegram", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _rows_by_name(event_name: str) -> list[AppEvent]:
    async with SessionLocal() as session:
        return list(
            (await session.execute(select(AppEvent).where(AppEvent.event_name == event_name)))
            .scalars()
            .all()
        )


async def test_requires_auth(auth_client) -> None:
    resp = await auth_client.post("/api/events", json={"event_name": "app_opened"})
    assert resp.status_code in (401, 403)


async def test_valid_event_accepted_and_written(auth_client) -> None:
    token = await _auth(auth_client)
    marker = uuid.uuid4().hex
    resp = await auth_client.post(
        "/api/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_name": "deck_selected", "properties": {"m": marker}},
    )
    assert resp.status_code == 202
    rows = await _rows_by_name("deck_selected")
    assert any(r.event_properties.get("m") == marker for r in rows)


async def test_unknown_event_still_202_no_row(auth_client) -> None:
    token = await _auth(auth_client)
    name = "unknown_" + uuid.uuid4().hex
    resp = await auth_client.post(
        "/api/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_name": name},
    )
    assert resp.status_code == 202
    assert await _rows_by_name(name) == []


async def test_body_cannot_spoof_user_id(auth_client) -> None:
    """A foreign user_id in the body is rejected (extra=forbid) — user is JWT-scoped only."""
    token = await _auth(auth_client)
    resp = await auth_client.post(
        "/api/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_name": "app_opened", "user_id": str(uuid.uuid4())},
    )
    assert resp.status_code == 422
