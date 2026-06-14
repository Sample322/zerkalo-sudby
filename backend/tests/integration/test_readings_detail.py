"""HIST-03/04 — ``GET /api/readings/{id}`` detail (RED until the 05-02 detail slice lands).

The detail endpoint does not exist yet, so every test is ``xfail(strict=False)``: the suite stays
green now and each flips to ``xpass`` once ``GET /api/readings/{id}`` is implemented (05-02). The
contract:

  * **immutable** (HIST-03) — a stored reading is read back as-is; a second GET returns a
    byte-identical body (no regeneration, no re-draw — the reading is frozen once completed);
  * **deleted → 404** (HIST-04 / RESEARCH Pitfall 4) — a soft-deleted reading is not served by id.

Readings are seeded through the shared ``create_completed_reading`` helper (FakeSafety+FakeLLM, no
Anthropic) for the JWT user, asserted over the in-process ``auth_client`` + a real Bearer. Skips
cleanly without Postgres (``seeded_catalog`` → ``auth_session`` → ``_db_ready``).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encode_jwt
from app.models import Reading, User
from app.models.enums import ReadingStatus
from tests.integration._history_helpers import (
    create_completed_reading,
    make_user_with_limits,
)

pytestmark = pytest.mark.xfail(
    reason="GET /api/readings/{id} pending 05-02 (history detail slice)",
    strict=False,
)


async def _user_with_bearer(session: AsyncSession) -> tuple[User, dict[str, str]]:
    """A fresh user (with quota) + an ``Authorization`` header carrying a Bearer minted for it."""
    user = await make_user_with_limits(session)
    token = encode_jwt(sub=str(user.id), telegram_id=user.telegram_id)
    return user, {"Authorization": f"Bearer {token}"}


async def test_detail_immutable(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-03: two GETs of the same reading return identical bodies (frozen, no regeneration)."""
    user, auth = await _user_with_bearer(auth_session)
    created = await create_completed_reading(auth_session, user)

    first = await auth_client.get(f"/api/readings/{created.reading_id}", headers=auth)
    assert first.status_code == 200, first.text
    second = await auth_client.get(f"/api/readings/{created.reading_id}", headers=auth)
    assert second.status_code == 200, second.text

    # Byte-identical: the stored reading is immutable — the second read does not regenerate it.
    assert first.json() == second.json()
    # And it reflects the persisted reading: the id round-trips and the cards/summary are present.
    body = first.json()
    assert body["reading_id"] == created.reading_id
    assert body["cards"]
    assert body["summary"] is not None


async def test_detail_deleted_404(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-04 / Pitfall 4: a soft-deleted reading is not served by id (404)."""
    user, auth = await _user_with_bearer(auth_session)
    created = await create_completed_reading(auth_session, user)

    # Soft-delete directly in the session (the delete endpoint is exercised in test_readings_delete).
    row = await auth_session.get(Reading, uuid.UUID(created.reading_id))
    assert row is not None
    row.deleted_at = datetime.now(UTC)
    await auth_session.flush()

    resp = await auth_client.get(f"/api/readings/{created.reading_id}", headers=auth)
    assert resp.status_code == 404, resp.text


async def test_detail_unknown_id_404(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-03: an unknown reading id → 404 (never a 500, never another user's reading)."""
    _user, auth = await _user_with_bearer(auth_session)
    # A valid-shaped but non-existent UUID.
    missing = (
        await auth_session.execute(select(Reading).where(Reading.id == uuid.uuid4()))
    ).scalar_one_or_none()
    assert missing is None

    resp = await auth_client.get(f"/api/readings/{uuid.uuid4()}", headers=auth)
    assert resp.status_code == 404, resp.text


async def test_detail_completed_status(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-03: the served detail carries the persisted COMPLETED status."""
    user, auth = await _user_with_bearer(auth_session)
    created = await create_completed_reading(auth_session, user)

    resp = await auth_client.get(f"/api/readings/{created.reading_id}", headers=auth)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == ReadingStatus.COMPLETED.value
