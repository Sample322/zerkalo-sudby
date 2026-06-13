"""``LLMService`` — the swappable single-call generation wrapper (READ-03/04, D-12).

This is the "how we talk to Claude" layer for a reading. It wraps **one**
``client.messages.parse(output_format=ReadingOutput)`` call in the locked resilience contract:

  * **exactly one corrective retry** (``stop_after_attempt(2)`` → 2 tries total) that escalates
    the model Haiku→Sonnet on the retry (D-12 — Haiku is the default, Sonnet is used *only* on
    the corrective attempt);
  * a **per-attempt timeout** (passed to ``messages.parse``);
  * retry only on the verified transient/validation failures
    (``RETRYABLE = (ValidationError, anthropic.APIStatusError, anthropic.APIConnectionError,
    TimeoutError)``) — any other exception type is raised immediately (no retry);
  * a ``refusal`` / ``max_tokens`` ``stop_reason`` is treated as a retry trigger (RESEARCH
    Pitfall 2 — the output may not match the schema);
  * on exhaustion the failure surfaces as ``LLMGenerationError`` so ``ReadingService`` (Plan 05)
    can run the honest-fail path — **never** a fake/templated reading (D-09);
  * usage / latency / resolved model alias / stop_reason are extracted onto ``GenerationResult``
    so the caller writes one ``generation_logs`` row per call (ANALYTICS-02).

Model ids are **aliases** (``claude-haiku-4-5`` / ``claude-sonnet-4-6``), never dated snapshots
(CLAUDE.md "What NOT to Use"); the alias string is what gets logged as the resolved model.

The service is **injectable**: the constructor takes the ``AsyncAnthropic`` client, defaulting to
the ``core/llm_client.py`` singleton, so Plan 05 + the unit tests substitute a mock client and no
real API call is ever made in tests (RESEARCH Pitfall 6 — ``AsyncAnthropic`` + ``await``).

Timing / temperature / token budget are RESEARCH's delegated starting config (A3) kept as named
module constants so they stay tunable without touching the control flow.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import anthropic
from pydantic import ValidationError
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

from app.schemas.reading import ReadingOutput

if TYPE_CHECKING:  # pragma: no cover - typing only
    from anthropic import AsyncAnthropic

# --- Locked model aliases (D-12). NEVER a dated ``-YYYYMMDD`` snapshot (CLAUDE.md). ----------
HAIKU_MODEL = "claude-haiku-4-5"  # default generation model (attempt 1)
SONNET_MODEL = "claude-sonnet-4-6"  # corrective-retry escalation ONLY (attempt 2, D-12)

# --- Delegated starting config (RESEARCH A3) — named so they stay tunable. -------------------
MAX_TOKENS = 1500  # D-10 short copy + 3–4 cards + summary
TEMPERATURE = 0.7  # steadier JSON ↔ more atmosphere; planner-tunable
ATTEMPT_TIMEOUT_SECONDS = 20.0  # per-attempt wall clock; ritual covers ~3s, holds if slower (D-07)
MAX_ATTEMPTS = 2  # one corrective retry total
RETRY_WAIT_SECONDS = 0.5

# Stop reasons that mean the output may not be schema-valid → treat as a retry trigger (Pitfall 2).
_NON_SCHEMA_STOP_REASONS = frozenset({"refusal", "max_tokens"})


class LLMGenerationError(RuntimeError):
    """Raised when generation is exhausted after the corrective retry.

    ``ReadingService`` (Plan 05) catches this to mark the reading ``failed``, keep the limit
    (READ-04/10), and return the soft §9.8 copy — it must NEVER assemble a templated reading
    (D-09). Carries the last underlying exception as ``__cause__`` for the server-side log.
    """


class _NonSchemaStopReason(RuntimeError):
    """Internal retry trigger for a ``refusal`` / ``max_tokens`` stop reason (Pitfall 2)."""


# ``ValidationError`` (schema mismatch on ``parsed_output``) + the verified transient anthropic
# error types + ``TimeoutError`` (per-attempt deadline) + the non-schema-stop trigger above.
RETRYABLE: tuple[type[BaseException], ...] = (
    ValidationError,
    anthropic.APIStatusError,
    anthropic.APIConnectionError,
    TimeoutError,
    _NonSchemaStopReason,
)


@dataclass(frozen=True)
class GenerationResult:
    """The successful single-call result + the audit metadata Plan 05 logs (ANALYTICS-02).

    The fields are exactly what one ``generation_logs`` row needs: the validated ``output`` plus
    the resolved model alias, token usage, wall-clock latency, and the terminal ``stop_reason``.
    """

    output: ReadingOutput
    model_name: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    stop_reason: str


class LLMService:
    """Resilient wrapper around the single ``messages.parse`` generation call."""

    def __init__(self, client: AsyncAnthropic | None = None) -> None:
        """Inject the ``AsyncAnthropic`` client (defaults to the shared singleton).

        Tests/Plan 05 pass a fake client so no real API call is made. The default import is
        local so importing this module never forces client construction during collection.
        """
        if client is None:
            from app.core.llm_client import client as default_client

            client = default_client
        self._client = client

    @staticmethod
    def _model_for_attempt(attempt_number: int) -> str:
        """Attempt 1 → Haiku (default); attempt 2 → Sonnet (the corrective escalation, D-12)."""
        return HAIKU_MODEL if attempt_number <= 1 else SONNET_MODEL

    async def _attempt(self, *, model: str, system: str, user_prompt: str) -> GenerationResult:
        """One ``messages.parse`` call → validated ``GenerationResult`` (raises on any failure).

        ``parsed_output`` raises ``ValidationError`` on a schema mismatch; a non-schema
        ``stop_reason`` is converted to a retryable ``_NonSchemaStopReason``. Both route through
        the tenacity retry policy in ``generate``.
        """
        started = time.monotonic()
        response = await self._client.messages.parse(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=ReadingOutput,
            temperature=TEMPERATURE,
            timeout=ATTEMPT_TIMEOUT_SECONDS,
        )
        # Access first: a refusal/truncated response may already fail schema validation here.
        output: ReadingOutput = response.parsed_output
        stop_reason = response.stop_reason or "end_turn"
        if stop_reason in _NON_SCHEMA_STOP_REASONS:
            # 200 OK but not a trustworthy schema-valid reading → corrective retry (Pitfall 2).
            raise _NonSchemaStopReason(stop_reason)

        latency_ms = max(0, int((time.monotonic() - started) * 1000))
        usage = response.usage
        # The resolved model alias the API echoes; fall back to the requested alias if absent.
        resolved_model = getattr(response, "model", None) or model
        return GenerationResult(
            output=output,
            model_name=resolved_model,
            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
            stop_reason=stop_reason,
        )

    async def generate(self, *, system: str, user_prompt: str) -> GenerationResult:
        """Generate one schema-valid reading with the locked resilience contract.

        Runs at most ``MAX_ATTEMPTS`` tries: attempt 1 on Haiku, the single corrective retry on
        Sonnet (D-12). Retries only on ``RETRYABLE`` (validation / transient API / timeout /
        non-schema stop). On exhaustion raises ``LLMGenerationError`` (Plan 05 → honest fail);
        a non-retryable exception propagates unchanged after a single attempt.
        """
        retrying = AsyncRetrying(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=wait_fixed(RETRY_WAIT_SECONDS),
            retry=retry_if_exception_type(RETRYABLE),
            reraise=True,  # final failure re-raises the real exception (caught below)
        )
        try:
            async for attempt in retrying:
                with attempt:
                    model = self._model_for_attempt(attempt.retry_state.attempt_number)
                    return await self._attempt(
                        model=model, system=system, user_prompt=user_prompt
                    )
        except RETRYABLE as exc:
            # Exhausted the corrective retry on a retryable failure → honest-fail signal (D-09).
            raise LLMGenerationError(
                "LLM generation failed after the corrective retry"
            ) from exc
        # AsyncRetrying always returns or raises inside the loop; this is unreachable.
        raise AssertionError("unreachable")  # pragma: no cover


__all__ = [
    "HAIKU_MODEL",
    "SONNET_MODEL",
    "MAX_TOKENS",
    "TEMPERATURE",
    "ATTEMPT_TIMEOUT_SECONDS",
    "MAX_ATTEMPTS",
    "RETRYABLE",
    "GenerationResult",
    "LLMGenerationError",
    "LLMService",
]
