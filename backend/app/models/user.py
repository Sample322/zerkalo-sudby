"""``users`` model (TZ §13.1).

``telegram_id`` is the durable identity key — ``BIGINT UNIQUE NOT NULL`` so the Plan-04
auth upsert (``INSERT ... ON CONFLICT (telegram_id)``) is DB-guaranteed against duplicate
accounts (threat T-02-01). Profile fields mirror the Telegram ``user`` blob; settings flags
back the onboarding / reversals / history-personalization toggles.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    language_code: Mapped[str | None] = mapped_column(String, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    is_premium_telegram: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    reversals_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    allow_history_personalization: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    status: Mapped[str] = mapped_column(String, default="active", server_default="active")

    last_seen_at: Mapped[datetime | None] = mapped_column(
        nullable=True, server_default=func.now()
    )


__all__ = ["User"]
