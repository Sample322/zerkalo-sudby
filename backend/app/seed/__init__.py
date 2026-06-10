"""Seed package — idempotent MVP catalog loader (INFRA-03).

``run_seed`` upserts the JSON content under ``data/`` by slug; ``python -m app.seed``
(see ``__main__.py``) opens a session and runs it, committing once.
"""

from __future__ import annotations

from app.seed.loader import run_seed, upsert_by_slug

__all__ = ["run_seed", "upsert_by_slug"]
