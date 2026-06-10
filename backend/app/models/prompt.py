"""``prompt_templates`` model (TZ §13.10).

The versioned prompt fragments the interpreter composes (system / single_card /
final_summary / deck_modifier / safety / refusal — native ENUM). ``slug`` is UNIQUE so the
admin panel and the seed loader address templates by a stable key.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import PromptTemplateType, prompt_template_type_enum


class PromptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prompt_templates"

    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    type: Mapped[PromptTemplateType] = mapped_column(prompt_template_type_enum)
    template_text: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


__all__ = ["PromptTemplate"]
