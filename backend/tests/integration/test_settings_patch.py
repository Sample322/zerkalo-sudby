"""PROF-02 — ``PATCH /api/me/settings`` partial update + round-trip + reversals source (RED).

The settings PATCH endpoint does not exist yet, so every test is ``xfail(strict=False)``: the suite
stays green now and each flips to ``xpass`` once ``PATCH /api/me/settings`` is implemented (05-03).
The contract:

  * **partial round-trip** (load-bearing invariant #3) — PATCHing only one flag flips it and LEAVES
    the others untouched; a follow-up ``GET /api/me`` reflects the change;
  * **JWT-scoped, not body-scoped** (T-05-SPOOF / V4) — a forged ``user_id`` in the PATCH body is
    ignored; only the authenticated (JWT) user is mutated;
  * **reversals source** (D-09) — after ``PATCH reversals_enabled=false`` a subsequently created
    reading draws upright-only (the draw sources reversals from the PERSISTED user flag, not the
    request body), asserted on the persisted ``reading_cards`` orientations.

Skips cleanly without Postgres (``seeded_catalog`` / ``auth_session`` → ``_db_ready``).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import encode_jwt
from app.models import Reading, ReadingCard, User
from app.models.enums import Orientation
from tests.integration._history_helpers import (
    create_completed_reading,
    make_user_with_limits,
)

pytestmark = pytest.mark.xfail(
    reason="PATCH /api/me/settings pending 05-03 (profile settings slice)",
    strict=False,
)


async def _user_with_bearer(session: AsyncSession) -> tuple[User, dict[str, str]]:
    """A fresh user (with quota) + an ``Authorization`` header carrying a Bearer minted for it."""
    user = await make_user_with_limits(session)
    token = encode_jwt(sub=str(user.id), telegram_id=user.telegram_id)
    return user, {"Authorization": f"Bearer {token}"}


async def test_partial_patch_round_trip(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """Invariant #3: PATCH one flag → it flips, the others are untouched, GET /api/me reflects it."""
    user, auth = await _user_with_bearer(auth_session)
    # Baseline defaults (User model): reversals_enabled=True, allow_history_personalization=False,
    # onboarding_completed=False.
    assert user.reversals_enabled is True
    assert user.allow_history_personalization is False
    assert user.onboarding_completed is False

    # PATCH only allow_history_personalization.
    resp = await auth_client.patch(
        "/api/me/settings",
        json={"allow_history_personalization": True},
        headers=auth,
    )
    assert resp.status_code == 200, resp.text

    # GET /api/me reflects the single change; the other two flags are unchanged.
    me = await auth_client.get("/api/me", headers=auth)
    assert me.status_code == 200, me.text
    settings = me.json()["settings"]
    assert settings["allow_history_personalization"] is True
    assert settings["reversals_enabled"] is True  # untouched
    assert settings["onboarding_completed"] is False  # untouched


async def test_patch_user_from_jwt_not_body(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """T-05-SPOOF/V4: a forged ``user_id`` in the body is ignored — only the JWT user mutates."""
    user, auth = await _user_with_bearer(auth_session)
    # A second user who must remain completely untouched by the forged-id PATCH.
    victim = await make_user_with_limits(auth_session)
    assert victim.allow_history_personalization is False

    forged = {
        "allow_history_personalization": True,
        "user_id": str(victim.id),  # forged — must have NO effect
    }
    resp = await auth_client.patch("/api/me/settings", json=forged, headers=auth)
    assert resp.status_code == 200, resp.text

    auth_session.expire_all()
    # The JWT user changed.
    me = (
        await auth_session.execute(select(User).where(User.id == user.id))
    ).scalar_one()
    assert me.allow_history_personalization is True
    # The forged-id victim did NOT change.
    other = (
        await auth_session.execute(select(User).where(User.id == victim.id))
    ).scalar_one()
    assert other.allow_history_personalization is False


async def test_reversals_source(
    auth_client, auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """D-09: after PATCH reversals_enabled=false, a new reading draws upright-only.

    Reversals are sourced from the PERSISTED user flag (not the request body): the user opts out via
    the settings PATCH, and the subsequently created reading's drawn cards are all upright. We assert
    on the persisted ``reading_cards`` orientations (the authoritative, server-side draw state).
    """
    user, auth = await _user_with_bearer(auth_session)

    # User opts OUT of reversals through the settings endpoint.
    resp = await auth_client.patch(
        "/api/me/settings", json={"reversals_enabled": False}, headers=auth
    )
    assert resp.status_code == 200, resp.text
    auth_session.expire_all()
    refreshed = (
        await auth_session.execute(select(User).where(User.id == user.id))
    ).scalar_one()
    assert refreshed.reversals_enabled is False

    # A reading created now sources reversals from the persisted flag → upright-only draw.
    created = await create_completed_reading(
        auth_session, refreshed, reversals_enabled=refreshed.reversals_enabled
    )

    rows = (
        await auth_session.execute(
            select(ReadingCard).where(
                ReadingCard.reading_id == uuid.UUID(created.reading_id)
            )
        )
    ).scalars().all()
    assert rows  # the draw produced cards
    assert all(row.orientation is Orientation.UPRIGHT for row in rows)

    # And the response echoes the persisted upright orientations.
    reading_row = await auth_session.get(Reading, uuid.UUID(created.reading_id))
    assert reading_row is not None
    assert all(card.orientation == "upright" for card in created.cards)
