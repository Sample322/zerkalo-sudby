"""READ-10 — the limit is consumed exactly once on success, never on any non-success exit.

Implemented in Plan 04-05 (ReadingService limit-consume seam). Injects ``fake_llm`` /
``fake_safety`` against ``seeded_catalog`` in the transaction-isolated ``auth_session`` and drives
the service directly. Asserts:
  * a successful reading decrements ``free_used_this_week`` exactly once;
  * every non-success exit (no quota, crisis short-circuit, abusive redirect, honest fail)
    leaves the counter unchanged (READ-10 / D-09 / Pitfall 4).

Phase 4 only needs "consumed on success, not on failure" — weekly reset/buckets/atomic decrement
are Phase 6 (RESEARCH Deferred Ideas), out of scope here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserLimits
from app.models.enums import ReadingStatus
from app.schemas.reading import SafetyCategory
from app.services.llm import LLMService
from app.services.reading import ReadingService
from tests.integration.conftest import FakeLLM, FakeSafety
from tests.integration.test_readings_flow import (
    _REQ,
    _AlwaysInvalidClient,
    _make_user,
    _output_for_indices,
    _spread_position_indices,
)


async def _make_fresh_exhausted(session: AsyncSession) -> User:
    """A user with a FRESH window (week_start=now) fully spent (used=3/limit=3).

    Distinct from the imported ``_make_user`` (which leaves ``week_start`` NULL): a real ``reset_at``
    on the paywall body requires an anchored window, so this seeds ``week_start=now`` — the only
    state where the paywall carries a non-None reopen moment for the FE countdown (D-04).
    """
    user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
    session.add(user)
    await session.flush()
    session.add(
        UserLimits(
            user_id=user.id,
            free_weekly_limit=3,
            free_used_this_week=3,
            week_start=datetime.now(UTC),
        )
    )
    await session.flush()
    return user


async def _used(session: AsyncSession, user: User) -> int:
    limits = (
        await session.execute(select(UserLimits).where(UserLimits.user_id == user.id))
    ).scalar_one()
    return limits.free_used_this_week


async def test_limit_consumed_once_on_success(
    auth_session: AsyncSession,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """READ-10: a completed reading consumes exactly one unit."""
    user = await _make_user(auth_session)
    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    fake_llm = FakeLLM(_output_for_indices(indices))
    service = ReadingService(safety=fake_safety, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.COMPLETED.value
    assert await _used(auth_session, user) == 1


async def test_limit_untouched_on_no_quota(
    auth_session: AsyncSession,
    fake_llm: FakeLLM,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """READ-10: a user with no remaining quota gets a soft paywall and the counter is unchanged."""
    user = await _make_user(auth_session, free_used=3)  # 3/3 used → no quota
    service = ReadingService(safety=fake_safety, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.FAILED.value  # soft paywall body
    assert fake_llm.calls == 0  # no generation attempted
    assert await _used(auth_session, user) == 3  # unchanged


async def test_limit_untouched_on_crisis(
    auth_session: AsyncSession,
    fake_llm: FakeLLM,
    seeded_catalog: dict,
) -> None:
    """READ-10/D-03: a crisis short-circuit keeps the limit (no draw, no charge)."""
    user = await _make_user(auth_session)
    crisis = FakeSafety(category=SafetyCategory.CRISIS_SENSITIVE)
    service = ReadingService(safety=crisis, llm=fake_llm)

    await service.create_reading(auth_session, user, _REQ)

    assert fake_llm.calls == 0
    assert await _used(auth_session, user) == 0


async def test_limit_untouched_on_abusive(
    auth_session: AsyncSession,
    fake_llm: FakeLLM,
    seeded_catalog: dict,
) -> None:
    """READ-10/D-06: an abusive redirect keeps the limit (no draw, no charge)."""
    user = await _make_user(auth_session)
    abusive = FakeSafety(category=SafetyCategory.ABUSIVE_OR_MANIPULATIVE)
    service = ReadingService(safety=abusive, llm=fake_llm)

    await service.create_reading(auth_session, user, _REQ)

    assert fake_llm.calls == 0
    assert await _used(auth_session, user) == 0


async def test_limit_untouched_on_honest_fail(
    auth_session: AsyncSession,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """READ-10/D-09: an honest fail (generation exhausted) keeps the limit — retry is free."""
    user = await _make_user(auth_session)
    llm = LLMService(client=_AlwaysInvalidClient())
    service = ReadingService(safety=fake_safety, llm=llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.FAILED.value
    assert await _used(auth_session, user) == 0


async def test_paywall_carries_reset_at(
    auth_session: AsyncSession,
    fake_llm: FakeLLM,
    fake_safety: FakeSafety,
    seeded_catalog: dict,
) -> None:
    """LIMIT-01/D-04: an exhausted FRESH window → paywall body with reason='paywall' + reset_at.

    The consume-gate returns None (within a fresh window, used==limit), so the soft body carries the
    machine-readable ``reason`` discriminant (Plan 04's FE branches on it) and the per-user
    ``reset_at`` (week_start + 7d) for the countdown — with NO draw and the counter NOT pushed past
    the limit (consume-as-gate never matched a row).
    """
    user = await _make_fresh_exhausted(auth_session)
    service = ReadingService(safety=fake_safety, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.FAILED.value
    assert fake_llm.calls == 0  # no draw / no generation on a paywalled request
    assert await _used(auth_session, user) == 3  # never past the limit
    assert result.reason == "paywall"
    assert result.reset_at is not None  # week_start + 7d, the FE countdown anchor (D-04)
