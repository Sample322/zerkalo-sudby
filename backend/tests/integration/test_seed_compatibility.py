"""Integration — ``deck_spread_compatibility`` seed (SPREAD-04, Plan 02-01 Task 1).

Phase 1 deliberately left ``deck_spread_compatibility`` empty; SPREAD-04's "recommendation
honors compatibility" therefore had no data. Phase 2 derives the rows from REFERENCE-TZ §7
(``compatibility.json``) and seeds them in ``run_seed``. Against a **real** PostgreSQL test
database these tests prove:

  * ``test_compat_seeded`` — after ``run_seed`` the table is non-empty AND at least one row
    is ``is_recommended=true``;
  * ``test_compat_idempotent`` — running ``run_seed`` twice yields identical compatibility
    row counts with no ``IntegrityError`` (scoped delete -> insert per deck);
  * ``test_compat_scores`` — for a known pair (heart_oracle x between_us) the row is
    ``is_recommended=true`` and ``compatibility_score`` equals the size of the deck/spread
    ``recommended_topics`` overlap.

Like ``test_seed.py`` these COMMIT (idempotency is a re-run property) and own their schema
lifecycle (migrate to a clean ``head``, assert, ``downgrade base``). Alembic's async
``env.py`` calls ``asyncio.run`` (illegal inside the running pytest-asyncio loop), so
migrations run on a worker thread. When Postgres is unreachable the tests ``pytest.skip``
cleanly so the suite stays green + collectable without ``docker compose up``.
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


async def _compat_total() -> int:
    """Total rows in deck_spread_compatibility via a short-lived connection."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                sa.text("SELECT count(*) FROM deck_spread_compatibility")
            )
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def _recommended_count() -> int:
    """Rows with is_recommended=true via a short-lived connection."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                sa.text(
                    "SELECT count(*) FROM deck_spread_compatibility "
                    "WHERE is_recommended IS TRUE"
                )
            )
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def _pair_row(deck_slug: str, spread_slug: str) -> tuple[int, bool] | None:
    """Return (compatibility_score, is_recommended) for one (deck, spread) pair, or None."""
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                sa.text(
                    "SELECT c.compatibility_score, c.is_recommended "
                    "FROM deck_spread_compatibility c "
                    "JOIN decks d ON d.id = c.deck_id "
                    "JOIN spread_types s ON s.id = c.spread_type_id "
                    "WHERE d.slug = :deck AND s.slug = :spread"
                ),
                {"deck": deck_slug, "spread": spread_slug},
            )
            row = result.first()
            return (int(row[0]), bool(row[1])) if row else None
    finally:
        await engine.dispose()


async def _seed_once() -> None:
    """Run ``run_seed`` in its own session and commit (persist across transactions)."""
    async with SessionLocal() as session:
        await run_seed(session)
        await session.commit()


async def test_compat_seeded() -> None:
    """SPREAD-04: after seed, compatibility is non-empty with >=1 is_recommended row."""
    if not await _db_reachable():
        pytest.skip("Postgres unreachable — start `docker compose up` to run the seed test")

    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")
    try:
        await _seed_once()
        assert await _compat_total() > 0, "deck_spread_compatibility was not seeded"
        assert await _recommended_count() > 0, "no is_recommended=true compatibility row"
    finally:
        _run_alembic("downgrade", "base")


async def test_compat_idempotent() -> None:
    """SPREAD-04: running the seed twice yields identical compat counts, no dup-key error."""
    if not await _db_reachable():
        pytest.skip("Postgres unreachable — start `docker compose up` to run the seed test")

    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")
    try:
        await _seed_once()
        first = await _compat_total()
        assert first > 0, "first seed produced no compatibility rows"

        await _seed_once()  # re-run: scoped delete -> insert, no IntegrityError
        second = await _compat_total()
        assert second == first, f"compat idempotency violated: {first} -> {second}"
    finally:
        _run_alembic("downgrade", "base")


async def test_compat_scores() -> None:
    """SPREAD-04: heart_oracle x between_us is recommended; score == topic overlap (2).

    heart_oracle.recommended_topics = {love, general, self_reflection}
    between_us.recommended_topics    = {love, general}
    overlap = {love, general} -> compatibility_score == 2.
    """
    if not await _db_reachable():
        pytest.skip("Postgres unreachable — start `docker compose up` to run the seed test")

    _run_alembic("downgrade", "base")
    _run_alembic("upgrade", "head")
    try:
        await _seed_once()
        pair = await _pair_row("heart_oracle", "between_us")
        assert pair is not None, "expected a heart_oracle x between_us compatibility row"
        score, is_recommended = pair
        assert is_recommended is True
        assert score == 2, f"expected topic-overlap score 2, got {score}"
    finally:
        _run_alembic("downgrade", "base")
