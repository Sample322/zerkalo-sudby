"""ANALYTICS-02 — one ``generation_logs`` row per LLM call (classify + each generation attempt).

Wave-0 stub — implemented in Plan 04-05 (ReadingService generation_logs writes). Injects
``fake_llm`` / ``fake_safety`` against ``seeded_catalog``. The body will assert:
  * each LLM call (the classify call + every generation attempt) writes exactly one
    ``generation_logs`` row;
  * each row carries ``prompt_template_version`` / ``model_name`` / ``input_tokens`` /
    ``output_tokens`` / ``latency_ms`` / ``status`` / ``error`` (fields map 1:1 to what
    ``messages.parse`` exposes);
  * a failed attempt logs ``status='failed'`` with the error; a corrective retry logs two rows.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (generation_logs writes)")
async def test_log_row_per_llm_call(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """ANALYTICS-02: one generation_logs row per LLM call with model/tokens/latency/status."""
    raise NotImplementedError


@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-05 (generation_logs writes)")
async def test_failed_attempt_logged(
    auth_client: object, fake_llm: object, fake_safety: object, seeded_catalog: dict
) -> None:
    """ANALYTICS-02: a failed generation attempt logs status='failed' + the error."""
    raise NotImplementedError
