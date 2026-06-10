"""Idempotent seed loader — upsert MVP catalog content by slug in FK-safe order.

INFRA-03. Loads the JSON files under ``app/seed/data/`` and writes them with
PostgreSQL ``INSERT ... ON CONFLICT (slug) DO UPDATE`` so re-running ``run_seed``
produces identical row counts with no duplicate-key error (T-03-01 mitigation).

FK-safe order (RESEARCH Pattern 6): ``topics`` -> ``decks`` -> ``cards`` ->
``spread_types`` -> ``spread_positions`` -> ``prompt_templates``. The Phase-1 INFRA-03
counts do NOT require ``deck_cards`` / ``deck_spread_compatibility`` (those are
authored alongside art/compat in Phase 2), so this loader seeds only the rows the
counts depend on.

``spread_positions`` has no natural single-column unique key, so it is made idempotent
per spread with a scoped delete-then-insert inside the same transaction (keyed by
``spread_type_id``); the outer caller commits once.
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


async def _upsert_spreads(session: AsyncSession, rows: list[dict[str, Any]]) -> None:
    """Upsert spread_types by slug, then rebuild each spread's positions idempotently.

    ``spread_positions`` has no single-column unique key, so positions are made
    idempotent by deleting the spread's existing positions and re-inserting the
    authored set (scoped to that ``spread_type_id`` only) inside the same transaction.
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

        # Rebuild positions for THIS spread only (scoped delete -> insert).
        await session.execute(
            delete(SpreadPosition).where(SpreadPosition.spread_type_id == spread_type_id)
        )
        for position in positions:
            await session.execute(
                pg_insert(SpreadPosition).values(spread_type_id=spread_type_id, **position)
            )


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

    await upsert_by_slug(session, Topic, topics)
    await upsert_by_slug(session, Deck, decks)
    await upsert_by_slug(session, Card, cards)
    await _upsert_spreads(session, spreads)
    await upsert_by_slug(session, PromptTemplate, prompts)

    return {
        "topics": len(topics),
        "decks": len(decks),
        "spread_types": len(spreads),
        "spread_positions": sum(len(s.get("positions", [])) for s in spreads),
        "cards": len(cards),
        "prompt_templates": len(prompts),
    }


__all__ = ["run_seed", "upsert_by_slug", "DATA_DIR"]
