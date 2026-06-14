"""Shared Phase-5 integration helpers — create a COMPLETED reading without re-driving the POST.

This module is the Wave-0 substrate the history/profile slice tests (list / detail / delete /
settings) build on. It is deliberately **not** ``test_``-prefixed so pytest does not collect it as
a test module — it only exports helpers.

WHY a high ``free_weekly_limit`` knob (``make_user_with_limits``):
    The last-10-cap test (``test_readings_list.test_last_ten_cap``, HIST-06) needs ≥12 COMPLETED
    readings for ONE user so it can assert the list returns exactly 10 while the older rows stay
    fetchable by id. Each ``create_completed_reading`` call runs the real ``ReadingService`` keystone,
    which consumes one free unit on success (Phase-4 quota gate). With the default 3/week limit the
    4th call would hit the soft paywall and persist a FAILED row instead of a COMPLETED one — so the
    cap test seeds the user with a high ``free_weekly_limit`` (default 100) to stay inside quota.

Single source of truth (no re-declaration):
    * the fakes — ``FakeLLM`` / ``FakeSafety`` — come from ``tests.integration.conftest``;
    * the matched fake output + the seeded position indices — ``_output_for_indices`` /
      ``_spread_position_indices`` — come from ``tests.integration.test_readings_flow``.
    These helpers wire those together so a caller gets a real, persisted COMPLETED reading
    (``readings`` + immutable ``reading_cards``) through the genuine orchestration seam, with NO
    Anthropic call (fakes injected) and NO inline duplication of the flow.

Everything runs inside the caller's transaction-isolated ``auth_session`` (the savepoint fixture),
so nothing persists between tests, and the integration suite still skips cleanly when Postgres is
down (the fixtures that provide the session + seeded catalog are the ones that skip).
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserLimits
from app.schemas.reading import ReadingCreate, ReadingOut
from app.services.reading import ReadingService
from tests.integration.conftest import FakeLLM, FakeSafety
from tests.integration.test_readings_flow import (
    _output_for_indices,
    _spread_position_indices,
)

# Defaults that match the seeded MVP catalog (a real active deck + a real 3-card spread + a real
# topic slug) so ``ReadingService`` resolves them and the draw has a genuine pool.
DEFAULT_DECK_SLUG = "classic_arcana"
DEFAULT_SPREAD_SLUG = "three_keys"
DEFAULT_TOPIC = "choice"
DEFAULT_QUESTION = "Что мне поможет принять важное решение на этой неделе?"


async def make_user_with_limits(
    session: AsyncSession,
    *,
    free_weekly_limit: int = 100,
    free_used: int = 0,
) -> User:
    """Insert a fresh ``User`` + a ``user_limits`` row with a (configurably high) weekly limit.

    Mirrors ``test_readings_flow._make_user`` but exposes ``free_weekly_limit`` so a single test can
    create many COMPLETED readings without tripping the Phase-4 quota gate (see the module docstring
    — the last-10-cap test needs ≥12). ``free_used`` seeds the already-consumed counter when a test
    wants to start partway through the quota. 2.0-style inserts only; no lazy loads.
    """
    user = User(telegram_id=int(uuid.uuid4().int % 1_000_000_000))
    session.add(user)
    await session.flush()
    session.add(
        UserLimits(
            user_id=user.id,
            free_weekly_limit=free_weekly_limit,
            free_used_this_week=free_used,
        )
    )
    await session.flush()
    return user


async def create_completed_reading(
    session: AsyncSession,
    user: User,
    *,
    deck_slug: str = DEFAULT_DECK_SLUG,
    spread_slug: str = DEFAULT_SPREAD_SLUG,
    topic: str = DEFAULT_TOPIC,
    question: str = DEFAULT_QUESTION,
    reversals_enabled: bool = True,
) -> ReadingOut:
    """Persist one COMPLETED reading (+ immutable ``reading_cards``) for ``user`` via the real service.

    Builds a fakes-backed ``ReadingService(safety=FakeSafety(), llm=FakeLLM(...))`` whose fake output
    is matched to the seeded spread's actual ``position_index`` values (so the keystone's by-index
    persistence succeeds), runs ``create_reading``, and returns the resulting ``ReadingOut`` (carrying
    ``reading_id``). NO Anthropic call is made. The caller is responsible for having seeded the
    catalog (``seeded_catalog``) and for the user having quota (use ``make_user_with_limits`` when
    creating more than 3). ``reversals_enabled=False`` forces an upright-only draw (the settings
    ``reversals_source`` test relies on this).
    """
    indices = await _spread_position_indices(session, spread_slug)
    service = ReadingService(
        safety=FakeSafety(),
        llm=FakeLLM(_output_for_indices(indices)),
    )
    req = ReadingCreate(
        question=question,
        topic=topic,
        deck_slug=deck_slug,
        spread_slug=spread_slug,
        reversals_enabled=reversals_enabled,
    )
    return await service.create_reading(session, user, req)


__all__ = [
    "DEFAULT_DECK_SLUG",
    "DEFAULT_SPREAD_SLUG",
    "DEFAULT_TOPIC",
    "DEFAULT_QUESTION",
    "make_user_with_limits",
    "create_completed_reading",
]
