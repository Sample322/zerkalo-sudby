"""user_limits rolling-window foundation

Revision ID: 0002_user_limits_rolling_window
Revises: 0001_initial_schema
Create Date: 2026-06-15

Phase-6 schema foundation for the per-user **rolling 7-day** free limit (D-01) and the
race-safe row-ensure at auth (D-02). Two changes, both reversible:

1. ``user_limits.week_start`` ``DATE`` -> ``TIMESTAMP(timezone=True)`` (A1 / Pitfall 1).
   D-01 anchors the window at the *timestamp* of the first reading and resets when
   ``now - week_start >= 7 days``; a ``DATE`` truncates the time-of-day and makes the reset
   day-granular (the D-04 countdown could not compute hours). The ``postgresql_using`` cast
   turns any pre-existing ISO-Monday ``DATE`` value into a midnight ``timestamptz`` cleanly —
   no row is NULLed or errored; a stale legacy anchor simply self-heals on the first lazy
   reset (RESEARCH Runtime State Inventory). No data backfill is required.

2. A **UNIQUE** constraint on ``user_limits.user_id`` (A2). The relationship is logically 1:1
   with ``users``; the auth row-ensure (Task 2) switches to ``INSERT ... ON CONFLICT
   (user_id) DO NOTHING``, which requires a unique target (the existing
   ``ix_user_limits_user_id`` is a plain, non-unique index). This also structurally prevents
   a double-login from ever creating two rows (threat T-06-01).

HAND-WRITTEN (not ``--autogenerate``) — the build environment has no live database; authored
directly from ``Base.metadata`` and kept fully reversible. ``downgrade`` reverses the two
changes in the opposite order (drop the constraint, then cast the column back to ``DATE``).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_user_limits_rolling_window"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. week_start DATE -> TIMESTAMP(timezone=True). The cast makes existing ISO-Monday
    #    DATE values become midnight timestamptz (self-heals on the first lazy reset, A1).
    op.alter_column(
        "user_limits",
        "week_start",
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.Date(),
        existing_nullable=True,
        postgresql_using="week_start::timestamptz",
    )
    # 2. UNIQUE(user_id) — the ON CONFLICT target for the race-safe row-ensure (A2 / Task 2).
    op.create_unique_constraint(
        "uq_user_limits_user_id", "user_limits", ["user_id"]
    )


def downgrade() -> None:
    # Reverse order: drop the unique constraint, then cast the column back to DATE.
    op.drop_constraint("uq_user_limits_user_id", "user_limits", type_="unique")
    op.alter_column(
        "user_limits",
        "week_start",
        type_=sa.Date(),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=True,
        postgresql_using="week_start::date",
    )
