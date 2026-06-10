"""Shared FastAPI dependencies.

Phase 1 only re-exports the DB + Redis session providers. Plan 04 adds
``get_current_user`` (JWT bearer) and ``require_admin`` (server-side
``ADMIN_TELEGRAM_IDS`` allowlist) here so routers can stay thin.
"""

from __future__ import annotations

from app.core.db import get_session
from app.core.redis import get_redis

__all__ = ["get_session", "get_redis"]
