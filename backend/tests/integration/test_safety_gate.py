"""SAFE-03 / D-06 — the safety gate runs BEFORE the draw and short-circuits crisis/abusive.

Implemented in Plan 04-05 (ReadingService gate-before-draw ordering). Injects a parametrized
``fake_safety`` (``crisis_sensitive`` / ``abusive_or_manipulative``) + ``fake_llm`` against
``seeded_catalog`` in the transaction-isolated ``auth_session``, driving the service directly.
Asserts:
  * **crisis** → a refusal response (the seeded supportive copy, NOT a mystical prediction —
    D-03/04), with NO card draw, NO generation call, and the limit kept (SAFE-03);
  * **abusive_or_manipulative** → a gentle in-character redirect, NO draw, limit kept (D-06);
  * the gate ran BEFORE ``CardDrawService`` — asserted via ``fake_safety.calls`` incrementing
    while ``fake_llm.calls == 0`` and NO ``reading_cards`` rows were written for the reading.

The seeded refusal/redirect copy must NOT contain a banned brand token (brand voice), and the
crisis copy must not be a templated reading (zero cards).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.brand_guard import contains_banned_brand_token
from app.models import Reading, ReadingCard, UserLimits
from app.models.enums import ReadingStatus
from app.schemas.reading import SafetyCategory
from app.services.reading import ReadingService
from tests.integration.conftest import FakeLLM, FakeSafety
from tests.integration.test_readings_flow import (
    _REQ,
    _make_user,
    _output_for_indices,
    _spread_position_indices,
)


async def _reading_card_count(session: AsyncSession, reading_id: uuid.UUID) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(ReadingCard)
        .where(ReadingCard.reading_id == reading_id)
    )


async def test_crisis_short_circuits_before_draw(
    auth_session: AsyncSession,
    fake_llm: FakeLLM,
    seeded_catalog: dict,
) -> None:
    """SAFE-03/D-03: crisis → refusal, NO draw, NO generation, limit kept; gate ran first."""
    user = await _make_user(auth_session)
    crisis = FakeSafety(category=SafetyCategory.CRISIS_SENSITIVE)
    service = ReadingService(safety=crisis, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    # Gate ran (classify called) BEFORE the draw — and the draw/generation never happened.
    assert crisis.calls == 1
    assert fake_llm.calls == 0

    # Refusal body: failed status, the seeded supportive copy, NOT a templated reading.
    assert result.status == ReadingStatus.FAILED.value
    assert result.reading_id
    assert result.cards == []
    assert result.summary is not None
    refusal = result.summary.soft_advice
    assert refusal  # seeded refusal copy present
    assert not contains_banned_brand_token(refusal)  # brand voice holds

    # A FAILED parent reading exists (so the classify-log FK can hold) with ZERO reading_cards.
    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None
    assert reading.status is ReadingStatus.FAILED
    assert await _reading_card_count(auth_session, reading.id) == 0

    # Limit kept.
    limits = (
        await auth_session.execute(
            select(UserLimits).where(UserLimits.user_id == user.id)
        )
    ).scalar_one()
    assert limits.free_used_this_week == 0


async def test_abusive_redirects_without_draw(
    auth_session: AsyncSession,
    fake_llm: FakeLLM,
    seeded_catalog: dict,
) -> None:
    """D-06: abusive_or_manipulative → gentle redirect, NO draw, limit kept; gate ran first."""
    user = await _make_user(auth_session)
    abusive = FakeSafety(category=SafetyCategory.ABUSIVE_OR_MANIPULATIVE)
    service = ReadingService(safety=abusive, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    assert abusive.calls == 1
    assert fake_llm.calls == 0

    assert result.status == ReadingStatus.FAILED.value
    assert result.cards == []
    assert result.summary is not None
    redirect = result.summary.soft_advice
    assert redirect
    assert not contains_banned_brand_token(redirect)

    reading = await auth_session.get(Reading, uuid.UUID(result.reading_id))
    assert reading is not None
    assert await _reading_card_count(auth_session, reading.id) == 0

    limits = (
        await auth_session.execute(
            select(UserLimits).where(UserLimits.user_id == user.id)
        )
    ).scalar_one()
    assert limits.free_used_this_week == 0


async def test_sensitive_continues_to_generate(
    auth_session: AsyncSession,
    seeded_catalog: dict,
) -> None:
    """D-05/SAFE-02: a *_sensitive question is NOT short-circuited — it draws + generates (softly)."""
    user = await _make_user(auth_session)
    indices = await _spread_position_indices(auth_session, _REQ.spread_slug)
    fake_llm = FakeLLM(_output_for_indices(indices))
    sensitive = FakeSafety(category=SafetyCategory.RELATIONSHIP_SENSITIVE)
    service = ReadingService(safety=sensitive, llm=fake_llm)

    result = await service.create_reading(auth_session, user, _REQ)

    # Sensitive continues to draw + generate (silent softening), unlike crisis/abusive.
    assert sensitive.calls == 1
    assert fake_llm.calls == 1
    assert result.status == ReadingStatus.COMPLETED.value
    assert len(result.cards) == 3
