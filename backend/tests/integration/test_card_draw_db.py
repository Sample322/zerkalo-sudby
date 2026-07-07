"""READ-02 (integration) — ``CardDrawService.draw`` over the real seeded catalog.

Exercises the backend-only draw against genuine ``deck_cards`` / ``cards`` / ``spread_positions``
rows (via the shared ``seeded_catalog`` fixture). Skips cleanly when Postgres is unreachable
(``seeded_catalog`` → ``auth_session`` → ``_db_ready``), mirroring the rest of the integration
suite. Asserts the draw selects from the active deck's deck_cards server-side, returns exactly
``card_count`` records (one per position, no card reused), and carries the (card_id, deck_card_id,
position_id, position_index, orientation) + joined universal meaning Plan 05 will persist / prompt.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Deck, SpreadType
from app.models.enums import Orientation
from app.models.spread import SpreadPosition
from app.services.card_draw import CardDrawService, DrawnCard


async def _first_deck_and_spread(
    session: AsyncSession,
) -> tuple[Deck, SpreadType, int]:
    deck = (
        await session.execute(select(Deck).where(Deck.is_active.is_(True)).limit(1))
    ).scalar_one()
    spread = (
        await session.execute(
            select(SpreadType)
            .options(selectinload(SpreadType.positions))  # eager: draw() reads spread.positions
            .where(SpreadType.is_active.is_(True))
            .limit(1)
        )
    ).scalar_one()
    n_positions = len(
        (
            await session.execute(
                select(SpreadPosition).where(
                    SpreadPosition.spread_type_id == spread.id
                )
            )
        )
        .scalars()
        .all()
    )
    return deck, spread, n_positions


async def test_draw_count_and_records_over_seeded_catalog(
    seeded_catalog: dict[str, int],
    auth_session: AsyncSession,
) -> None:
    """Count == positions; each record well-formed; reversals OFF → all upright."""
    deck, spread, n_positions = await _first_deck_and_spread(auth_session)

    records = await CardDrawService.draw(
        auth_session,
        deck_id=deck.id,
        spread=spread,
        reversals_enabled=False,
    )

    assert all(isinstance(r, DrawnCard) for r in records)
    assert len(records) == spread.card_count == n_positions
    # Positions carry the seeded ``spread_positions.position_index`` (1-based, in order); no reuse.
    assert [r.position_index for r in records] == list(range(1, n_positions + 1))
    assert len({r.card_id for r in records}) == n_positions
    for r in records:
        assert r.deck_card_id is not None
        assert r.position_id is not None
        assert r.orientation is Orientation.UPRIGHT  # reversals off → all upright
        # Joined universal meaning the PromptEngine later needs is carried through.
        assert r.card_title
        assert r.meaning_upright
        assert r.meaning_reversed


async def test_draw_reversals_on_orientation_domain(
    seeded_catalog: dict[str, int],
    auth_session: AsyncSession,
) -> None:
    """Reversals ON → orientation domain is exactly {upright, reversed} (CSPRNG coin)."""
    deck, spread, _ = await _first_deck_and_spread(auth_session)

    records = await CardDrawService.draw(
        auth_session,
        deck_id=deck.id,
        spread=spread,
        reversals_enabled=True,
    )

    assert {r.orientation for r in records} <= {
        Orientation.UPRIGHT,
        Orientation.REVERSED,
    }


@pytest.mark.parametrize("reversals", [True, False])
async def test_draw_is_backend_only_ignores_client_cards(
    seeded_catalog: dict[str, int],
    auth_session: AsyncSession,
    reversals: bool,
) -> None:
    """T-04-12: the draw takes only (deck, spread) — there is no seam to inject client cards.

    Every returned ``card_id`` is one of the active deck's own cards (server-side selection),
    so a client cannot forge the hand.
    """
    deck, spread, _ = await _first_deck_and_spread(auth_session)

    from app.models import Card, DeckCard

    active_card_ids = {
        cid
        for (cid,) in (
            await auth_session.execute(
                select(Card.id)
                .join(DeckCard, DeckCard.card_id == Card.id)
                .where(DeckCard.deck_id == deck.id, DeckCard.is_active.is_(True))
            )
        ).all()
    }

    records = await CardDrawService.draw(
        auth_session,
        deck_id=deck.id,
        spread=spread,
        reversals_enabled=reversals,
    )

    assert {r.card_id for r in records} <= active_card_ids
