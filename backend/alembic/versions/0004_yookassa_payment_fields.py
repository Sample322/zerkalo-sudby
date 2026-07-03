"""ЮKassa payment fields — provider pivot Stars→ЮKassa (D-01/D-02/D-06/D-08)

Revision ID: 0004_yookassa_payment_fields
Revises: 0003_reading_answer_style
Create Date: 2026-06-29

Additive, reversible migration carrying the ЮKassa (YooKassa) v3 surface onto the existing
``payments`` + ``subscriptions`` tables. No data migration — no real payments exist yet
(PAY-* all Pending), so this only adds columns, flips two server-defaults for NEW rows, and
relaxes one NOT NULL.

``payments`` — adds the provider-agnostic ЮKassa id (UNIQUE — the exactly-once grant backstop,
T-07-REPLAY), the hosted-page ``confirmation_url``, the per-attempt ``idempotence_key`` and a
saved ``payment_method_id``; flips ``provider`` ``telegram_stars``→``yookassa`` and ``currency``
``XTR``→``RUB`` (D-02, NEW rows only).
``subscriptions`` — adds the saved ``payment_method_id`` + renewal bookkeeping
(``provider_payment_id``/``last_charge_at``/``period_index``) and makes
``telegram_payment_charge_id`` NULLABLE so a ЮKassa subscription insert (no Telegram charge id)
is legal (D-08).

HAND-WRITTEN (not ``--autogenerate``) — the build environment has no live database; authored
directly from ``Base.metadata`` and kept fully reversible (style: ``0003_reading_answer_style.py``).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_yookassa_payment_fields"
down_revision: str | None = "0003_reading_answer_style"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- payments: ЮKassa columns (all nullable — additive) ---
    op.add_column(
        "payments", sa.Column("provider_payment_id", sa.String(), nullable=True)
    )
    op.add_column("payments", sa.Column("confirmation_url", sa.String(), nullable=True))
    op.add_column("payments", sa.Column("idempotence_key", sa.String(), nullable=True))
    op.add_column("payments", sa.Column("payment_method_id", sa.String(), nullable=True))
    # UNIQUE index on the ЮKassa payment id — the exactly-once grant backstop (T-07-REPLAY).
    op.create_index(
        "ix_payments_provider_payment_id",
        "payments",
        ["provider_payment_id"],
        unique=True,
    )
    # D-02: flip the server-defaults for NEW rows (existing rows keep their stored values).
    op.alter_column("payments", "provider", server_default="yookassa")
    op.alter_column("payments", "currency", server_default="RUB")

    # --- subscriptions: saved-method + renewal bookkeeping ---
    op.add_column(
        "subscriptions", sa.Column("payment_method_id", sa.String(), nullable=True)
    )
    op.add_column(
        "subscriptions", sa.Column("provider_payment_id", sa.String(), nullable=True)
    )
    op.add_column(
        "subscriptions",
        sa.Column("last_charge_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "subscriptions",
        sa.Column(
            "period_index",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    # D-08: a ЮKassa subscription has no Telegram charge id → drop the NOT NULL.
    op.alter_column(
        "subscriptions",
        "telegram_payment_charge_id",
        existing_type=sa.String(),
        nullable=True,
    )
    # Phase-7 subscription-window timestamps must be tz-AWARE: the grant + recurring renewal write
    # ``datetime.now(UTC)`` and the consume-gate compares ``current_period_end`` to a tz-aware
    # ``now`` — asyncpg refuses to mix naive/aware (the bug the recurring path hit). 0001 created
    # these as ``DateTime`` (naive); convert in place (``last_charge_at`` was already added tz-aware
    # above). ``USING ... AT TIME ZONE 'UTC'`` interprets any existing naive value as UTC (there are
    # no live subscription rows yet — additive-only phase).
    for _col in ("started_at", "current_period_start", "current_period_end", "canceled_at"):
        op.alter_column(
            "subscriptions",
            _col,
            existing_type=sa.DateTime(),
            type_=sa.TIMESTAMP(timezone=True),
            postgresql_using=f"{_col} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    # --- subscriptions: reverse the tz-aware conversion (back to naive DateTime) ---
    for _col in ("canceled_at", "current_period_end", "current_period_start", "started_at"):
        op.alter_column(
            "subscriptions",
            _col,
            existing_type=sa.TIMESTAMP(timezone=True),
            type_=sa.DateTime(),
            postgresql_using=f"{_col} AT TIME ZONE 'UTC'",
        )
    # --- subscriptions: reverse (restore NOT NULL, drop the added columns) ---
    op.alter_column(
        "subscriptions",
        "telegram_payment_charge_id",
        existing_type=sa.String(),
        nullable=False,
    )
    op.drop_column("subscriptions", "period_index")
    op.drop_column("subscriptions", "last_charge_at")
    op.drop_column("subscriptions", "provider_payment_id")
    op.drop_column("subscriptions", "payment_method_id")

    # --- payments: reverse (restore the Stars-era server-defaults, drop index + columns) ---
    op.alter_column("payments", "currency", server_default="XTR")
    op.alter_column("payments", "provider", server_default="telegram_stars")
    op.drop_index("ix_payments_provider_payment_id", table_name="payments")
    op.drop_column("payments", "payment_method_id")
    op.drop_column("payments", "idempotence_key")
    op.drop_column("payments", "confirmation_url")
    op.drop_column("payments", "provider_payment_id")
