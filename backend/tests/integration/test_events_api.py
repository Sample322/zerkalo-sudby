"""Integration — the client analytics sink ``POST /api/events`` (ANALYTICS-01).

Contract: Bearer-required; user_id is JWT-scoped (the body cannot carry one — ``extra=forbid``);
an allowlisted event is accepted (202) and written; an unknown name is still 202 but writes nothing
(best-effort, never surfaces an error). DB-backed; skips without Postgres.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.api import events as events_module
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


# --- SEC-01 hardening: fail-open per-user cap + bounded properties (DoS/bloat guard) ---


def test_bounded_drops_oversized_properties() -> None:
    """`_bounded` keeps small payloads and drops abusive ones (too many keys / too many bytes)."""
    assert events_module._bounded(None) is None
    assert events_module._bounded({"deck_slug": "moon"}) == {"deck_slug": "moon"}
    assert events_module._bounded({str(i): i for i in range(25)}) is None
    assert events_module._bounded({"x": "y" * 5000}) is None


async def test_over_cap_event_is_dropped(auth_client, monkeypatch) -> None:
    """When the per-user cap is hit, the event is silently dropped (202, no write) — never 429."""
    token = await _auth(auth_client)

    async def _blocked(*_a: object, **_k: object) -> bool:
        return False

    monkeypatch.setattr(events_module, "throttle_ok", _blocked)
    marker = uuid.uuid4().hex
    resp = await auth_client.post(
        "/api/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_name": "deck_selected", "properties": {"m": marker}},
    )
    assert resp.status_code == 202
    rows = await _rows_by_name("deck_selected")
    assert not any(r.event_properties.get("m") == marker for r in rows)


async def test_throttle_error_fails_open(auth_client, monkeypatch) -> None:
    """A Redis error in the cap check fails OPEN — the event is still written, still 202."""
    token = await _auth(auth_client)

    async def _boom(*_a: object, **_k: object) -> bool:
        raise RuntimeError("redis down")

    monkeypatch.setattr(events_module, "throttle_ok", _boom)
    marker = uuid.uuid4().hex
    resp = await auth_client.post(
        "/api/events",
        headers={"Authorization": f"Bearer {token}"},
        json={"event_name": "deck_selected", "properties": {"m": marker}},
    )
    assert resp.status_code == 202
    rows = await _rows_by_name("deck_selected")
    assert any(r.event_properties.get("m") == marker for r in rows)
