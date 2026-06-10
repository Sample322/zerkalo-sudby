"""Billing aggregate: ``user_limits`` (§13.11), ``products`` (§13.12), ``payments``
(§13.13), ``subscriptions`` (§13.14).

- ``user_limits``: the per-user quota state — free weekly counter (Postgres is the source
  of truth, Redis is a fast mirror) + paid/subscription balances.
- ``products``: purchasable packs / subscription (Telegram Stars). ``product_type`` ENUM.
- ``payments``: every Stars transaction. ``payload`` is **UNIQUE** and
  ``telegram_payment_charge_id`` is indexed so Phase-7 payment idempotency is
  DB-guaranteed (threat T-02-02); ``raw_update`` JSONB keeps the full audit trail
  (threat T-02-03). ``status`` ENUM.
- ``subscriptions``: the entitlement window (DB is the source of truth, not Telegram).
  ``status`` ENUM.

Timestamp columns follow TZ exactly: ``user_limits`` has only ``updated_at``; ``payments``
has ``created_at``/``paid_at``/``refunded_at`` (no ``updated_at``); ``products`` and
``subscriptions`` have both ``created_at``/``updated_at`` (TimestampMixin).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    PaymentStatus,
    ProductType,
    SubscriptionStatus,
    payment_status_enum,
    product_type_enum,
    subscription_status_enum,
)


class UserLimits(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_limits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    free_weekly_limit: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3"
    )
    free_used_this_week: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    week_start: Mapped[date | None] = mapped_column(nullable=True)
    paid_spreads_balance: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    subscription_spreads_limit: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    subscription_spreads_used: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    product_type: Mapped[ProductType] = mapped_column(product_type_enum)
    stars_price: Mapped[int] = mapped_column(Integer)
    spreads_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    subscription_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class Payment(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    provider: Mapped[str] = mapped_column(
        String, default="telegram_stars", server_default="telegram_stars"
    )
    currency: Mapped[str] = mapped_column(String, default="XTR", server_default="XTR")
    amount: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(String, unique=True)
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )
    status: Mapped[PaymentStatus] = mapped_column(
        payment_status_enum,
        default=PaymentStatus.CREATED,
        server_default=PaymentStatus.CREATED.value,
    )
    raw_update: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(nullable=True)


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    telegram_payment_charge_id: Mapped[str] = mapped_column(String)
    status: Mapped[SubscriptionStatus] = mapped_column(
        subscription_status_enum,
        default=SubscriptionStatus.ACTIVE,
        server_default=SubscriptionStatus.ACTIVE.value,
    )
    started_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    current_period_start: Mapped[datetime] = mapped_column(
        server_default=func.now(), nullable=False
    )
    current_period_end: Mapped[datetime] = mapped_column()
    canceled_at: Mapped[datetime | None] = mapped_column(nullable=True)


__all__ = ["UserLimits", "Product", "Payment", "Subscription"]
