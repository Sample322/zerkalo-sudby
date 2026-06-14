"""HIST-05 — the closed history-personalization gate (load-bearing invariant #4).

This is a NEGATIVE-requirement lock, and it PASSES today (it is intentionally **not** xfail): the
v1 product deliberately has NO history-personalization path, and this test makes that a regression
fence so a future v2 author cannot wire prior-reading content into the prompt silently.

The contract it locks:
  * even with ``user.allow_history_personalization = True`` AND a prior completed reading on record,
    the prompt assembled for a NEW reading contains NONE of the prior reading's question / summary
    text — the gate is "closed by absence" (there is no history channel into ``PromptEngine.build``);
  * ``PromptEngine.build`` exposes NO ``history`` / ``history_context`` parameter (asserted by
    signature introspection) — the absence of the seam is the guarantee.

It builds a real prompt via ``PromptEngine.build`` over the seeded catalog + a real CSPRNG draw (no
Anthropic — prompt assembly is pure once the rows are loaded), so it skips cleanly without Postgres
(``seeded_catalog`` → ``auth_session`` → ``_db_ready``).
"""

from __future__ import annotations

import inspect
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Deck, Reading, SpreadType
from app.services.card_draw import CardDrawService
from app.services.prompt_engine import PromptEngine
from tests.integration._history_helpers import (
    DEFAULT_DECK_SLUG,
    DEFAULT_SPREAD_SLUG,
    create_completed_reading,
    make_user_with_limits,
)

# A distinctive sentinel embedded in the PRIOR reading's question. If any history leaked into the
# new prompt, this exact phrase (or the prior summary text) would appear in the assembled strings.
_PRIOR_SENTINEL = "ПРЕДЫДУЩИЙ_РАСКЛАД_СЕКРЕТНАЯ_МЕТКА_О_СТАРОЙ_РАБОТЕ"
_PRIOR_QUESTION = f"Что говорит {_PRIOR_SENTINEL} про моё решение уйти с прежней работы?"
# The new reading's own, unrelated question.
_NEW_QUESTION = "Что мне поможет принять важное решение на этой неделе?"


def test_build_has_no_history_parameter() -> None:
    """HIST-05: ``PromptEngine.build`` exposes no history channel (signature introspection).

    No DB needed — this asserts the *seam* does not exist, which is what keeps history out by
    construction. A future author adding a ``history`` kwarg trips this immediately.
    """
    params = set(inspect.signature(PromptEngine.build).parameters)
    assert "history" not in params
    assert "history_context" not in params
    assert "prior_readings" not in params


async def test_prompt_has_no_history_even_with_flag_on(
    auth_session: AsyncSession, seeded_catalog: dict
) -> None:
    """HIST-05 / invariant #4: flag ON + a prior reading → the new prompt carries no prior content."""
    # A user who has OPTED IN to history personalization and already has one reading on record.
    user = await make_user_with_limits(auth_session)
    user.allow_history_personalization = True
    await auth_session.flush()
    prior = await create_completed_reading(
        auth_session, user, question=_PRIOR_QUESTION
    )
    assert prior.reading_id

    # Assemble the prompt for a NEW reading exactly as ReadingService does: resolve the active
    # deck/spread, run the real draw, then PromptEngine.build.
    deck = (
        await auth_session.execute(
            select(Deck).where(Deck.slug == DEFAULT_DECK_SLUG, Deck.is_active.is_(True))
        )
    ).scalar_one()
    spread = (
        await auth_session.execute(
            select(SpreadType)
            .where(SpreadType.slug == DEFAULT_SPREAD_SLUG, SpreadType.is_active.is_(True))
            .options(selectinload(SpreadType.positions))
        )
    ).scalar_one()
    draw_records = await CardDrawService.draw(
        auth_session, deck_id=deck.id, spread=spread, reversals_enabled=True
    )

    bundle = await PromptEngine().build(
        auth_session,
        deck=deck,
        spread=spread,
        draw_records=draw_records,
        question=_NEW_QUESTION,
        topic="choice",
    )

    assembled = f"{bundle.system}\n{bundle.user}"
    # The prior reading's distinctive question text must NOT appear anywhere in the new prompt.
    assert _PRIOR_SENTINEL not in assembled
    assert _PRIOR_QUESTION not in assembled

    # The prior reading's persisted summary text must NOT appear either (no summary_full leak).
    prior_row = await auth_session.get(Reading, uuid.UUID(prior.reading_id))
    assert prior_row is not None
    if prior_row.summary_full:
        # The prior summary JSON (or its short form) must not have been spliced into the new prompt.
        assert prior_row.summary_full not in assembled
    if prior_row.summary_short:
        assert prior_row.summary_short not in assembled

    # Sanity: the NEW question IS present (the prompt was actually built for this reading).
    assert _NEW_QUESTION in assembled
