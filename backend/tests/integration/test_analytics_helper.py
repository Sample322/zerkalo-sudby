"""Integration — the best-effort ``record_event`` analytics writer (ANALYTICS-01).

Proves the two invariants that keep analytics off the critical path: unknown names are dropped, and
ANY write error is swallowed (never propagated). ``record_event`` uses its OWN ``SessionLocal`` (not a
passed-in session), so these rows are committed to the real test DB — asserted via a fresh session and
scoped to a unique ``user_id`` per test to avoid cross-test interference. Skips without Postgres.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.analytics import AppEvent
from app.services import analytics
from app.services.analytics import record_event


async def _rows_for(user_id: uuid.UUID) -> list[AppEvent]:
    async with SessionLocal() as session:
        return list(
            (await session.execute(select(AppEvent).where(AppEvent.user_id == user_id)))
            .scalars()
            .all()
        )


async def test_unknown_event_is_dropped(_db_ready: bool) -> None:
    """An event name not in the allowlist writes nothing and does not raise."""
    uid = uuid.uuid4()
    await record_event(uid, "definitely_not_allowed", {"x": 1})
    assert await _rows_for(uid) == []


async def test_valid_event_written(_db_ready: bool) -> None:
    """An allowlisted event writes exactly one row with the name + non-PII properties."""
    uid = uuid.uuid4()
    await record_event(uid, "deck_selected", {"deck_slug": "moon_mirror"})
    rows = await _rows_for(uid)
    assert len(rows) == 1
    assert rows[0].event_name == "deck_selected"
    assert rows[0].event_properties == {"deck_slug": "moon_mirror"}


async def test_none_user_is_allowed(_db_ready: bool) -> None:
    """An anonymous (user_id=None) event is legal — app_events.user_id is nullable by design."""
    await record_event(None, "app_opened", {})  # must not raise


async def test_write_error_is_swallowed(_db_ready: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failing session factory is swallowed — analytics must never propagate an error."""

    def _boom(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(analytics, "SessionLocal", _boom)
    # Must return normally despite the write blowing up.
    await record_event(uuid.uuid4(), "app_opened", {"deck_slug": "x"})
