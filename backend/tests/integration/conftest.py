"""Integration-test fixtures for the auth slice (Plan 04).

These tests exercise the real ``POST /api/auth/telegram`` -> upsert -> JWT -> Bearer round
trip against a live test database. To keep each test isolated even though the service code
calls ``session.commit()``, we use SQLAlchemy's documented "join an external transaction"
recipe: open one outer transaction on a dedicated connection, bind the session to it, and
restart a SAVEPOINT after every inner ``commit()``. At teardown the outer transaction is
rolled back, so nothing persists between tests.

The app's ``get_session`` dependency is overridden to yield this same transaction-scoped
session, so the endpoint and the test assertions see one consistent view.

Everything skips cleanly (via the shared ``_db_ready`` fixture in the root conftest) when
Postgres is unreachable, so the suite stays green + collectable without ``docker compose up``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.db import engine
from app.main import app


@pytest.fixture
async def auth_session(_db_ready: bool) -> AsyncIterator[AsyncSession]:
    """A transaction-isolated ``AsyncSession`` that survives inner ``commit()`` calls.

    Outer transaction on one connection + auto-restarting SAVEPOINT; rolled back at teardown.
    """
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")

        try:
            yield session
        finally:
            await session.close()
            if outer.is_active:
                await outer.rollback()


@pytest.fixture
async def auth_client(auth_session: AsyncSession) -> AsyncIterator[object]:
    """In-process client with ``get_session`` overridden to the isolated test session."""
    from httpx import ASGITransport, AsyncClient

    async def _override_get_session() -> AsyncIterator[AsyncSession]:
        yield auth_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_session, None)
