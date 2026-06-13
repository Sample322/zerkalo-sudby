"""READ-03/04/05/06 — the reading flow: success / honest-fail / corrective-retry (mocked LLM).

Wave-0 stub — implemented in Plan 04-05 (ReadingService orchestration). All three paths inject
``fake_llm`` / ``fake_safety`` (never a real Anthropic call) and run against ``seeded_catalog``.
The body will assert:
  * **success** — mocked LLM → ``readings`` + ``reading_cards`` persisted, ``status=completed``,
    response carries every per-card field + all five summary fields (READ-03/05/06);
  * **honest-fail** — ``ValidationError`` on every attempt → ``reading=failed``, soft §9.8 body,
    limit NOT consumed, NO templated stand-in reading (READ-04 / D-09);
  * **corrective-retry** — invalid once then valid → the retry escalates Haiku→Sonnet and the
    reading completes (READ-04 / D-12).
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (ReadingService)")
async def test_success(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """READ-03/05/06: mocked LLM success → completed reading with all fields persisted."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (ReadingService)")
async def test_honest_fail(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """READ-04/D-09: invalid JSON twice → failed, soft §9.8 body, limit NOT consumed."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (ReadingService)")
async def test_corrective_retry(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """READ-04/D-12: invalid once then valid → Sonnet-escalated retry succeeds."""
    raise NotImplementedError
