"""LIMIT-02 (red stub) — lazy rolling-7-day reset folded into the atomic consume (D-01).

Plan 06-02 folds the reset into the conditional ``UPDATE`` (RESEARCH Pattern 2): on a reading
request, if ``now - week_start >= 7d`` (stale) the counter resets to 1 and ``week_start``
re-anchors to ``now``; within the window an exhausted user stays blocked (the reset does NOT fire
early); a brand-new user (``week_start IS NULL``, D-02) anchors on this first reading. These drive
the REAL ``ReadingService.create_reading`` consume path against the seeded catalog.

``xfail(strict=False)`` until Plan 02 lands (today the Phase-4 service has no reset, so a stale or
NULL window does NOT reset → the assertions fail); they **xpass** once the fold is implemented.
Skip cleanly without Postgres (via ``seeded_catalog`` → ``auth_session`` → ``_db_ready``).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserLimits
from app.models.enums import ReadingStatus
from app.schemas.reading import ReadingCreate
from tests.integration.conftest import FakeLLM, FakeSafety
from tests.integration.test_readings_flow import (
    _output_for_indices,
    _spread_position_indices,
)

_REQ = ReadingCreate(
    question="Что мне поможет принять важное решение на этой неделе?",
    topic="choice",
    deck_slug="classic_arcana",
    spread_slug="three_keys",
)

_WINDOW = timedelta(days=7)


async def _make_user_with_window(
    session: AsyncSession, *, free_used: int, week_start: datetime | None
) -> User:
    """Insert a user + a ``user_limits`` row with an explicit ``week_start`` anchor and counter."""
    user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
    session.add(user)
    await session.flush()
    session.add(
        UserLimits(
            user_id=user.id,
            free_weekly_limit=3,
            free_used_this_week=free_used,
            week_start=week_start,
        )
    )
    await session.flush()
    return user


async def _limits(session: AsyncSession, user: User) -> UserLimits:
    return (
        await session.execute(select(UserLimits).where(UserLimits.user_id == user.id))
    ).scalar_one()


async def _service(session: AsyncSession) -> object:
    indices = await _spread_position_indices(session, _REQ.spread_slug)
    from app.services.reading import ReadingService

    return ReadingService(safety=FakeSafety(), llm=FakeLLM(_output_for_indices(indices)))


@pytest.mark.xfail(strict=False, reason="Plan 06-02 implements the folded lazy reset")
async def test_reset_on_stale_window(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """A stale window (week_start = now − 7d, used=3) resets: used → 1, week_start re-anchors ≈ now."""
    now = datetime.now(UTC)
    user = await _make_user_with_window(
        auth_session, free_used=3, week_start=now - _WINDOW - timedelta(seconds=1)
    )
    service = await _service(auth_session)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.COMPLETED.value  # the reset gave a fresh slot
    limits = await _limits(auth_session, user)
    assert limits.free_used_this_week == 1  # reset to 0 then this reading counted
    assert limits.week_start is not None
    assert abs((limits.week_start - now).total_seconds()) < 120  # re-anchored ≈ now


@pytest.mark.xfail(strict=False, reason="Plan 06-02 implements the folded lazy reset")
async def test_no_reset_within_window(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """Within the window (week_start = now − 3d, used=3) the reset does NOT fire → still blocked."""
    now = datetime.now(UTC)
    anchor = now - timedelta(days=3)
    user = await _make_user_with_window(auth_session, free_used=3, week_start=anchor)
    service = await _service(auth_session)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.FAILED.value  # soft paywall — no early reset
    limits = await _limits(auth_session, user)
    assert limits.free_used_this_week == 3  # unchanged
    assert limits.week_start == anchor  # window NOT re-anchored


@pytest.mark.xfail(strict=False, reason="Plan 06-02 implements first-reading anchoring (D-02)")
async def test_first_reading_anchors(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """A brand-new user (week_start IS NULL, D-02) anchors on the first reading: used → 1."""
    now = datetime.now(UTC)
    user = await _make_user_with_window(auth_session, free_used=0, week_start=None)
    service = await _service(auth_session)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.COMPLETED.value
    limits = await _limits(auth_session, user)
    assert limits.free_used_this_week == 1
    assert limits.week_start is not None  # anchored on this first reading
    assert abs((limits.week_start - now).total_seconds()) < 120
