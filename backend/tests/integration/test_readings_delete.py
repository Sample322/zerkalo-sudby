"""HIST-04 — soft-delete + restore + list-exclusion (RED until the 05-04 delete slice lands).

The ``DELETE /api/readings/{id}`` + ``POST /api/readings/{id}/restore`` endpoints (and the list they
feed) do not exist yet, so every test is ``xfail(strict=False)``: the suite stays green now and each
flips to ``xpass`` once the delete slice (05-04) + the list slice (05-02) are implemented. The
contract:

  * **soft delete** (HIST-04) — ``DELETE`` sets ``deleted_at`` (the row is retained, not hard-deleted)
    and the reading disappears from ``GET /api/readings``;
  * **excluded from list** (load-bearing invariant #1) — after deleting exactly one of two readings,
    the list omits exactly the deleted one;
  * **restore** (D-03) — ``POST /{id}/restore`` nulls ``deleted_at`` and the reading reappears in the
    list.

Readings are seeded through the shared ``create_completed_reading`` helper (FakeSafety+FakeLLM, no
Anthropic). Skips cleanly without Postgres (``seeded_catalog`` → ``auth_session`` → ``_db_ready``).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encode_jwt
from app.models import Reading, User
from tests.integration._history_helpers import (
    create_completed_reading,
    make_user_with_limits,
)

pytestmark = pytest.mark.xfail(
    reason="DELETE/restore /api/readings/{id} pending 05-04 (+ list 05-02)",
    strict=False,
)


async def _user_with_bearer(session: AsyncSession) -> tuple[User, dict[str, str]]:
    """A fresh user (with quota) + an ``Authorization`` header carrying a Bearer minted for it."""
    user = await make_user_with_limits(session)
    token = encode_jwt(sub=str(user.id), telegram_id=user.telegram_id)
    return user, {"Authorization": f"Bearer {token}"}


async def _list_ids(auth_client, auth: dict[str, str]) -> list[str]:
    """The ``reading_id`` values currently returned by ``GET /api/readings``."""
    resp = await auth_client.get("/api/readings", headers=auth)
    assert resp.status_code == 200, resp.text
    return [item["reading_id"] for item in resp.json()]


async def test_soft_delete_sets_deleted_at(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-04: DELETE sets ``deleted_at`` (row retained) and the reading leaves the list."""
    user, auth = await _user_with_bearer(auth_session)
    created = await create_completed_reading(auth_session, user)

    resp = await auth_client.delete(
        f"/api/readings/{created.reading_id}", headers=auth
    )
    assert resp.status_code in (200, 204), resp.text

    # The row still exists (soft delete) but now has a non-null deleted_at.
    auth_session.expire_all()
    row = await auth_session.get(Reading, uuid.UUID(created.reading_id))
    assert row is not None  # retained, not hard-deleted
    assert row.deleted_at is not None

    # And it is gone from the list.
    assert created.reading_id not in await _list_ids(auth_client, auth)


async def test_excluded_from_list(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """Invariant #1: deleting one of two readings omits exactly the deleted one from the list."""
    user, auth = await _user_with_bearer(auth_session)
    keep = await create_completed_reading(
        auth_session, user, question="Оставленный вопрос о моём пути на этой неделе?"
    )
    drop = await create_completed_reading(
        auth_session, user, question="Удаляемый вопрос о моих планах на выходные дни?"
    )

    resp = await auth_client.delete(f"/api/readings/{drop.reading_id}", headers=auth)
    assert resp.status_code in (200, 204), resp.text

    ids = await _list_ids(auth_client, auth)
    assert keep.reading_id in ids  # the survivor stays
    assert drop.reading_id not in ids  # exactly the deleted one is gone


async def test_restore_unsets_deleted_at(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """D-03: restore nulls ``deleted_at`` and the reading reappears in the list."""
    user, auth = await _user_with_bearer(auth_session)
    created = await create_completed_reading(auth_session, user)

    # Delete, then restore.
    deleted = await auth_client.delete(
        f"/api/readings/{created.reading_id}", headers=auth
    )
    assert deleted.status_code in (200, 204), deleted.text
    assert created.reading_id not in await _list_ids(auth_client, auth)

    restored = await auth_client.post(
        f"/api/readings/{created.reading_id}/restore", headers=auth
    )
    assert restored.status_code in (200, 204), restored.text

    # deleted_at is back to null and the reading is in the list again.
    auth_session.expire_all()
    row = await auth_session.get(Reading, uuid.UUID(created.reading_id))
    assert row is not None
    assert row.deleted_at is None
    assert created.reading_id in await _list_ids(auth_client, auth)
