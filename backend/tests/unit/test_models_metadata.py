"""Unit (DB-free) assertions on the declarative metadata (INFRA-02, Task 1).

These run without Postgres: they inspect ``Base.metadata`` directly so the 17-table
schema contract (16 TZ §13 tables + the ``topics`` lookup) and the key
uniques / native ENUMs are locked at import time. The live ``alembic upgrade head``
round-trip lives in ``tests/integration/test_migration.py``.
"""

from __future__ import annotations

from sqlalchemy import Enum as SAEnum

from app.models import Base

EXPECTED_TABLES = frozenset(
    {
        "topics",
        "users",
        "decks",
        "cards",
        "deck_cards",
        "spread_types",
        "spread_positions",
        "deck_spread_compatibility",
        "readings",
        "reading_cards",
        "prompt_templates",
        "user_limits",
        "products",
        "payments",
        "subscriptions",
        "app_events",
        "generation_logs",
    }
)


def test_metadata_has_exactly_17_tables() -> None:
    """16 TZ §13 tables + the topics lookup table — no more, no fewer."""
    actual = set(Base.metadata.tables.keys())
    assert actual == set(EXPECTED_TABLES), {
        "missing": EXPECTED_TABLES - actual,
        "unexpected": actual - EXPECTED_TABLES,
    }
    assert len(Base.metadata.tables) == 17


def _column(table_name: str, column_name: str):
    return Base.metadata.tables[table_name].columns[column_name]


def test_key_unique_constraints_declared() -> None:
    """telegram_id, payments.payload, and every catalog slug are UNIQUE.

    EXCEPT ``prompt_templates`` (Phase 8, ADMIN-05): its ``slug`` is intentionally NON-unique so
    versions coexist — uniqueness is ``(slug, version)``, plus a partial-unique index that enforces
    at most one active row per slug (the safety valve the engine's ``_active_template`` relies on).
    """
    assert _column("users", "telegram_id").unique is True
    assert _column("payments", "payload").unique is True
    for table in ("decks", "cards", "spread_types", "products", "topics"):
        assert _column(table, "slug").unique is True, table

    prompt = Base.metadata.tables["prompt_templates"]
    assert _column("prompt_templates", "slug").unique is not True  # non-unique: versions coexist
    unique_constraint_cols = {
        tuple(col.name for col in con.columns)
        for con in prompt.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    }
    assert ("slug", "version") in unique_constraint_cols
    assert "uq_prompt_active_per_slug" in {ix.name for ix in prompt.indexes}


def test_native_enums_present() -> None:
    """Fixed status/type sets are native PG ENUMs with the documented names."""
    expected = {
        ("cards", "arcana_type", "card_arcana_type"),
        ("cards", "suit", "card_suit"),
        ("decks", "access_type", "access_type"),
        ("spread_types", "access_type", "access_type"),
        ("readings", "status", "reading_status"),
        ("reading_cards", "orientation", "card_orientation"),
        ("prompt_templates", "type", "prompt_template_type"),
        ("products", "product_type", "product_type"),
        ("payments", "status", "payment_status"),
        ("subscriptions", "status", "subscription_status"),
    }
    for table, column, enum_name in expected:
        col_type = _column(table, column).type
        assert isinstance(col_type, SAEnum), f"{table}.{column} is not a native ENUM"
        assert col_type.name == enum_name, f"{table}.{column} enum name={col_type.name!r}"


def test_cards_deck_cards_boundary() -> None:
    """cards holds universal meaning only; deck_cards holds imagery/style only."""
    cards = set(Base.metadata.tables["cards"].columns.keys())
    deck_cards = set(Base.metadata.tables["deck_cards"].columns.keys())
    # cards must NOT carry imagery
    assert {"image_url", "thumbnail_url", "back_image_url"}.isdisjoint(cards)
    # deck_cards must NOT carry base meaning
    assert {"meaning_upright", "meaning_reversed"}.isdisjoint(deck_cards)
