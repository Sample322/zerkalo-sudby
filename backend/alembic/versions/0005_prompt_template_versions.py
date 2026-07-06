"""prompt_templates versioning — multi-version + partial-unique active (Phase 8, ADMIN-05)

Revision ID: 0005_prompt_template_versions
Revises: 0004_yookassa_payment_fields
Create Date: 2026-07-07

The production safety valve for generation. Lets multiple versions of one logical prompt template
coexist (addressed by ``slug``) with at most ONE active per slug, so a bad version can be rolled
back via the admin API WITHOUT a redeploy.

Swaps the uniqueness on ``prompt_templates``: drops the single-column UNIQUE on ``slug`` (both the
0001 table constraint ``prompt_templates_slug_key`` AND the unique index ``ix_prompt_templates_slug``)
and replaces it with UNIQUE ``(slug, version)`` + a partial-unique index (at most one ``is_active``
row per slug) + a plain non-unique lookup index on ``slug``. Existing prod data (one row per slug,
all active) already satisfies the ≤1-active invariant, so NO data migration is needed.

The single-column drops use ``IF EXISTS`` because a metadata-built database (tests:
``Base.metadata.create_all``) never had the redundant 0001 table constraint — only the migrated
prod database does. HAND-WRITTEN (no live DB in the build env); fully reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_prompt_template_versions"
down_revision: str | None = "0004_yookassa_payment_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the single-column slug uniqueness (0001's table constraint + its unique index). IF EXISTS
    # so this is safe whether the schema came from migrations (prod: has both) or from
    # Base.metadata.create_all (tests: only ever had the unique index, never the extra constraint).
    op.execute("ALTER TABLE prompt_templates DROP CONSTRAINT IF EXISTS prompt_templates_slug_key")
    op.execute("DROP INDEX IF EXISTS ix_prompt_templates_slug")

    # Plain non-unique lookup index on slug (engine + admin filter by slug).
    op.create_index("ix_prompt_templates_slug", "prompt_templates", ["slug"], unique=False)

    # Versions coexist: (slug, version) is the new unique key (the seed loader upserts on it).
    op.create_unique_constraint(
        "uq_prompt_templates_slug_version", "prompt_templates", ["slug", "version"]
    )

    # Safety-valve invariant: at most one active row per slug (partial-unique index). This is exactly
    # what PromptEngine._active_template's `slug == :s AND is_active` scalar_one_or_none relies on.
    op.create_index(
        "uq_prompt_active_per_slug",
        "prompt_templates",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )


def downgrade() -> None:
    # Reverse: drop the versioning objects, restore the single-column slug uniqueness (index +
    # constraint, matching 0001). NOTE: if an operator created extra versions per slug while at
    # head, this downgrade will fail the UNIQUE(slug) restore — expected for an emergency reversal.
    op.drop_index("uq_prompt_active_per_slug", table_name="prompt_templates")
    op.drop_constraint("uq_prompt_templates_slug_version", "prompt_templates", type_="unique")
    op.drop_index("ix_prompt_templates_slug", table_name="prompt_templates")
    op.create_index("ix_prompt_templates_slug", "prompt_templates", ["slug"], unique=True)
    op.create_unique_constraint("prompt_templates_slug_key", "prompt_templates", ["slug"])
