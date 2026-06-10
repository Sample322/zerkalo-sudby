"""``topics`` lookup table (orchestrator directive 1 — NOT in TZ §13).

A lightweight catalog so the admin panel / UI can resolve a topic *slug* to a human
title and ordering. It is a **lookup only**: it is NOT a foreign-key target. Readings keep
``topic`` as a free TEXT slug and decks/spreads keep ``recommended_topics`` as ``TEXT[]``
(RESEARCH Pitfall 5 — stay consistent with the TEXT/TEXT[] columns either way).
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class Topic(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "topics"

    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


__all__ = ["Topic"]
