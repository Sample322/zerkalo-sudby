"""Reading aggregate: ``readings`` (§13.8) + ``reading_cards`` (§13.9).

- ``readings``: one tarot session — question + topic + chosen deck/spread, the generation
  ``status`` (native ENUM), and the produced summary/advice fields (NULL until completed).
- ``reading_cards``: the drawn cards, **immutable once written** — each row pins the
  universal card, the deck-specific style row, the position, the ``orientation`` (native
  ENUM), and the per-card interpretation text.

TZ §13.8/§13.9 give these ``created_at`` (+ readings ``completed_at``/``deleted_at``) but no
``updated_at`` — so the ``TimestampMixin`` is intentionally not used here. ``readings.user_id``
and ``reading_cards.reading_id`` are indexed (history queries — RESEARCH Open Question #3).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import (
    Orientation,
    ReadingStatus,
    orientation_enum,
    reading_status_enum,
)


class Reading(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "readings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    question: Mapped[str] = mapped_column(String)
    topic: Mapped[str | None] = mapped_column(String, nullable=True)
    deck_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("decks.id", ondelete="RESTRICT"), index=True
    )
    spread_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spread_types.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[ReadingStatus] = mapped_column(
        reading_status_enum,
        default=ReadingStatus.PENDING,
        server_default=ReadingStatus.PENDING.value,
    )
    reversals_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    summary_short: Mapped[str | None] = mapped_column(String, nullable=True)
    summary_full: Mapped[str | None] = mapped_column(String, nullable=True)
    main_factor: Mapped[str | None] = mapped_column(String, nullable=True)
    advice: Mapped[str | None] = mapped_column(String, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String, nullable=True)
    generation_error: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ReadingCard(UUIDPrimaryKeyMixin, Base):
    """Immutable record of a drawn card within a reading."""

    __tablename__ = "reading_cards"

    reading_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("readings.id", ondelete="CASCADE"), index=True
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cards.id", ondelete="RESTRICT"), index=True
    )
    deck_card_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("deck_cards.id", ondelete="RESTRICT"), index=True
    )
    position_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spread_positions.id", ondelete="RESTRICT"), index=True
    )
    position_index: Mapped[int] = mapped_column(Integer)
    orientation: Mapped[Orientation] = mapped_column(orientation_enum)
    short_meaning: Mapped[str | None] = mapped_column(String, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(String, nullable=True)
    mystical_accent: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


__all__ = ["Reading", "ReadingCard"]
