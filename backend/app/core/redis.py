"""Async Redis client (redis-py, pinned ``>=5.2,<6``) + the reading-create throttle.

PING-only in Phase 1 (the ``/healthz`` probe). Phase 6 adds the anti-abuse throttle
(LIMIT-05, D-07): an atomic Lua ``INCR`` + conditional-``EXPIRE`` per-user counter that
GATE-0s ``POST /api/readings`` before any Postgres/LLM work. Weekly limits stay PG-authoritative
(CLAUDE.md) — Redis is used here ONLY for the throttle write, never as the count read-path.
Pinned ``<6`` to avoid the fresh redis-py 8.0 RESP3 default.
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


# ---------------------------------------------------------------------------------------
# Reading-create throttle (LIMIT-05, D-07 / RESEARCH Pattern 3).
#
# An atomic Lua ``INCR`` + conditional-``EXPIRE``: the TTL is set ONLY when ``INCR`` returns 1
# (the first hit in the window), so the fixed window has NO stuck-counter race — a worker dying
# between the INCR and the EXPIRE (the plain two-await form) could strand a key without a TTL and
# throttle a user forever. Running both inside one Lua script makes the pair indivisible.
#
# Band (within D-07): a single ~60s window, cap ~5. A real user (30s+ between readings) tops out
# at ~2/min and is never throttled; rapid double-taps and scripts are caught. The throttle counts
# creation ATTEMPTS (it runs first, before validation) — intended, not a bug (RESEARCH Pitfall 4).
# ---------------------------------------------------------------------------------------

_THROTTLE_LUA = (
    "local c = redis.call('INCR', KEYS[1])\n"
    "if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end\n"
    "return c"
)

# Registered once at module load. ``register_script`` is lazy — it does NOT touch Redis until the
# script is first called (it auto-loads on ``NOSCRIPT`` and retries), so importing this module
# never requires a live Redis.
_throttle_script = redis_client.register_script(_THROTTLE_LUA)

# Fixed-window band (D-07). The exact numbers are the planner's within the band.
THROTTLE_WINDOW_S = 60
THROTTLE_BURST_CAP = 5


async def throttle_ok(
    user_id: object,
    *,
    window_s: int = THROTTLE_WINDOW_S,
    burst_cap: int = THROTTLE_BURST_CAP,
    bucket: str = "reading",
) -> bool:
    """Atomic per-user burst check — ``True`` while under the cap, ``False`` once over it.

    Keys off the caller-supplied ``user_id`` ONLY (``throttle_gate`` passes the verified JWT
    ``user.id`` — never a request-body field, T-06 spoofing). The key shape is
    ``throttle:{bucket}:{user_id}`` (per-user, per-bucket so independent surfaces — ``reading`` vs
    ``events`` — never share a budget). Runs the atomic Lua ``INCR``+conditional-``EXPIRE``, so the
    TTL is always armed on the first hit (no stranded counter).

    ``decode_responses=True`` on the shared client makes the Lua ``return c`` arrive as a ``str``;
    it is cast with ``int()`` before the comparison.
    """
    count = await _throttle_script(
        keys=[f"throttle:{bucket}:{user_id}"],
        args=[window_s],
    )
    return int(count) <= burst_cap


__all__ = [
    "redis_client",
    "get_redis",
    "throttle_ok",
    "THROTTLE_WINDOW_S",
    "THROTTLE_BURST_CAP",
]
