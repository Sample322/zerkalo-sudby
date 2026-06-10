"""Idempotent seed loader — exact counts + idempotency (INFRA-03, Plan 03 Task 2).

Replaces the Wave-0 skip stub. Against a **real** PostgreSQL test database these tests
prove the MVP seed (``app.seed.loader.run_seed``):

  * ``test_seed_counts`` — loads exactly 7 topics, 6 decks, 7 spread_types, 78 cards,
    23 spread_positions (3+3+3+3+3+4+4) and 11 prompt_templates
    (system + single_card + final_summary + 6 deck_modifier + safety + refusal);
  * ``test_seed_idempotent`` — running ``run_seed`` twice yields identical counts with
    no ``IntegrityError`` (upsert-by-slug, T-03-01 mitigation).

DB requirement: Postgres reachable at ``settings.DATABASE_URL``. When the DB is
unreachable (e.g. ``docker compose`` is not up), the tests ``pytest.skip`` cleanly so the
suite stays green and fully collectable — matching ``test_migration.py``. When the stack
is live they exercise the seed for real.

The seed must persist across transactions (idempotency is a *re-run* property), so these
tests COMMIT (they do not use the rollback-scoped ``db_session`` fixture). Each test owns
its schema lifecycle: migrate to a clean ``head`` first, then assert, then ``downgrade
base`` so no rows leak between tests. Alembic's async ``env.py`` calls ``asyncio.run`` (illegal
inside pytest-asyncio's running loop), so migrations run on a worker thread.
"""

from __future__ import annotations

import threading
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.db import SessionLocal
from app.seed.loader import run_seed

# Exact target counts (INFRA-03 / TZ §27).
EXPECTED_COUNTS: dict[str, int] = {
    "topics": 7,
    "decks": 6,
    "spread_types": 7,
    "cards": 78,
    "spread_positions": 23,  # 3+3+3+3+3+4+4
    "prompt_templates": 11,  # system + single_card + final_summary + 6 deck_modifier + safety + refusal
}

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _alembic_config():
    from alembic.config import Config

    cfg = Config(str(_BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_BACKEND_ROOT / "alembic"))
    return cfg


def _run_alembic(direction: str, revision: str) -> None:
    """Run alembic upgrade/downgrade on a worker thread (fresh event loop)."""
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


async def _count(table: str) -> int:
    """SELECT count(*) for one seeded table via a short-lived connection."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(sa.text(f"SELECT count(*) FROM {table}"))
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def _all_counts() -> dict[str, int]:
    return {table: await _count(table) for table in EXPECTED_COUNTS}


async def _seed_once() -> None:
    """Run ``run_seed`` in its own session and commit (persist across transactions)."""
    async with SessionLocal() as session:
        await run_seed(session)
        await session.commit()


async def test_seed_counts() -> None:
    """INFRA-03: seed loads exactly 7 topics / 6 decks / 7 spreads / 78 cards / 23 positions / 11 prompts."""
    if not await _db_reachable():
        pytest.skip("Postgres unreachable — start `docker compose up` to run the seed test")

    # Clean slate at head, seed once, assert exact counts, then reverse.
    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")
    try:
        await _seed_once()
        counts = await _all_counts()
        assert counts == EXPECTED_COUNTS, f"seed counts mismatch: {counts}"
    finally:
        _run_alembic("downgrade", "base")


async def test_seed_idempotent() -> None:
    """INFRA-03: running the seed twice yields identical counts with no duplicate-key error."""
    if not await _db_reachable():
        pytest.skip("Postgres unreachable — start `docker compose up` to run the seed test")

    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")
    try:
        # First run establishes the rows; second run must be a no-op upsert (no IntegrityError).
        await _seed_once()
        counts_first = await _all_counts()
        assert counts_first == EXPECTED_COUNTS, f"first seed mismatch: {counts_first}"

        await _seed_once()  # re-run: ON CONFLICT DO UPDATE, no dup-key error
        counts_second = await _all_counts()
        assert counts_second == counts_first, (
            f"idempotency violated: {counts_first} -> {counts_second}"
        )
    finally:
        _run_alembic("downgrade", "base")
