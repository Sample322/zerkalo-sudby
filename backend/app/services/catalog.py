"""Catalog service (thick) — decks, spreads, and the topic-aware recommendation.

Mirrors the Phase 1 service-layer split (thin router -> thick service). All queries are
SQLAlchemy 2.0 ``select()``, parameterized (PG ARRAY ``.any()`` for topic membership —
never f-string SQL). Spreads always eager-load their positions via ``selectinload`` so the
router can serialize ``SpreadOut`` without a lazy-load greenlet error.

``recommend_spread`` implements the deterministic resolution order (SPREAD-04):
  1. deck given -> spreads compatible with that deck whose recommended_topics include the
     topic, ranked is_recommended DESC, compatibility_score DESC, sort_order ASC;
  2. else -> any active spread whose recommended_topics include the topic, by sort_order;
  3. else -> the constant fallback ``DEFAULT_SPREAD_SLUG`` ("three_keys").
The ``reason`` string is in-character RU and never mentions AI/нейросеть/модель (brand voice).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Deck, DeckSpreadCompatibility, SpreadType

DEFAULT_SPREAD_SLUG = "three_keys"

# RU labels for topic slugs (TZ §27.1) — used to build human, in-character reasons.
_TOPIC_LABELS: dict[str, str] = {
    "love": "любовь",
    "work": "работа",
    "money": "деньги",
    "choice": "выбор",
    "day": "день",
    "self_reflection": "саморефлексия",
    "general": "общий вопрос",
}


def _topic_label(topic: str) -> str:
    return _TOPIC_LABELS.get(topic, topic)


def _build_reason(topic: str, deck: Deck | None) -> str:
    """Pure, DB-free reason builder (testable in isolation).

    In-character RU copy. MUST NOT contain AI/нейросеть/модель/сгенерирован (brand voice).
    """
    label = _topic_label(topic)
    if deck is not None and deck.atmosphere:
        return (
            f"Для темы «{label}» колода «{deck.title}» звучит в атмосфере "
            f"{deck.atmosphere} — этот расклад раскрывает её особенно бережно."
        )
    if deck is not None:
        return (
            f"Для темы «{label}» колода «{deck.title}» ложится в этот расклад "
            f"яснее всего."
        )
    return f"Для темы «{label}» этот расклад открывает вопрос мягко и по существу."


async def list_decks(session: AsyncSession) -> list[Deck]:
    """All active decks, ordered for the carousel (DECK-01/03)."""
    result = await session.execute(
        select(Deck).where(Deck.is_active.is_(True)).order_by(Deck.sort_order)
    )
    return list(result.scalars().all())


async def get_deck(session: AsyncSession, slug: str) -> Deck | None:
    """One active deck by slug, or None (router maps None -> 404) (DECK-03)."""
    result = await session.execute(
        select(Deck).where(Deck.slug == slug, Deck.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def list_spreads(
    session: AsyncSession,
    *,
    topic: str | None = None,
    deck_slug: str | None = None,
) -> list[SpreadType]:
    """Active spreads with nested positions; optional topic / deck filters (SPREAD-01/02/03)."""
    stmt = (
        select(SpreadType)
        .where(SpreadType.is_active.is_(True))
        .options(selectinload(SpreadType.positions))
        .order_by(SpreadType.sort_order)
    )
    if topic:
        stmt = stmt.where(SpreadType.recommended_topics.any(topic))
    if deck_slug:
        compat_subq = (
            select(DeckSpreadCompatibility.spread_type_id)
            .join(Deck, Deck.id == DeckSpreadCompatibility.deck_id)
            .where(Deck.slug == deck_slug)
        )
        stmt = stmt.where(SpreadType.id.in_(compat_subq))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _fallback_spread(session: AsyncSession) -> SpreadType | None:
    result = await session.execute(
        select(SpreadType)
        .where(SpreadType.slug == DEFAULT_SPREAD_SLUG)
        .options(selectinload(SpreadType.positions))
    )
    return result.scalar_one_or_none()


async def recommend_spread(
    session: AsyncSession,
    *,
    topic: str,
    deck_slug: str | None = None,
) -> tuple[SpreadType | None, str]:
    """Pick one recommended spread for (topic[, deck]) + a human reason (SPREAD-04)."""
    deck: Deck | None = None
    spread: SpreadType | None = None

    if deck_slug:
        deck = await get_deck(session, deck_slug)
        stmt = (
            select(SpreadType)
            .join(
                DeckSpreadCompatibility,
                DeckSpreadCompatibility.spread_type_id == SpreadType.id,
            )
            .join(Deck, Deck.id == DeckSpreadCompatibility.deck_id)
            .where(
                Deck.slug == deck_slug,
                SpreadType.is_active.is_(True),
                SpreadType.recommended_topics.any(topic),
            )
            .order_by(
                DeckSpreadCompatibility.is_recommended.desc(),
                DeckSpreadCompatibility.compatibility_score.desc(),
                SpreadType.sort_order,
            )
            .options(selectinload(SpreadType.positions))
        )
        spread = (await session.execute(stmt)).scalars().first()

    if spread is None:
        stmt = (
            select(SpreadType)
            .where(
                SpreadType.is_active.is_(True),
                SpreadType.recommended_topics.any(topic),
            )
            .order_by(SpreadType.sort_order)
            .options(selectinload(SpreadType.positions))
        )
        spread = (await session.execute(stmt)).scalars().first()

    if spread is None:
        spread = await _fallback_spread(session)

    return spread, _build_reason(topic, deck)


__all__ = [
    "DEFAULT_SPREAD_SLUG",
    "list_decks",
    "get_deck",
    "list_spreads",
    "recommend_spread",
]
