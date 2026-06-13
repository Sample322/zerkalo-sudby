"""READ-10 — the limit is consumed exactly once on success, never on any non-success exit.

Wave-0 stub — implemented in Plan 04-05 (ReadingService + LimitService seam). Injects
``fake_llm`` / ``fake_safety`` against ``seeded_catalog``. The body will assert:
  * a successful reading decrements ``free_used_this_week`` exactly once;
  * every non-success exit (no quota, crisis short-circuit, abusive redirect, honest fail)
    leaves the counter unchanged (READ-10 / D-09 / Pitfall 4).

Phase 4 only needs "consumed on success, not on failure" — weekly reset/buckets/atomic
decrement are Phase 6 (RESEARCH Deferred Ideas), out of scope for this stub.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (limit consume seam)")
async def test_limit_consumed_once_on_success(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """READ-10: a completed reading consumes exactly one unit."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (limit consume seam)")
async def test_limit_untouched_on_failure(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """READ-10/D-09: honest fail / safety block / no-quota does NOT consume the limit."""
    raise NotImplementedError
