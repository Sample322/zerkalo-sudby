"""``cards`` model (TZ §13.3) — the UNIVERSAL card meaning, deck-agnostic.

ARCHITECTURE boundary rule: ``cards`` holds the canonical name + keywords + meaning/advice
that are true regardless of deck. It carries **no imagery** — every image_url / visual lives
in ``deck_cards`` (the style layer). ``arcana_type`` / ``suit`` are native PG ENUMs; ``suit``
is NULL for the 22 major arcana.
"""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ArcanaType, Suit, arcana_type_enum, suit_enum


class Card(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cards"

    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    arcana_type: Mapped[ArcanaType] = mapped_column(arcana_type_enum)
    suit: Mapped[Suit | None] = mapped_column(suit_enum, nullable=True)
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String)
    title_en: Mapped[str | None] = mapped_column(String, nullable=True)

    keywords_upright: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    keywords_reversed: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    meaning_upright: Mapped[str] = mapped_column(String)
    meaning_reversed: Mapped[str] = mapped_column(String)
    advice_upright: Mapped[str] = mapped_column(String)
    advice_reversed: Mapped[str] = mapped_column(String)


__all__ = ["Card"]
