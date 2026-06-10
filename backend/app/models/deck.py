"""Deck aggregate: ``decks`` (§13.2), ``deck_cards`` (§13.4), ``deck_spread_compatibility``
(§13.7).

- ``decks``: the catalog entry — atmosphere/tone/visual_style/prompt_modifier drive the
  "same question, different deck" core value. ``access_type`` is a native ENUM.
- ``deck_cards``: the STYLE layer — imagery + deck-specific modifiers for a (deck, card)
  pair. It carries **no base meaning** (that lives in ``cards``) per the ARCHITECTURE rule.
- ``deck_spread_compatibility``: which spreads a deck recommends.

FK columns are indexed so later catalog joins stay cheap (RESEARCH Open Question #3).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AccessType, access_type_enum


class Deck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "decks"

    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    subtitle: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    atmosphere: Mapped[str | None] = mapped_column(String, nullable=True)
    tone: Mapped[str | None] = mapped_column(String, nullable=True)
    visual_style: Mapped[dict] = mapped_column(JSONB, default=dict)
    prompt_modifier: Mapped[str | None] = mapped_column(String, nullable=True)
    recommended_topics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    is_mvp: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    access_type: Mapped[AccessType] = mapped_column(
        access_type_enum, default=AccessType.FREE, server_default=AccessType.FREE.value
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DeckCard(UUIDPrimaryKeyMixin, Base):
    """Style layer for a (deck, card) pair — imagery + deck-specific modifiers only."""

    __tablename__ = "deck_cards"

    deck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decks.id", ondelete="CASCADE"), index=True
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), index=True
    )
    image_url: Mapped[str] = mapped_column(String)
    thumbnail_url: Mapped[str] = mapped_column(String)
    back_image_url: Mapped[str | None] = mapped_column(String, nullable=True)
    visual_prompt: Mapped[str | None] = mapped_column(String, nullable=True)
    deck_specific_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    deck_specific_upright_modifier: Mapped[str | None] = mapped_column(String, nullable=True)
    deck_specific_reversed_modifier: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DeckSpreadCompatibility(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "deck_spread_compatibility"

    deck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decks.id", ondelete="CASCADE"), index=True
    )
    spread_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spread_types.id", ondelete="CASCADE"), index=True
    )
    compatibility_score: Mapped[int] = mapped_column(Integer, default=0)
    is_recommended: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    custom_note: Mapped[str | None] = mapped_column(String, nullable=True)


__all__ = ["Deck", "DeckCard", "DeckSpreadCompatibility"]
