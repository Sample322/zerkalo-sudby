"""FastAPI application entrypoint.

Boots with structured logging, mounts the health router, and disposes the DB engine +
closes the Redis client on shutdown. The auth/admin routers and the global soft-error
exception handler are registered in Plan 04 at the marked seam.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import admin, auth, decks, health, readings, spreads, users
from app.core.db import engine
from app.core.errors import unhandled_exception_handler
from app.core.logging import configure_logging
from app.core.redis import redis_client
from app.core.sentry import init_sentry

logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    init_sentry()  # no-op unless SENTRY_DSN is set (INFRA-05)
    logger.info("startup", extra={"event": "lifespan.startup"})
    try:
        yield
    finally:
        logger.info("shutdown", extra={"event": "lifespan.shutdown"})
        await engine.dispose()
        await redis_client.aclose()


app = FastAPI(
    title="Зеркало Судьбы API",
    version="0.1.0",
    lifespan=lifespan,
)

# --- Routers ---
app.include_router(health.router)
app.include_router(auth.router, prefix="/api")  # POST /api/auth/telegram
app.include_router(users.router, prefix="/api")  # GET  /api/me
app.include_router(admin.router, prefix="/api")  # GET  /api/admin/ping (require_admin)
app.include_router(decks.router, prefix="/api")  # GET  /api/decks, /api/decks/{slug}
app.include_router(spreads.router, prefix="/api")  # GET  /api/spreads, /api/spreads/recommend
app.include_router(readings.router, prefix="/api")  # POST /api/readings (Bearer JWT)

# --- INFRA-05: global soft-error handler (no stacktrace leak to the client) --------
# Registered for the bare ``Exception`` only — FastAPI keeps its own HTTPException /
# RequestValidationError handlers, so 401 / 403 / 422 retain their semantics.
app.add_exception_handler(Exception, unhandled_exception_handler)
