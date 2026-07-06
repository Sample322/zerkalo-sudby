"""Idempotent seed loader — upsert MVP catalog content by slug in FK-safe order.

INFRA-03. Loads the JSON files under ``app/seed/data/`` and writes them with
PostgreSQL ``INSERT ... ON CONFLICT (slug) DO UPDATE`` so re-running ``run_seed``
produces identical row counts with no duplicate-key error (T-03-01 mitigation).

FK-safe order (RESEARCH Pattern 6): ``topics`` -> ``decks`` -> ``cards`` ->
``spread_types`` -> ``spread_positions`` -> ``prompt_templates`` ->
``deck_spread_compatibility``. Phase 2 (SPREAD-04) closes the seed gap: the
``deck_spread_compatibility`` rows are derived from REFERENCE-TZ §7 (per-deck recommended
spread lists in ``compatibility.json``) and seeded AFTER decks + spreads exist, because
each row needs both their ids.

``spread_positions`` and ``deck_spread_compatibility`` have no natural single-column
unique key, so each is made idempotent with a scoped delete-then-insert inside the same
transaction (``spread_positions`` keyed by ``spread_type_id``; compatibility keyed by
``deck_id``); the outer caller commits once.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Card,
    Deck,
    DeckCard,
    DeckSpreadCompatibility,
    Product,
    PromptTemplate,
    SpreadPosition,
    SpreadType,
    Topic,
)

DATA_DIR = Path(__file__).parent / "data"


def _load(name: str) -> list[dict[str, Any]]:
    """Read one seed JSON file from ``data/`` and return its list of row dicts."""
    path = DATA_DIR / name
    with path.open(encoding="utf-8") as fh:
        rows = json.load(fh)
    if not isinstance(rows, list):  # pragma: no cover - guards a malformed file
        raise ValueError(f"seed file {name} must contain a JSON array")
    return rows


async def upsert_by_slug(session: AsyncSession, model: type, rows: list[dict[str, Any]]) -> None:
    """Upsert ``rows`` into ``model`` keyed on the unique ``slug`` column.

    Uses ``ON CONFLICT (slug) DO UPDATE`` so an existing row is refreshed in place
    rather than duplicated — the idempotency guarantee. Every non-``slug`` column in
    the row is overwritten on conflict.
    """
    if not rows:  # pragma: no cover - all seed files are non-empty
        return
    for row in rows:
        stmt = pg_insert(model).values(**row)
        update_cols = {k: v for k, v in row.items() if k != "slug"}
        stmt = stmt.on_conflict_do_update(index_elements=["slug"], set_=update_cols)
        await session.execute(stmt)


async def _upsert_prompts(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """Upsert ``prompt_templates`` keyed on the composite ``(slug, version)``.

    Phase 8 (ADMIN-05) made versions coexist per slug, so the conflict key is
    ``uq_prompt_templates_slug_version`` — NOT ``slug`` alone (which is no longer unique). Re-seeding
    on a redeploy refreshes the *seeded* version row in place and never clobbers an operator-created
    newer version: a different ``version`` under the same slug is a different row and survives
    untouched. Seed rows keep whatever ``is_active`` the JSON declares (the seeded baseline stays
    active unless an operator has since activated another version).
    """
    if not rows:  # pragma: no cover - prompts.json is non-empty
        return
    for row in rows:
        stmt = pg_insert(PromptTemplate).values(**row)
        update_cols = {k: v for k, v in row.items() if k not in ("slug", "version")}
        stmt = stmt.on_conflict_do_update(index_elements=["slug", "version"], set_=update_cols)
        await session.execute(stmt)


async def _upsert_spreads(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """Upsert spread_types by slug, then seed each spread's positions once.

    ``spread_positions`` is authored content, immutable after the first seed. A
    delete-then-reinsert would crash a re-seed once real readings exist: ``reading_cards``
    FK-references ``spread_positions`` (``reading_cards_position_id_fkey``), so deleting a
    referenced position raises ForeignKeyViolationError. We therefore insert a spread's
    positions ONLY when it has none yet — idempotent, and never touching a row a reading
    depends on.
    """
    for spread in rows:
        positions = spread.get("positions", [])
        type_row = {k: v for k, v in spread.items() if k != "positions"}

        stmt = pg_insert(SpreadType).values(**type_row)
        update_cols = {k: v for k, v in type_row.items() if k != "slug"}
        stmt = stmt.on_conflict_do_update(index_elements=["slug"], set_=update_cols)
        await session.execute(stmt)

        spread_type_id = await session.scalar(
            select(SpreadType.id).where(SpreadType.slug == spread["slug"])
        )

        # Insert positions only when this spread has none (immutable; never delete referenced rows).
        has_positions = await session.scalar(
            select(SpreadPosition.id)
            .where(SpreadPosition.spread_type_id == spread_type_id)
            .limit(1)
        )
        if has_positions is None:
            for position in positions:
                await session.execute(
                    pg_insert(SpreadPosition).values(spread_type_id=spread_type_id, **position)
                )


async def _upsert_compatibility(
    session: AsyncSession, rows: list[dict[str, Any]]
) -> int:
    """Derive + upsert ``deck_spread_compatibility`` from REFERENCE-TZ §7 (SPREAD-04).

    ``rows`` is ``compatibility.json``: one object per deck with the deck slug and its
    recommended spread slugs (transcribed from §7). For each deck we resolve the deck row +
    each spread row, then rebuild the deck's compatibility rows with a scoped
    delete-then-insert (keyed by ``deck_id`` — there is no single-column unique key),
    mirroring the ``spread_positions`` idempotency pattern.

    Every spread listed under a deck in §7 is a *recommended* spread, so each inserted row
    gets ``is_recommended=True``. ``compatibility_score`` is the size of the topic overlap
    between the deck's and the spread's ``recommended_topics`` (orchestrator directive 3 /
    RESEARCH derivation rule) — a deterministic, re-derivable signal the recommender ranks on.

    Returns the total number of compatibility rows written.
    """
    written = 0
    for row in rows:
        deck = (
            await session.execute(
                select(Deck).where(Deck.slug == row["deck_slug"])
            )
        ).scalar_one_or_none()
        if deck is None:  # pragma: no cover - guards a malformed compatibility.json
            raise ValueError(f"compatibility references unknown deck '{row['deck_slug']}'")

        deck_topics = set(deck.recommended_topics or [])

        # Rebuild THIS deck's compatibility rows only (scoped delete -> insert).
        await session.execute(
            delete(DeckSpreadCompatibility).where(
                DeckSpreadCompatibility.deck_id == deck.id
            )
        )
        for spread_slug in row.get("recommended_spread_slugs", []):
            spread = (
                await session.execute(
                    select(SpreadType).where(SpreadType.slug == spread_slug)
                )
            ).scalar_one_or_none()
            if spread is None:  # pragma: no cover - guards a malformed compatibility.json
                raise ValueError(
                    f"compatibility references unknown spread '{spread_slug}'"
                )

            spread_topics = set(spread.recommended_topics or [])
            score = len(deck_topics & spread_topics)
            await session.execute(
                pg_insert(DeckSpreadCompatibility).values(
                    deck_id=deck.id,
                    spread_type_id=spread.id,
                    compatibility_score=score,
                    is_recommended=True,
                )
            )
            written += 1
    return written


async def _seed_deck_cards(session: AsyncSession) -> int:
    """Populate ``deck_cards`` — the per-deck card pool the reading draw selects from.

    One row per (deck, card): 6 decks x 78 cards = 468. Idempotent WITHOUT a single-column
    unique key — existing ``(deck_id, card_id)`` pairs are skipped, missing ones inserted.
    Imagery is a deferred content task (TZ §5), so ``image_url`` / ``thumbnail_url`` are seeded
    empty: the frontend renders the CSS/SVG card-art fallback until real art is uploaded via the
    admin panel. WITHOUT these rows the card draw raises "deck ... has 0 active cards".
    """
    deck_ids = (await session.execute(select(Deck.id))).scalars().all()
    card_ids = (await session.execute(select(Card.id))).scalars().all()
    existing = {
        (deck_id, card_id)
        for deck_id, card_id in (
            await session.execute(select(DeckCard.deck_id, DeckCard.card_id))
        ).all()
    }
    rows = [
        {
            "deck_id": deck_id,
            "card_id": card_id,
            "image_url": "",
            "thumbnail_url": "",
            "is_active": True,
        }
        for deck_id in deck_ids
        for card_id in card_ids
        if (deck_id, card_id) not in existing
    ]
    if rows:
        await session.execute(pg_insert(DeckCard), rows)
    return len(existing) + len(rows)


async def run_seed(session: AsyncSession) -> dict[str, int]:
    """Load and upsert all MVP seed content in FK-safe order.

    Idempotent: safe to run repeatedly. Does NOT commit — the caller owns the
    transaction boundary (``app/seed/__main__.py`` commits once). Returns a mapping
    of table -> rows seeded for logging / assertions.
    """
    topics = _load("topics.json")
    decks = _load("decks.json")
    spreads = _load("spreads.json")
    cards = _load("cards.json")
    prompts = _load("prompts.json")
    compatibility = _load("compatibility.json")
    # Purchasable catalog (Phase 7, D-15): packs + subscription. No FK deps → upsert by slug
    # alongside the other top-level catalog tables; RUB prices live in ``stars_price`` (A1).
    products = _load("products.json")

    await upsert_by_slug(session, Topic, topics)
    await upsert_by_slug(session, Deck, decks)
    await upsert_by_slug(session, Card, cards)
    await _upsert_spreads(session, spreads)
    await _upsert_prompts(session, prompts)  # keyed on (slug, version) — versions coexist (ADMIN-05)
    await upsert_by_slug(session, Product, products)
    # Compatibility needs deck + spread ids, so it runs AFTER both are upserted.
    compat_count = await _upsert_compatibility(session, compatibility)
    # deck_cards is the per-deck draw pool — needs deck + card ids, so it runs last.
    deck_card_count = await _seed_deck_cards(session)

    return {
        "topics": len(topics),
        "decks": len(decks),
        "spread_types": len(spreads),
        "spread_positions": sum(len(s.get("positions", [])) for s in spreads),
        "cards": len(cards),
        "deck_cards": deck_card_count,
        "prompt_templates": len(prompts),
        "deck_spread_compatibility": compat_count,
        "products": len(products),
    }


__all__ = ["run_seed", "upsert_by_slug", "DATA_DIR"]
