"""Liveness/readiness probe (INFRA-04).

Performs a **real** dependency probe — a Postgres ``SELECT 1`` and a Redis ``PING`` —
so ``docker compose`` healthchecks reflect actual reachability, not just "process up"
(RESEARCH Pitfall 3: the healthcheck-that-lies). Returns 503 with per-dependency status
when any probe fails.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_redis, get_session

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    checks: dict[str, str] = {}

    try:
        await session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "down"

    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"

    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(checks, status_code=200 if healthy else 503)
