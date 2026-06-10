"""CLI entrypoint: ``python -m app.seed`` — load MVP seed content idempotently.

Opens a single ``AsyncSession``, runs the FK-safe ``run_seed`` upsert, and commits
once. Re-runnable with no duplicate-key error (INFRA-03). Prints the per-table row
counts it seeded so the operator gets immediate confirmation.

Run from the ``backend/`` directory after the migration is applied::

    alembic upgrade head
    python -m app.seed
"""

from __future__ import annotations

import asyncio
import logging

from app.core.db import SessionLocal
from app.seed.loader import run_seed

logger = logging.getLogger("app.seed")


async def _main() -> None:
    async with SessionLocal() as session:
        counts = await run_seed(session)
        await session.commit()
    summary = ", ".join(f"{table}={n}" for table, n in counts.items())
    logger.info("seed complete: %s", summary)
    # Always surface the result on stdout too (the CLI's primary feedback channel).
    print(f"seed complete: {summary}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    asyncio.run(_main())


if __name__ == "__main__":
    main()
