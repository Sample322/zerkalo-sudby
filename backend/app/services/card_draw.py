"""``CardDrawService`` — the backend-only, cryptographically-secure card draw (READ-02).

The draw is **entirely server-side** (§12.4 / §29.2, T-04-12): the client never supplies or
forges the drawn cards or the reversals state. The service selects from the *active* deck's
``deck_cards`` (the style layer that pins which (deck, card) rows exist), joins ``cards`` for
the universal meaning the prompt later needs, shuffles with a CSPRNG, and assigns the first
``spread.card_count`` cards to the spread's positions in ``position_index`` order.

Randomness (§12.5, D-13, CLAUDE.md anti-pattern, T-04-13):
  * shuffle + orientation coin use ``secrets.SystemRandom`` — a CSPRNG — **never** the plain
    ``random`` module (predictable / seedable → hand prediction);
  * orientation: ``reversals_enabled=False`` → every card upright; ``True`` → each card is
    ``reversed`` with probability ``REVERSED_PROBABILITY`` (0.30), else ``upright`` (70/30).

This service performs **no** ``reading_cards`` INSERT — persistence + the transaction are
``ReadingService``'s job (Plan 05). ``draw`` returns plain, immutable ``DrawnCard`` records
carrying exactly the columns Plan 05 writes into ``reading_cards`` (``card_id`` /
``deck_card_id`` / ``position_id`` / ``position_index`` / ``orientation``) plus the joined
universal ``meaning_*`` / ``keywords_*`` the ``PromptEngine`` consumes.

Per RESEARCH A5 / Open Question 1 there is **no** seed/debug_hash column on ``readings`` — the
immutable ``reading_cards`` rows are the durable record, so this service does not invent one.

Eager-loading (RESEARCH Pitfall 5): the deck-card pool is fetched with an explicit ``select()``
join (no implicit lazy load), so building the records never trips ``MissingGreenlet`` under the
async ASGI server.
"""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, DeckCard, SpreadType
from app.models.enums import Orientation

# CSPRNG — the single secure source for both the shuffle and the orientation coin.
# This is deliberately NOT the stdlib pseudo-random module (predictable / seedable → hand
# prediction; CLAUDE.md "What NOT to Use"; TZ §12.5). The module-level instance is the
# production default; the pure helpers accept an injected rng so the orientation/ratio tests
# can drive a seeded double deterministically.
_rng = secrets.SystemRandom()

# D-13: with reversals enabled, a card lands reversed ~30% of the time, upright ~70%.
REVERSED_PROBABILITY = 0.30


class _RNG(Protocol):
    """The minimal random interface the pure helpers depend on (shuffle + random)."""

    def shuffle(self, x: list[object], /) -> None: ...
    def random(self) -> float: ...


@dataclass(frozen=True)
class DrawnCard:
    """One drawn card — the immutable record ``ReadingService`` (Plan 05) persists + prompts on.

    The first five fields map 1:1 onto the ``reading_cards`` columns Plan 05 writes; the
    remaining fields are the joined *universal* meaning/keywords the ``PromptEngine`` needs (the
    deck-specific style modifiers live on ``deck_cards`` and are looked up separately by the
    prompt). No interpretation text here — that is produced later by the single LLM call.
    """

    card_id: object
    deck_card_id: object
    position_id: object
    position_index: int
    orientation: Orientation
    # Joined universal meaning (from ``cards``) the prompt later needs.
    card_title: str
    meaning_upright: str
    meaning_reversed: str
    keywords_upright: Sequence[str]
    keywords_reversed: Sequence[str]


def _assign_orientations(
    *, count: int, reversals_enabled: bool, rng: _RNG
) -> list[Orientation]:
    """Pure orientation assignment for ``count`` cards (D-13). Deterministic for a seeded rng.

    ``reversals_enabled=False`` → all upright (the rng is not consulted). ``True`` → each card is
    ``REVERSED`` with probability ``REVERSED_PROBABILITY`` (0.30), else ``UPRIGHT`` (70/30).
    """
    if not reversals_enabled:
        return [Orientation.UPRIGHT] * count
    return [
        Orientation.REVERSED if rng.random() < REVERSED_PROBABILITY else Orientation.UPRIGHT
        for _ in range(count)
    ]


class CardDrawService:
    """Backend-only CSPRNG card draw for a (deck, spread) pair."""

    @staticmethod
    async def draw(
        session: AsyncSession,
        *,
        deck_id: object,
        spread: SpreadType,
        reversals_enabled: bool = True,
        rng: _RNG | None = None,
    ) -> list[DrawnCard]:
        """Draw exactly ``spread.card_count`` cards for ``deck_id`` (backend-only, CSPRNG).

        Selects the active ``deck_cards`` for the deck joined to ``cards`` (universal meaning),
        shuffles the pool with the CSPRNG, takes the first ``card_count`` (== number of
        positions), and assigns each to ``spread.positions`` in ``position_index`` order, with a
        70/30 orientation when reversals are enabled. Returns immutable ``DrawnCard`` records;
        writes nothing (persistence is Plan 05). ``rng`` is injectable for deterministic tests
        and defaults to the module CSPRNG.
        """
        active_rng = rng if rng is not None else _rng

        positions = sorted(spread.positions, key=lambda p: p.position_index)
        card_count = spread.card_count
        if card_count != len(positions):
            # Defensive: the spread's declared card_count must match its seeded positions.
            raise ValueError(
                f"spread {spread.slug!r} card_count={card_count} != "
                f"{len(positions)} positions"
            )

        # Eager pool fetch (no lazy load): active (deck_card, card) pairs for this deck.
        rows = (
            await session.execute(
                select(DeckCard, Card)
                .join(Card, Card.id == DeckCard.card_id)
                .where(DeckCard.deck_id == deck_id, DeckCard.is_active.is_(True))
            )
        ).all()

        if len(rows) < card_count:
            raise ValueError(
                f"deck {deck_id!r} has {len(rows)} active cards, need {card_count}"
            )

        pool = list(rows)
        active_rng.shuffle(pool)
        chosen = pool[:card_count]
        orientations = _assign_orientations(
            count=card_count, reversals_enabled=reversals_enabled, rng=active_rng
        )

        return [
            DrawnCard(
                card_id=card.id,
                deck_card_id=deck_card.id,
                position_id=position.id,
                position_index=position.position_index,
                orientation=orientation,
                card_title=card.title,
                meaning_upright=card.meaning_upright,
                meaning_reversed=card.meaning_reversed,
                keywords_upright=tuple(card.keywords_upright or ()),
                keywords_reversed=tuple(card.keywords_reversed or ()),
            )
            for position, (deck_card, card), orientation in zip(
                positions, chosen, orientations, strict=True
            )
        ]


__all__ = [
    "REVERSED_PROBABILITY",
    "CardDrawService",
    "DrawnCard",
]
