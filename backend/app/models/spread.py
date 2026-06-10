"""Spread aggregate: ``spread_types`` (§13.5) + ``spread_positions`` (§13.6).

A spread type defines the shape (card_count) and recommended topics; each position carries
the ``prompt_instruction`` that tells the interpreter how to read the card in that slot
(e.g. "central energy of the question, no past/future"). ``access_type`` is the shared
native ENUM (same PG type as decks).
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin
from app.models.enums import AccessType, access_type_enum


class SpreadType(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "spread_types"

    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    card_count: Mapped[int] = mapped_column(Integer)
    recommended_topics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    access_type: Mapped[AccessType] = mapped_column(
        access_type_enum, default=AccessType.FREE, server_default=AccessType.FREE.value
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class SpreadPosition(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "spread_positions"

    spread_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("spread_types.id", ondelete="CASCADE"), index=True
    )
    position_index: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    prompt_instruction: Mapped[str | None] = mapped_column(String, nullable=True)


__all__ = ["SpreadType", "SpreadPosition"]
