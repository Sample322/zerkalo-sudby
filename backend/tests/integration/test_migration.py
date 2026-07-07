"""Full-schema migration round-trip (INFRA-02, Plan 02 Task 2).

Asserts, against a **real** PostgreSQL test database, that the single initial migration
``0001_initial_schema``:

  * ``alembic upgrade head`` creates all 17 tables (16 TZ §13 + ``topics``);
  * the key UNIQUE constraints exist (``users.telegram_id``, ``payments.payload``, and
    every ``slug``) — queried from ``information_schema``;
  * ``alembic downgrade base`` removes every one of those tables (reversible).

DB requirement: this needs Postgres reachable at ``settings.DATABASE_URL``. When the DB
is unreachable (e.g. ``docker compose`` is not up in CI/dev), the test ``pytest.skip``s
cleanly so the suite stays green and fully collectable — but when the stack is live it
exercises the migration for real (no ``@pytest.mark.skip``; the assertions always run when
a DB is present).

Alembic's online runner calls ``asyncio.run`` internally, which cannot be invoked from
inside pytest-asyncio's already-running event loop. We therefore drive Alembic in a worker
thread (fresh loop) and use a separate synchronous ``psycopg``-free reachability probe via
the async engine.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings

# 16 TZ §13 tables + the topics lookup.
EXPECTED_TABLES = frozenset(
    {
        "topics",
        "users",
        "decks",
        "cards",
        "deck_cards",
        "spread_types",
        "spread_positions",
        "deck_spread_compatibility",
        "readings",
        "reading_cards",
        "prompt_templates",
        "user_limits",
        "products",
        "payments",
        "subscriptions",
        "app_events",
        "generation_logs",
    }
)

# (table, column) pairs that MUST carry a UNIQUE constraint.
EXPECTED_UNIQUES = frozenset(
    {
        ("users", "telegram_id"),
        ("payments", "payload"),
        ("decks", "slug"),
        ("cards", "slug"),
        ("spread_types", "slug"),
        ("prompt_templates", "slug"),
        ("products", "slug"),
        ("topics", "slug"),
    }
)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config():
    """Build an Alembic ``Config`` pointed at this backend's ``alembic.ini``."""
    from alembic.config import Config

    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    # env.py injects sqlalchemy.url from settings.DATABASE_URL itself.
    return cfg


def _run_alembic(direction: str, revision: str) -> None:
    """Run ``alembic upgrade/downgrade`` in a worker thread (own event loop).

    Alembic's async ``env.py`` calls ``asyncio.run`` — illegal inside the test's running
    loop — so we execute it on a fresh thread where no loop is running.
    """
    from alembic import command

    error: list[BaseException] = []

    def _target() -> None:
        try:
            cfg = _alembic_config()
            if direction == "upgrade":
                command.upgrade(cfg, revision)
            else:
                command.downgrade(cfg, revision)
        except BaseException as exc:  # noqa: BLE001 - re-raised on the main thread
            error.append(exc)

    thread = threading.Thread(target=_target)
    thread.start()
    thread.join()
    if error:
        raise error[0]


async def _db_reachable() -> bool:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - environment-dependent
        return False
    finally:
        await engine.dispose()


async def _present_tables() -> set[str]:
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                sa.text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            return {r[0] for r in rows}
    finally:
        await engine.dispose()


async def _unique_columns() -> set[tuple[str, str]]:
    """Return (table, column) pairs backed by a UNIQUE constraint (information_schema)."""
    engine = create_async_engine(settings.DATABASE_URL)
    query = sa.text(
        """
        SELECT tc.table_name, kcu.column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema = kcu.table_schema
        WHERE tc.constraint_type = 'UNIQUE'
          AND tc.table_schema = 'public'
        """
    )
    try:
        async with engine.connect() as conn:
            rows = await conn.execute(query)
            return {(r[0], r[1]) for r in rows}
    finally:
        await engine.dispose()


async def test_full_schema_applies(clean_migration_db: None) -> None:
    """INFRA-02: upgrade head creates all 17 tables + key uniques; downgrade base reverses."""
    if not await _db_reachable():
        pytest.skip("Postgres unreachable — start `docker compose up` to run the migration test")

    # Clean slate, then apply the whole schema.
    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")

    try:
        present = await _present_tables()
        missing = EXPECTED_TABLES - present
        assert not missing, f"missing tables after upgrade head: {sorted(missing)}"
        assert len(EXPECTED_TABLES & present) == 17

        uniques = await _unique_columns()
        missing_uniques = EXPECTED_UNIQUES - uniques
        assert not missing_uniques, f"missing UNIQUE constraints: {sorted(missing_uniques)}"
    finally:
        # Always reverse so the test leaves no schema behind (and proves reversibility).
        _run_alembic("downgrade", "base")

    after_downgrade = await _present_tables()
    leftover = EXPECTED_TABLES & after_downgrade
    assert not leftover, f"tables not dropped by downgrade base: {sorted(leftover)}"
