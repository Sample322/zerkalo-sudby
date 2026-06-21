"""Async SQLAlchemy 2 engine + session factory.

DSN form is ``postgresql+asyncpg://...`` (see ``.env.example``). A libpq ``?sslmode=...``
query param is translated to an asyncpg ``connect_args={"ssl": ...}`` via
``app.core.db_url`` (asyncpg does not accept ``sslmode``), so a managed-Postgres URL such as
``...?sslmode=require`` connects unchanged. ``pool_pre_ping`` recycles dead connections so the
first request after an idle period does not fail.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.db_url import async_url_and_connect_args

_url, _connect_args = async_url_and_connect_args(settings.DATABASE_URL)
engine = create_async_engine(_url, pool_pre_ping=True, connect_args=_connect_args)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with SessionLocal() as session:
        yield session
