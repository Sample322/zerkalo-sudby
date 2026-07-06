"""``prompt_templates`` model (TZ §13.10).

The versioned prompt fragments the interpreter composes (system / single_card /
final_summary / deck_modifier / safety / refusal — native ENUM). Multiple *versions* of one
logical template COEXIST — addressed by ``slug`` (the stable key the engine + seed use) but
``slug`` is NOT unique; ``(slug, version)`` is. At most ONE row per slug is ``is_active`` — the
production safety valve (Phase 8, ADMIN-05): publishing/activating a version flips ``is_active`` so
a bad version can be rolled back without a redeploy. ``PromptEngine._active_template`` resolves the
single active row per slug; the partial-unique index below is what makes that ``scalar_one_or_none``
correct.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PromptTemplateType, prompt_template_type_enum


class PromptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_templates"
    __table_args__ = (
        # Versions coexist per slug → (slug, version) is the unique key the seed loader upserts on
        # (ON CONFLICT (slug, version)); slug alone is a plain lookup index (declared on the column).
        UniqueConstraint("slug", "version", name="uq_prompt_templates_slug_version"),
        # Safety-valve invariant: at most ONE active row per slug. This partial-unique index is
        # exactly what _active_template's `slug == :s AND is_active` → scalar_one_or_none relies on;
        # activation/rollback flips is_active and the index guarantees a single winner (race-safe).
        Index(
            "uq_prompt_active_per_slug",
            "slug",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    slug: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    type: Mapped[PromptTemplateType] = mapped_column(prompt_template_type_enum)
    template_text: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


__all__ = ["PromptTemplate"]
