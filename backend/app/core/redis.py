"""Async Redis client (redis-py, pinned ``>=5.2,<6``).

PING-only in Phase 1 (the ``/healthz`` probe). Weekly limits / throttle / cache come
in later phases. Pinned ``<6`` to avoid the fresh redis-py 8.0 RESP3 default.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from app.core.config import settings

# decode_responses=True so PING and future GET/SET return str, not bytes.
redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


async def get_redis() -> AsyncIterator[aioredis.Redis]:
    """FastAPI dependency yielding the shared async Redis client."""
    yield redis_client
