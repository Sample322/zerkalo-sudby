"""Native PostgreSQL ENUM types for the fixed status / type sets (TZ §13).

Each set is declared once as a Python ``enum.Enum`` (the canonical value list) plus a
matching SQLAlchemy ``Enum`` *type name*. RESEARCH recommends native PG ENUMs for these
small, stable sets — they give DB-level integrity. The value lists below are the exact
sets enumerated in TZ §13.2/§13.3/§13.8–§13.14.

Usage in models::

    from app.models.enums import reading_status_enum
    status: Mapped[ReadingStatus] = mapped_column(reading_status_enum, ...)

``values_callable`` makes SQLAlchemy persist the *enum value* (the lowercase slug Telegram
and the API speak), not the Python member name.
"""

from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum


class ArcanaType(enum.StrEnum):
    """cards.arcana_type (TZ §13.3)."""

    MAJOR = "major"
    MINOR = "minor"


class Suit(enum.StrEnum):
    """cards.suit (TZ §13.3) — NULL for major arcana."""

    WANDS = "wands"
    CUPS = "cups"
    SWORDS = "swords"
    PENTACLES = "pentacles"


class AccessType(enum.StrEnum):
    """decks.access_type / spread_types.access_type (TZ §13.2)."""

    FREE = "free"
    PREMIUM = "premium"
    SUBSCRIPTION = "subscription"
    ONE_TIME_PURCHASE = "one_time_purchase"
    SEASONAL = "seasonal"
    LIMITED = "limited"


class ReadingStatus(enum.StrEnum):
    """readings.status (TZ §13.8)."""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETED = "deleted"


class Orientation(enum.StrEnum):
    """reading_cards.orientation (TZ §13.9)."""

    UPRIGHT = "upright"
    REVERSED = "reversed"


class PromptTemplateType(enum.StrEnum):
    """prompt_templates.type (TZ §13.10)."""

    SYSTEM = "system"
    SINGLE_CARD = "single_card"
    FINAL_SUMMARY = "final_summary"
    DECK_MODIFIER = "deck_modifier"
    SAFETY = "safety"
    REFUSAL = "refusal"


class ProductType(enum.StrEnum):
    """products.product_type (TZ §13.12)."""

    ONE_TIME_SPREADS = "one_time_spreads"
    SUBSCRIPTION = "subscription"


class PaymentStatus(enum.StrEnum):
    """payments.status (TZ §13.13)."""

    CREATED = "created"
    PRE_CHECKOUT_APPROVED = "pre_checkout_approved"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELED = "canceled"


class SubscriptionStatus(enum.StrEnum):
    """subscriptions.status (TZ §13.14)."""

    ACTIVE = "active"
    CANCELED = "canceled"
    EXPIRED = "expired"
    PAYMENT_FAILED = "payment_failed"


def _pg_enum(py_enum: type[enum.Enum], name: str) -> SAEnum:
    """Build a native PG ``Enum`` that persists member *values* (lowercase slugs).

    ``create_type=True`` (default) means the migration's ``op.create_table`` emits the
    ``CREATE TYPE`` exactly once for the first table that references it; the shared
    instance is reused on any second table (decks + spread_types share ``access_type``)
    so the type is not created twice.
    """
    return SAEnum(
        py_enum,
        name=name,
        values_callable=lambda e: [member.value for member in e],
    )


# Shared, reusable type instances. Reuse the SAME instance across tables that share a
# type (access_type is on both decks and spread_types) so SQLAlchemy treats it as one
# PG type and emits a single CREATE TYPE.
arcana_type_enum = _pg_enum(ArcanaType, "card_arcana_type")
suit_enum = _pg_enum(Suit, "card_suit")
access_type_enum = _pg_enum(AccessType, "access_type")
reading_status_enum = _pg_enum(ReadingStatus, "reading_status")
orientation_enum = _pg_enum(Orientation, "card_orientation")
prompt_template_type_enum = _pg_enum(PromptTemplateType, "prompt_template_type")
product_type_enum = _pg_enum(ProductType, "product_type")
payment_status_enum = _pg_enum(PaymentStatus, "payment_status")
subscription_status_enum = _pg_enum(SubscriptionStatus, "subscription_status")


__all__ = [
    "ArcanaType",
    "Suit",
    "AccessType",
    "ReadingStatus",
    "Orientation",
    "PromptTemplateType",
    "ProductType",
    "PaymentStatus",
    "SubscriptionStatus",
    "arcana_type_enum",
    "suit_enum",
    "access_type_enum",
    "reading_status_enum",
    "orientation_enum",
    "prompt_template_type_enum",
    "product_type_enum",
    "payment_status_enum",
    "subscription_status_enum",
]
