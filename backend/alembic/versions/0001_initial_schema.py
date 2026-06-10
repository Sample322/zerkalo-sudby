"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-10

The single initial migration for "Зеркало Судьбы" — all 17 tables (the 16 TZ §13
tables + the ``topics`` lookup, orchestrator directive 1), their native PG ENUM types,
UUID primary keys, JSONB / TEXT[] columns, foreign keys, and the UNIQUE constraints
(``users.telegram_id``, ``payments.payload``, every ``slug``) that later phases and the
admin panel depend on.

HAND-WRITTEN (not ``--autogenerate``) because the build environment has no live database;
it is authored directly from ``Base.metadata`` and kept fully reversible. ``downgrade``
drops every table in reverse dependency order and drops the created ENUM types, so
``alembic downgrade base`` returns to an empty schema.

ENUM handling: every ENUM type is created **once, explicitly** at the top of ``upgrade``
and the column definitions reference it with ``create_type=False`` — this keeps the shared
``access_type`` type (used by both ``decks`` and ``spread_types``) from being emitted twice
and makes the ``DROP TYPE`` in ``downgrade`` explicit.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# --- Native ENUM types (created explicitly in upgrade, dropped in downgrade) ----------
# create_type=False: the type is created/dropped by us, not implicitly by create_table.
arcana_type_enum = postgresql.ENUM(
    "major", "minor", name="card_arcana_type", create_type=False
)
suit_enum = postgresql.ENUM(
    "wands", "cups", "swords", "pentacles", name="card_suit", create_type=False
)
access_type_enum = postgresql.ENUM(
    "free",
    "premium",
    "subscription",
    "one_time_purchase",
    "seasonal",
    "limited",
    name="access_type",
    create_type=False,
)
reading_status_enum = postgresql.ENUM(
    "pending",
    "generating",
    "completed",
    "failed",
    "deleted",
    name="reading_status",
    create_type=False,
)
orientation_enum = postgresql.ENUM(
    "upright", "reversed", name="card_orientation", create_type=False
)
prompt_template_type_enum = postgresql.ENUM(
    "system",
    "single_card",
    "final_summary",
    "deck_modifier",
    "safety",
    "refusal",
    name="prompt_template_type",
    create_type=False,
)
product_type_enum = postgresql.ENUM(
    "one_time_spreads", "subscription", name="product_type", create_type=False
)
payment_status_enum = postgresql.ENUM(
    "created",
    "pre_checkout_approved",
    "paid",
    "failed",
    "refunded",
    "canceled",
    name="payment_status",
    create_type=False,
)
subscription_status_enum = postgresql.ENUM(
    "active",
    "canceled",
    "expired",
    "payment_failed",
    name="subscription_status",
    create_type=False,
)

