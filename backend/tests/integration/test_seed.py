"""RED stubs — idempotent seed loader (INFRA-03).

Wave-0 placeholders for VALIDATION.md node IDs. Plan 03 removes the skip and asserts the
seed loads exact counts (7 topics, 6 decks, 7 spreads, 78 cards, N prompt templates) and
is idempotent (run twice -> same counts, no dup-key error).

DO NOT implement here — Plan 03 owns these.
"""

from __future__ import annotations

import pytest

_OWNER = "Wave 0 stub — implemented in Plan 03 (seed loader)"


@pytest.mark.skip(reason=_OWNER)
async def test_seed_counts() -> None:
    """INFRA-03: seed loads exactly 7 topics / 6 decks / 7 spreads / 78 cards / N prompts."""
    raise NotImplementedError("Plan 03 implements seed-count assertions")


@pytest.mark.skip(reason=_OWNER)
async def test_seed_idempotent() -> None:
    """INFRA-03: running the seed twice yields the same counts (no duplicate-key error)."""
    raise NotImplementedError("Plan 03 implements seed-idempotency assertion")
