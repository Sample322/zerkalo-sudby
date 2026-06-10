"""Analytics / audit aggregate: ``app_events`` (§13.15) + ``generation_logs`` (§13.16).

- ``app_events``: lightweight product analytics. Per TZ §13.15 ``user_id`` is a bare
  ``UUID NULL`` (NOT a foreign key — events may be anonymous and must survive user
  deletion for analytics), indexed for per-user funnels. ``event_properties`` is JSONB.
- ``generation_logs``: the per-reading generation audit trail (model, latency, tokens,
  errors) — threat T-02-03. ``reading_id`` IS a foreign key and is indexed.

Both carry only ``created_at`` per TZ (no ``updated_at``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class AppEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "app_events"

    # Bare UUID (not a FK) per TZ §13.15 — anonymous-capable, survives user deletion.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    event_name: Mapped[str] = mapped_column(String)
    event_properties: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


class GenerationLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "generation_logs"

    reading_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("readings.id", ondelete="CASCADE"), index=True
    )
    prompt_template_version: Mapped[str | None] = mapped_column(String, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String, nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)


__all__ = ["AppEvent", "GenerationLog"]