_ALL_ENUMS = (
    arcana_type_enum,
    suit_enum,
    access_type_enum,
    reading_status_enum,
    orientation_enum,
    prompt_template_type_enum,
    product_type_enum,
    payment_status_enum,
    subscription_status_enum,
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Create every ENUM type once, up front.
    for enum_type in _ALL_ENUMS:
        enum_type.create(bind, checkfirst=True)

    # 2) Parent tables (no FK to other domain tables): topics, users, decks, cards,
    #    spread_types, products.
    op.create_table(
        "topics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_topics_slug", "topics", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=True),
        sa.Column("language_code", sa.String(), nullable=True),
        sa.Column("photo_url", sa.String(), nullable=True),
        sa.Column(
            "is_premium_telegram",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "reversals_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "allow_history_personalization",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), server_default=sa.text("'active'"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)

    op.create_table(
        "decks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("subtitle", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("atmosphere", sa.String(), nullable=True),
        sa.Column("tone", sa.String(), nullable=True),
        sa.Column("visual_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("prompt_modifier", sa.String(), nullable=True),
        sa.Column("recommended_topics", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_mvp", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "access_type",
            access_type_enum,
            server_default=sa.text("'free'"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_decks_slug", "decks", ["slug"], unique=True)

    op.create_table(
        "cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("arcana_type", arcana_type_enum, nullable=False),
        sa.Column("suit", suit_enum, nullable=True),
        sa.Column("number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("title_en", sa.String(), nullable=True),
        sa.Column("keywords_upright", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("keywords_reversed", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("meaning_upright", sa.String(), nullable=False),
        sa.Column("meaning_reversed", sa.String(), nullable=False),
        sa.Column("advice_upright", sa.String(), nullable=False),
        sa.Column("advice_reversed", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_cards_slug", "cards", ["slug"], unique=True)

    op.create_table(
        "spread_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("card_count", sa.Integer(), nullable=False),
        sa.Column("recommended_topics", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "access_type",
            access_type_enum,
            server_default=sa.text("'free'"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_spread_types_slug", "spread_types", ["slug"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("product_type", product_type_enum, nullable=False),
        sa.Column("stars_price", sa.Integer(), nullable=False),
        sa.Column("spreads_amount", sa.Integer(), nullable=True),
        sa.Column("subscription_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_products_slug", "products", ["slug"], unique=True)

    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("type", prompt_template_type_enum, nullable=False),
        sa.Column("template_text", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_prompt_templates_slug", "prompt_templates", ["slug"], unique=True)

    # 3) Child tables (FK to the parents above).
    op.create_table(
        "deck_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("thumbnail_url", sa.String(), nullable=False),
        sa.Column("back_image_url", sa.String(), nullable=True),
        sa.Column("visual_prompt", sa.String(), nullable=True),
        sa.Column("deck_specific_keywords", postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column("deck_specific_upright_modifier", sa.String(), nullable=True),
        sa.Column("deck_specific_reversed_modifier", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_deck_cards_deck_id", "deck_cards", ["deck_id"])
    op.create_index("ix_deck_cards_card_id", "deck_cards", ["card_id"])

    op.create_table(
        "spread_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("spread_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("prompt_instruction", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["spread_type_id"], ["spread_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_spread_positions_spread_type_id", "spread_positions", ["spread_type_id"]
    )

    op.create_table(
        "deck_spread_compatibility",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("spread_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("compatibility_score", sa.Integer(), nullable=False),
        sa.Column(
            "is_recommended", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("custom_note", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["spread_type_id"], ["spread_types.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_deck_spread_compatibility_deck_id", "deck_spread_compatibility", ["deck_id"]
    )
    op.create_index(
        "ix_deck_spread_compatibility_spread_type_id",
        "deck_spread_compatibility",
        ["spread_type_id"],
    )

    op.create_table(
        "readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("spread_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            reading_status_enum,
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("reversals_enabled", sa.Boolean(), nullable=False),
        sa.Column("summary_short", sa.String(), nullable=True),
        sa.Column("summary_full", sa.String(), nullable=True),
        sa.Column("main_factor", sa.String(), nullable=True),
        sa.Column("advice", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("generation_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["spread_type_id"], ["spread_types.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_readings_user_id", "readings", ["user_id"])
    op.create_index("ix_readings_deck_id", "readings", ["deck_id"])
    op.create_index("ix_readings_spread_type_id", "readings", ["spread_type_id"])

    op.create_table(
        "reading_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reading_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deck_card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position_index", sa.Integer(), nullable=False),
        sa.Column("orientation", orientation_enum, nullable=False),
        sa.Column("short_meaning", sa.String(), nullable=True),
        sa.Column("interpretation", sa.String(), nullable=True),
        sa.Column("mystical_accent", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deck_card_id"], ["deck_cards.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["position_id"], ["spread_positions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reading_cards_reading_id", "reading_cards", ["reading_id"])
    op.create_index("ix_reading_cards_card_id", "reading_cards", ["card_id"])
    op.create_index("ix_reading_cards_deck_card_id", "reading_cards", ["deck_card_id"])
    op.create_index("ix_reading_cards_position_id", "reading_cards", ["position_id"])

    op.create_table(
        "user_limits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "free_weekly_limit", sa.Integer(), server_default=sa.text("3"), nullable=False
        ),
        sa.Column(
            "free_used_this_week", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("week_start", sa.Date(), nullable=True),
        sa.Column(
            "paid_spreads_balance", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "subscription_spreads_limit",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "subscription_spreads_used",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_limits_user_id", "user_limits", ["user_id"])

    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider",
            sa.String(),
            server_default=sa.text("'telegram_stars'"),
            nullable=False,
        ),
        sa.Column("currency", sa.String(), server_default=sa.text("'XTR'"), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("payload", sa.String(), nullable=False),
        sa.Column("telegram_payment_charge_id", sa.String(), nullable=True),
        sa.Column(
            "status",
            payment_status_enum,
            server_default=sa.text("'created'"),
            nullable=False,
        ),
        sa.Column("raw_update", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("refunded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload"),
    )
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_product_id", "payments", ["product_id"])
    op.create_index(
        "ix_payments_telegram_payment_charge_id",
        "payments",
        ["telegram_payment_charge_id"],
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_payment_charge_id", sa.String(), nullable=False),
        sa.Column(
            "status",
            subscription_status_enum,
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "current_period_start",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("current_period_end", sa.DateTime(), nullable=False),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_product_id", "subscriptions", ["product_id"])

    op.create_table(
        "app_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_name", sa.String(), nullable=False),
        sa.Column("event_properties", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_app_events_user_id", "app_events", ["user_id"])

    op.create_table(
        "generation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reading_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_template_version", sa.String(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generation_logs_reading_id", "generation_logs", ["reading_id"])


def downgrade() -> None:
    bind = op.get_bind()

    # Drop tables in reverse dependency order (children before parents).
    op.drop_index("ix_generation_logs_reading_id", table_name="generation_logs")
    op.drop_table("generation_logs")

    op.drop_index("ix_app_events_user_id", table_name="app_events")
    op.drop_table("app_events")

    op.drop_index("ix_subscriptions_product_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_payments_telegram_payment_charge_id", table_name="payments")
    op.drop_index("ix_payments_product_id", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_table("payments")

    op.drop_index("ix_user_limits_user_id", table_name="user_limits")
    op.drop_table("user_limits")

    op.drop_index("ix_reading_cards_position_id", table_name="reading_cards")
    op.drop_index("ix_reading_cards_deck_card_id", table_name="reading_cards")
    op.drop_index("ix_reading_cards_card_id", table_name="reading_cards")
    op.drop_index("ix_reading_cards_reading_id", table_name="reading_cards")
    op.drop_table("reading_cards")

    op.drop_index("ix_readings_spread_type_id", table_name="readings")
    op.drop_index("ix_readings_deck_id", table_name="readings")
    op.drop_index("ix_readings_user_id", table_name="readings")
    op.drop_table("readings")

    op.drop_index(
        "ix_deck_spread_compatibility_spread_type_id",
        table_name="deck_spread_compatibility",
    )
    op.drop_index(
        "ix_deck_spread_compatibility_deck_id", table_name="deck_spread_compatibility"
    )
    op.drop_table("deck_spread_compatibility")

    op.drop_index("ix_spread_positions_spread_type_id", table_name="spread_positions")
    op.drop_table("spread_positions")

    op.drop_index("ix_deck_cards_card_id", table_name="deck_cards")
    op.drop_index("ix_deck_cards_deck_id", table_name="deck_cards")
    op.drop_table("deck_cards")

    op.drop_index("ix_prompt_templates_slug", table_name="prompt_templates")
    op.drop_table("prompt_templates")

    op.drop_index("ix_products_slug", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_spread_types_slug", table_name="spread_types")
    op.drop_table("spread_types")

    op.drop_index("ix_cards_slug", table_name="cards")
    op.drop_table("cards")

    op.drop_index("ix_decks_slug", table_name="decks")
    op.drop_table("decks")

    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_topics_slug", table_name="topics")
    op.drop_table("topics")

    # Finally drop the ENUM types (after every table that referenced them is gone).
    for enum_type in reversed(_ALL_ENUMS):
        enum_type.drop(bind, checkfirst=True)
