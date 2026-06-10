"""SQLAlchemy 2 declarative base + reusable typed mixins.

``Base.metadata`` is the Alembic autogenerate target (wired in ``alembic/env.py``).
Plan 02 creates the full 16-table schema against these mixins; no model is declared
here yet beyond the base so the skeleton stays thin.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base — ``metadata`` is the migration source of truth."""


class UUIDPrimaryKeyMixin:
    """UUID v4 primary key generated application-side (``default=uuid.uuid4``)."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """``created_at`` / ``updated_at`` populated by the database server clock."""

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
