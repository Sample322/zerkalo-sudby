"""PAY (D-11) bucket-consume (red stubs) — SUBSCRIPTION / PAID gate + correct-bucket refund.

Target plan: **Plan 07-05** (fill the ``SUBSCRIPTION`` / ``PAID`` arms of ``reading.py``'s
``_consume_free_gate`` + ``_refund_*``). This EXTENDS the Phase-6 free-quota gate — it does NOT
duplicate the free tests (``test_paywall_block`` / ``test_determine_access`` cover FREE). The
consume order is **free → subscription → paid** (D-11): expiring buckets are spent before the
permanent ``paid_spreads_balance``. Today ``_consume_free_gate`` returns ``None`` for every
non-FREE bucket (the Phase-7 seam), so these tests ``xfail(strict=False)`` until Plan 05 fills the
arms — they **xpass** the moment the SUBSCRIPTION/PAID consume + the correct-bucket refund exist.

They drive the REAL ``ReadingService.create_reading`` against the ``seeded_catalog`` with the
``FakeSafety`` / ``FakeLLM`` stand-ins (no Anthropic call — the established Phase-4/5/6 seam),
mirroring ``test_paywall_block``. The free bucket is deliberately EXHAUSTED (``free_used == limit``,
fresh window) so the gate must fall through to the sub/paid bucket under test. DB-touching, so they
clean-skip without Postgres (via ``seeded_catalog`` → ``auth_session`` → ``_db_ready``).
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
    _spread_position_indices,
)

_REQ = ReadingCreate(
    question="Что мне поможет принять важное решение на этой неделе?",
    topic="choice",
    deck_slug="classic_arcana",
    spread_slug="three_keys",
)


async def _make_user_with_buckets(
    session: AsyncSession,
    *,
    free_used: int = 3,
    free_limit: int = 3,
    week_start: datetime | None = None,
    subscription_limit: int = 0,
    subscription_used: int = 0,
    paid_balance: int = 0,
) -> User:
    """Insert a user + ``user_limits`` with the FREE bucket exhausted and the sub/paid buckets set.

    The free bucket is exhausted in a FRESH window (``week_start=now``, ``free_used==free_limit``)
    so ``determine_access`` cannot return FREE and the gate must fall through to the sub/paid bucket
    the test populates.
    """
    user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
    session.add(user)
    await session.flush()
    session.add(
        UserLimits(
            user_id=user.id,
            free_weekly_limit=free_limit,
            free_used_this_week=free_used,
            week_start=week_start if week_start is not None else datetime.now(UTC),
            subscription_spreads_limit=subscription_limit,
            subscription_spreads_used=subscription_used,
            paid_spreads_balance=paid_balance,
        )
    )
    await session.flush()
    return user


async def _limits(session: AsyncSession, user: User) -> UserLimits:
    return (
        await session.execute(select(UserLimits).where(UserLimits.user_id == user.id))
    ).scalar_one()


# ---------------------------------------------------------------------------------------
# SUBSCRIPTION bucket — consumed when an active subscription window has units left.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=False, reason="Plan 07-05 fills the SUBSCRIPTION arm of _consume_free_gate"
)
async def test_subscription_bucket_consumed_when_active(
    auth_session: AsyncSession, fake_safety: FakeSafety, seeded_catalog: dict
) -> None:
    """Free exhausted + an active subscription window → SUBSCRIPTION is chosen and consumed (D-11).

    ``determine_access`` already routes to ``Bucket.SUBSCRIPTION`` here (free exhausted,
    ``subscription_spreads_limit > used``); Plan 05 makes ``_consume_free_gate`` actually consume
    from it. A successful reading must complete and increment ``subscription_spreads_used`` by one
    while NOT touching the free counter (the free → subscription order, D-11).
    """
    from app.services.reading import Bucket, ReadingService, determine_access

    user = await _make_user_with_buckets(
        auth_session, free_used=3, subscription_limit=10, subscription_used=0
    )
    # Sanity: the pure policy already selects SUBSCRIPTION (the seam exists; the consume does not).
    assert determine_access(await _limits(auth_session, user)) is Bucket.SUBSCRIPTION

    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    service = ReadingService(safety=fake_safety, llm=FakeLLM(_output_for_indices(indices)))
    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.COMPLETED.value  # NOT a paywall — the sub bucket paid
    limits = await _limits(auth_session, user)
    assert limits.subscription_spreads_used == 1  # consumed from the subscription bucket
    assert limits.free_used_this_week == 3  # free untouched (was already exhausted)


# ---------------------------------------------------------------------------------------
# PAID bucket — consumed when there is no free and no subscription.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=False, reason="Plan 07-05 fills the PAID arm of _consume_free_gate"
)
async def test_paid_bucket_consumed_when_no_free_no_sub(
    auth_session: AsyncSession, fake_safety: FakeSafety, seeded_catalog: dict
) -> None:
    """No free + no subscription + a paid balance → PAID is chosen and decremented (D-11).

    With the free bucket exhausted and no subscription units, ``determine_access`` returns
    ``Bucket.PAID``; Plan 05 makes the gate decrement ``paid_spreads_balance`` by one on a
    successful reading. The permanent paid balance is spent LAST (after free + subscription).
    """
    from app.services.reading import Bucket, ReadingService, determine_access

    user = await _make_user_with_buckets(
        auth_session, free_used=3, subscription_limit=0, paid_balance=2
    )
    assert determine_access(await _limits(auth_session, user)) is Bucket.PAID

    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    service = ReadingService(safety=fake_safety, llm=FakeLLM(_output_for_indices(indices)))
    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.COMPLETED.value
    limits = await _limits(auth_session, user)
    assert limits.paid_spreads_balance == 1  # 2 → 1, one paid spread consumed
    assert limits.free_used_this_week == 3  # free untouched


# ---------------------------------------------------------------------------------------
# Correct-bucket refund — an honest fail refunds the bucket that was consumed, not free.
# ---------------------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=False, reason="Plan 07-05 refunds the consumed sub/paid bucket on honest fail"
)
async def test_honest_fail_refunds_correct_bucket(
    auth_session: AsyncSession, fake_safety: FakeSafety, seeded_catalog: dict
) -> None:
    """An honest LLM fail after a PAID consume refunds the PAID bucket (READ-10 / Pitfall 2, D-11).

    Because the gate consumes the bucket BEFORE the draw (RESEARCH Pattern 1), every non-success
    exit must refund THE SAME bucket so the net counter is unchanged. Here the free bucket is
    exhausted and a paid balance pays for the attempt; an exhausted-retry honest fail must give the
    PAID spread back (NOT refund a free unit — refunding the wrong bucket is the bug this guards).
    """
    from app.services.reading import ReadingService

    user = await _make_user_with_buckets(
        auth_session, free_used=3, subscription_limit=0, paid_balance=2
    )
    # Real LLMService retry contract: invalid on every attempt → exhausts → honest fail.
    llm = LLMService(client=_AlwaysInvalidClient())
    service = ReadingService(safety=fake_safety, llm=llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert result.status == ReadingStatus.FAILED.value
    limits = await _limits(auth_session, user)
    # Net unchanged on the PAID bucket — the consumed spread was refunded (not a free unit).
    assert limits.paid_spreads_balance == 2
    assert limits.free_used_this_week == 3  # free was never touched (so nothing to refund there)
