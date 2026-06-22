"""reading.answer_style — record the chosen answer style (Ясный / Бережный / Таинственный)

Revision ID: 0003_reading_answer_style
Revises: 0002_user_limits_rolling_window
Create Date: 2026-06-22

Adds a nullable ``readings.answer_style`` column recording which answer style the user chose for
each reading (an MVP preference knob + the source for the admin stats' style distribution). Old
rows stay NULL ("unknown" — they predate the feature). Fully reversible.

HAND-WRITTEN (not ``--autogenerate``) — the build environment has no live database; authored
directly from ``Base.metadata`` and kept reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_reading_answer_style"
down_revision: str | None = "0002_user_limits_rolling_window"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("readings", sa.Column("answer_style", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("readings", "answer_style")
