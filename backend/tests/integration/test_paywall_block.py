"""LIMIT-01 (red stub) — soft paywall on exhaustion + refund-on-failure (D-03 / Pitfall 4).

Two behaviors Plan 06-02 must deliver:
  * **paywall on exhausted** — the 4th reading in a fresh window (used=3/limit=3) returns the soft
    §9.8 body (status=failed) carrying the new machine-readable ``reason`` ("paywall") + a
    ``reset_at`` (week_start + 7d) for the FE countdown, with NO draw and the counter NOT pushed
    past the limit;
  * **refund on honest fail** — because Plan 02 consumes the free slot AS THE GATE (before the
    draw, RESEARCH Pattern 1), every non-success exit after the consume MUST refund so the counter
    is net unchanged (READ-10 / Pitfall 2). An honest LLM exhaustion is the canonical case.

These drive the REAL ``ReadingService.create_reading`` against the seeded catalog. ``xfail(strict=
False)`` until Plan 02 lands; **xpass** once the paywall ``reason``/``reset_at`` + the consume-then-
refund order exist. Skip cleanly without Postgres.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserLimits
from app.models.enums import ReadingStatus
from app.schemas.reading import ReadingCreate
from app.services.llm import LLMService
from tests.integration.conftest import FakeLLM, FakeSafety
from tests.integration.test_readings_flow import (
    _AlwaysInvalidClient,
    _output_for_indices,
)

_REQ = ReadingCreate(
    question="Что мне поможет принять важное решение на этой неделе?",
    topic="choice",
    deck_slug="classic_arcana",
    spread_slug="three_keys",
)


async def _make_user(
    session: AsyncSession, *, free_used: int, week_start: datetime | None
) -> User:
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


async def _used(session: AsyncSession, user: User) -> int:
    limits = (
        await session.execute(select(UserLimits).where(UserLimits.user_id == user.id))
    ).scalar_one()
    return limits.free_used_this_week


@pytest.mark.xfail(strict=False, reason="Plan 06-02 adds the paywall reason + reset_at fields")
async def test_paywall_on_exhausted(
    auth_session: AsyncSession, fake_safety: FakeSafety, seeded_catalog: dict
) -> None:
    """4th reading in a fresh window → soft paywall body with reason='paywall' + reset_at, no draw."""
    now = datetime.now(UTC)
    user = await _make_user(auth_session, free_used=3, week_start=now)
    fake_llm = FakeLLM(_output_for_indices([1, 2, 3]))
    from app.services.reading import ReadingService

    service = ReadingService(safety=fake_safety, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.FAILED.value
    assert fake_llm.calls == 0  # NO draw / NO generation on a paywalled request
    assert await _used(auth_session, user) == 3  # NOT pushed past the limit
    # The new machine-readable discriminator + the per-user reopen moment (D-03/D-04).
    reason = getattr(result, "reason", None)
    assert reason == "paywall"
    assert getattr(result, "reset_at", None) is not None


@pytest.mark.xfail(
    strict=False, reason="Plan 06-02 consumes-as-gate then refunds on non-success (Pitfall 2)"
)
async def test_refund_on_honest_fail(
    auth_session: AsyncSession, fake_safety: FakeSafety, seeded_catalog: dict
) -> None:
    """Consume-as-gate then LLM exhaustion → the slot is refunded, counter net unchanged (READ-10)."""
    now = datetime.now(UTC)
    user = await _make_user(auth_session, free_used=0, week_start=now)
    llm = LLMService(client=_AlwaysInvalidClient())  # exhausts the retry → honest fail
    from app.services.reading import ReadingService

    service = ReadingService(safety=fake_safety, llm=llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.FAILED.value
    # Net unchanged: even though the consume runs as the gate (Pattern 1), the failure refunds it.
    assert await _used(auth_session, user) == 0
