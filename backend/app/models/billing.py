"""Billing aggregate: ``user_limits`` (§13.11), ``products`` (§13.12), ``payments``
(§13.13), ``subscriptions`` (§13.14).

**Provider pivot (Phase 7, D-01):** the owner replaced the Telegram Stars rail with
**ЮKassa (YooKassa) direct v3 API** in RUB. The Stars-era columns stay (additive
migration 0004 only flips the server-defaults for NEW rows: ``payments.provider``
``telegram_stars``→``yookassa``, ``payments.currency`` ``XTR``→``RUB`` — D-02), and the
ЮKassa surface is carried by the new provider-agnostic columns below.

- ``user_limits``: the per-user quota state — free weekly counter (Postgres is the source
  of truth, Redis is a fast mirror) + paid/subscription balances.
- ``products``: purchasable packs / subscription. ``product_type`` ENUM. **A1 (Phase 7):**
  ``stars_price`` now holds the price as an **integer in RUBLES** (e.g. ``299`` ⇒ ``299``),
  formatted ``"{:.2f}"`` (``"299.00"``) by the service charge-helper at ЮKassa-call time —
  NOT kopecks, NOT Telegram Stars. The column name is kept (lowest-churn, additive plan).
- ``payments``: every transaction. ``payload`` is **UNIQUE** and the ЮKassa
  ``provider_payment_id`` is **UNIQUE**-indexed so payment idempotency is DB-guaranteed
  (threats T-02-02 / T-07-IDOR / T-07-REPLAY — the exactly-once grant backstop);
  ``raw_update`` JSONB keeps the full audit trail (threat T-02-03). ``status`` ENUM. The
  legacy ``telegram_payment_charge_id`` index is retained but unused under ЮKassa.
- ``subscriptions``: the entitlement window (DB is the source of truth, not the provider —
  D-08). ``status`` ENUM. ``telegram_payment_charge_id`` is now **nullable** so a ЮKassa
  subscription insert (which has no Telegram charge id — it has a saved
  ``payment_method_id`` instead) is legal.

Timestamp columns follow TZ exactly: ``user_limits`` has only ``updated_at``; ``payments``
has ``created_at``/``paid_at``/``refunded_at`` (no ``updated_at``); ``products`` and
``subscriptions`` have both ``created_at``/``updated_at`` (TimestampMixin).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Integer, String, UniqueConstraint, func
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

    # 1:1 with ``users`` — the UNIQUE constraint is the ON CONFLICT (user_id) target for the
    # race-safe row-ensure at auth (D-02 / migration 0002); the name MUST match the migration.
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_limits_user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    free_weekly_limit: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3"
    )
    free_used_this_week: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    # Rolling-window anchor (D-01): the TIMESTAMP of the first reading after a reset, NULL for a
    # brand-new user (anchors on first reading). TIMESTAMP not DATE so the 7-day window is
    # hour-accurate (A1 / Pitfall 1).
    week_start: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
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
    # D-02: server-defaults flipped to the ЮKassa provider/currency for NEW rows (migration
    # 0004). Existing Stars-era rows keep their old values (no data migration — no real payments).
    provider: Mapped[str] = mapped_column(
        String, default="yookassa", server_default="yookassa"
    )
    currency: Mapped[str] = mapped_column(String, default="RUB", server_default="RUB")
    amount: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(String, unique=True)
    # Legacy Stars charge id — retained (indexed) but unused under ЮKassa; the provider-agnostic
    # id below is the ЮKassa source of truth.
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )
    # --- ЮKassa surface (Phase 7, D-04/D-06). All nullable (additive; a CREATED row is written
    # before the SDK call, then provider_payment_id/confirmation_url are filled from the response). ---
    # The ЮKassa payment id — UNIQUE so a redelivered webhook grants exactly once (T-07-REPLAY).
    provider_payment_id: Mapped[str | None] = mapped_column(
        String, unique=True, index=True, nullable=True
    )
    # The ЮKassa-hosted payment page URL (confirmation.confirmation_url) the FE opens via openLink.
    confirmation_url: Mapped[str | None] = mapped_column(String, nullable=True)
    # The per-attempt Idempotence-Key sent to ЮKassa (uuid4) — audit + retry-safe (Pitfall 5).
    idempotence_key: Mapped[str | None] = mapped_column(String, nullable=True)
    # A saved ЮKassa payment method id (set when a pack also saves a method; subscriptions use it).
    payment_method_id: Mapped[str | None] = mapped_column(String, nullable=True)
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
    # D-08: now NULLABLE — a ЮKassa subscription has no Telegram charge id (it has a saved
    # payment_method_id instead). Migration 0004 drops the old NOT NULL.
    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # --- ЮKassa recurring surface (Phase 7, D-08). The saved method + the deterministic-key
    # bookkeeping for merchant-initiated renewals (ЮKassa does NOT auto-charge — Pattern 4). ---
    # The saved ЮKassa payment_method_id reused for every renewal charge.
    payment_method_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # The ЮKassa payment id of the most recent (first or renewal) charge for this subscription.
    provider_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # When the last successful charge landed (renewal bookkeeping / dunning).
    last_charge_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Monotonic period counter — the renewal Idempotence-Key is ``renew:{sub_id}:{period_index}``
    # (Pitfall 5: deterministic per period so a retry is a safe no-op, the next period a new key).
    period_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
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
