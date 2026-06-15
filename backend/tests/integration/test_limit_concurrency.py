"""LIMIT-03 (red stub) — the boundary-race atomicity proof (success-criterion 3).

THE load-bearing test of Phase 6. Two concurrent ``create_reading`` calls for the SAME user at
the limit boundary (``free_used=2``, ``free_weekly_limit=3``) must resolve to **exactly one
completed + one paywall**, and the counter must end at the limit (3), NEVER ``limit+1`` (4).

This CANNOT use the savepoint-shared ``auth_session`` (research Pitfall 3): two coroutines on one
connection cannot demonstrate a cross-connection PostgreSQL row lock. It uses the committed
substrate (``committed_seeded_catalog`` + ``two_committed_sessions``) so each ``attempt()`` runs on
its OWN real connection and ``commit``s — the only shape that exercises the lock.

Plan 06-02 implements the atomic conditional ``UPDATE … WHERE free_used < limit … RETURNING``
(RESEARCH Pattern 1) that makes this pass; until then it is ``xfail(strict=False)`` and **xpasses**
once the atomicity lands. It skips cleanly without Postgres (via ``committed_seeded_catalog`` →
``_db_ready``).

MUTATION TEST (prove the test is load-bearing, not vacuous — Pitfall 3 warning sign):
    Temporarily replace the atomic ``UPDATE … WHERE free_used_this_week < free_weekly_limit``
    in ``ReadingService`` with a non-atomic read-check-then-write (read used, ``if used < limit``,
    then ``UPDATE … SET used = used + 1``). Re-run this test WITH Postgres up: it MUST then
    observe ``used == 4`` (both racers read used=2, both pass the Python check, both write) and go
    red. A concurrency test that cannot observe that failure is not proving anything.
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.models import User, UserLimits
from app.schemas.reading import ReadingCreate

# A normal, schema-valid request against the seeded three-card spread (mirrors test_readings_flow).
_REQ = ReadingCreate(
    question="Что мне поможет принять важное решение на этой неделе?",
    topic="choice",
    deck_slug="classic_arcana",
    spread_slug="three_keys",
)


@pytest.mark.xfail(
    strict=False, reason="Plan 06-02 implements the atomic consume that serializes the race"
)
async def test_two_concurrent_at_boundary_only_one_succeeds(
    committed_seeded_catalog: dict,
    two_committed_sessions: object,
) -> None:
    """At used=2/limit=3, two concurrent creates → one completed, one paywall; counter == 3, never 4."""
    from datetime import UTC, datetime

    from tests.integration.conftest import FakeLLM, FakeSafety
    from tests.integration.test_readings_flow import (
        _output_for_indices,
        _spread_position_indices,
    )

    make = two_committed_sessions
    now = datetime.now(UTC)

    # Arrange: a COMMITTED user at the boundary (free_used=2, limit=3, fresh window anchored now),
    # so both independent connections see it. Capture the spread's real position indices so the
    # FakeLLM output echoes the actual draw.
    async with make() as setup:
        user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
        setup.add(user)
        await setup.flush()
        setup.add(
            UserLimits(
                user_id=user.id,
                free_weekly_limit=3,
                free_used_this_week=2,
                week_start=now,
            )
        )
        indices = await _spread_position_indices(setup, _REQ.spread_slug)
        await setup.commit()
    output = _output_for_indices(indices)

    async def attempt() -> str:
        async with make() as s:  # independent connection — real cross-connection lock
            from app.services.reading import ReadingService

            svc = ReadingService(safety=FakeSafety(), llm=FakeLLM(output))
            result = await svc.create_reading(s, user, _REQ)
            return result.status

    s1, s2 = await asyncio.gather(attempt(), attempt())

    # Exactly one completed + one paywall (order-independent).
    assert sorted([s1, s2]) == ["completed", "failed"]

    # The atomicity proof: the counter is EXACTLY the limit, never limit+1.
    async with make() as check:
        used = (
            await check.execute(
                select(UserLimits.free_used_this_week).where(UserLimits.user_id == user.id)
            )
        ).scalar_one()
    assert used == 3  # NOT 4

    # Teardown: remove the committed user + its limits row (the catalog fixture cleans the rest).
    async with make() as teardown:
        await teardown.execute(
            UserLimits.__table__.delete().where(UserLimits.user_id == user.id)
        )
        await teardown.execute(User.__table__.delete().where(User.id == user.id))
        await teardown.commit()
