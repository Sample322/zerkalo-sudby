---
phase: 04-real-personal-reading-keystone
plan: 03
subsystem: api
tags: [anthropic, messages-parse, structured-outputs, tenacity, safety-classifier, llm-service, regex-prefilter, pytest, tdd]

# Dependency graph
requires:
  - phase: 04-01
    provides: "app.schemas.reading contracts (ReadingOutput, SafetyVerdict, SafetyCategory, ClassifyResult, ClassifyCallMeta); core/llm_client.py AsyncAnthropic singleton; Wave-0 test stubs"
provides:
  - "LLMService.generate — ONE messages.parse(output_format=ReadingOutput) wrapped in tenacity (1 corrective retry Haiku→Sonnet, D-12) + per-attempt timeout + usage/latency/stop_reason extraction; raises LLMGenerationError on exhaustion (honest fail, D-09)"
  - "GenerationResult dataclass — the (output + model_name/input_tokens/output_tokens/latency_ms/stop_reason) audit record Plan 05 writes to generation_logs (ANALYTICS-02)"
  - "SafetyService.classify — regex pre-filter (instant crisis_sensitive + empty→normal, NO call) then a tiny Haiku messages.parse(output_format=SafetyVerdict); returns ClassifyResult(verdict, via_regex, meta)"
  - "route(verdict) → SafetyAction (crisis→REFUSAL, abusive→REDIRECT, *_sensitive→SAFETY_MODIFIER, normal→GENERATE) with a continues_to_draw boundary — the gate Plan 05 runs before the draw"
affects: [04-05, reading-orchestration, prompt-engine, reading-service, generation-logs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Injectable AsyncAnthropic client (constructor default = core/llm_client singleton, local import) → Plan 05 + tests substitute a mock; no real API call in tests, no client construction at module import"
    - "tenacity AsyncRetrying with per-attempt model selection keyed off retry_state.attempt_number (Haiku attempt 1 → Sonnet attempt 2, D-12) + reraise wrapped into a typed LLMGenerationError"
    - "Non-schema stop_reason (refusal/max_tokens) converted to an internal retryable exception so it routes through the same tenacity policy as ValidationError (Pitfall 2)"
    - "Two-stage gate: pure synchronous regex pre-filter (zero-cost crisis short-circuit + empty→normal) before any LLM call, then a tiny enum-only structured classify; pure route() mapping unit-tested without a client"
    - "Frozen-dataclass / Pydantic audit record (GenerationResult / ClassifyCallMeta) carrying exactly the generation_logs columns the caller logs per LLM call"

key-files:
  created:
    - "backend/app/services/llm.py"
    - "backend/app/services/safety.py"
    - "backend/tests/unit/test_llm_service.py"
  modified:
    - "backend/tests/unit/test_safety_routing.py"

key-decisions:
  - "LLMService wraps ONE messages.parse(output_format=ReadingOutput) in tenacity AsyncRetrying (stop_after_attempt(2), wait_fixed(0.5), reraise=True); attempt 1 = claude-haiku-4-5, the single corrective retry = claude-sonnet-4-6 (D-12) keyed off retry_state.attempt_number. Model aliases only — no dated snapshot (CLAUDE.md)."
  - "RETRYABLE = (ValidationError, anthropic.APIStatusError, anthropic.APIConnectionError, TimeoutError, _NonSchemaStopReason); a refusal/max_tokens stop_reason is wrapped into _NonSchemaStopReason so it triggers the corrective retry (Pitfall 2). Any other exception type is NOT retried."
  - "On exhaustion the retryable failure is re-raised as a typed LLMGenerationError (with __cause__) so ReadingService (Plan 05) runs the honest-fail path — NEVER a templated/fake reading (D-09)."
  - "GenerationResult carries output + model_name/input_tokens/output_tokens/latency_ms/stop_reason (latency via time.monotonic around the call) — the exact generation_logs row Plan 05 writes (ANALYTICS-02)."
  - "SafetyService.classify Stage 1 regex pre-filter returns crisis_sensitive instantly on high-signal RU/EN self-harm/violence terms (§20.2/§20.4) and normal for empty/whitespace/None (HOME-02) — both with NO API call (meta=None); Cyrillic stems matched as substrings (rich morphology), Latin terms with word boundaries."
  - "Stage 2 classify is ONE tiny messages.parse(model=claude-haiku-4-5, output_format=SafetyVerdict, temperature=0.0, max_tokens=64) — structured output, never json.loads of model text. The question is untrusted DATA inside the fixed system frame, not an instruction (T-04-15)."
  - "ClassifyResult.meta is None on the regex/empty short-circuit (no call → nothing to log) and otherwise carries model/tokens/latency, so Plan 05 writes a classify generation_logs row only when an actual call occurred (ANALYTICS-02)."
  - "Pure total route() maps every SafetyCategory to a SafetyAction (crisis→REFUSAL, abusive_or_manipulative→REDIRECT, {relationship,financial,health,legal}_sensitive→SAFETY_MODIFIER, normal→GENERATE); SafetyAction.continues_to_draw encodes the locked gate-before-draw boundary (D-03/04/05/06)."
  - "Both services are injectable (client passed to the constructor, default = singleton) so unit tests mock messages.parse with an AsyncMock — no network, no ANTHROPIC_API_KEY needed."

patterns-established:
  - "Injectable-client LLM service pattern (constructor default = core/llm_client singleton via local import) reused identically by LLMService and SafetyService — the mock seam for Plan 05 + tests."
  - "Stop-reason-as-retryable: convert a 200-OK-but-untrustworthy response into a typed retryable so one tenacity policy covers validation, transient API, timeout, and refusal/truncation uniformly."
  - "Pre-LLM regex gate + tiny enum-only structured classify: the cheapest design that honors 'classify before draw/charge' with a pure, client-free fast path."

requirements-completed: [READ-03, READ-04, SAFE-01, SAFE-02, SAFE-04, SAFE-05]

# Metrics
duration: 25min
completed: 2026-06-13
---

# Phase 04 Plan 03: Anthropic Call Layer (LLMService + SafetyService) Summary

**The "how we talk to Claude" layer: `LLMService` wraps ONE `messages.parse(output_format=ReadingOutput)` in the locked resilience contract (one corrective Haiku→Sonnet retry + per-attempt timeout + usage/latency/stop_reason extraction, honest-fail on exhaustion — D-12/D-09), and `SafetyService` is the mandatory pre-draw gate (regex pre-filter that short-circuits crisis instantly + a tiny Haiku classify → `SafetyVerdict`, with a pure `route()` Plan 05 branches on). Both are fully unit-tested against a MOCKED `AsyncAnthropic` client — no real API call.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-06-13T14:50Z (approx)
- **Completed:** 2026-06-13T15:15Z
- **Tasks:** 2 (both TDD: RED → GREEN)
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments
- **`LLMService.generate(system, user_prompt) -> GenerationResult`** — wraps a single `await client.messages.parse(model=…, output_format=ReadingOutput, max_tokens=1500, temperature=0.7, timeout=20.0)` in `tenacity.AsyncRetrying` (`stop_after_attempt(2)`, `wait_fixed(0.5)`, `reraise=True`). Attempt 1 runs on `claude-haiku-4-5`; the one corrective retry escalates to `claude-sonnet-4-6` (D-12), keyed off `retry_state.attempt_number`. Reads `response.parsed_output` (raises `ValidationError` on a schema mismatch), guards `stop_reason` (`refusal`/`max_tokens` → internal retryable), and extracts `usage.input_tokens/output_tokens`, monotonic-clock `latency_ms`, the resolved model alias, and `stop_reason` onto a frozen `GenerationResult`. On exhaustion it raises a typed `LLMGenerationError` (with `__cause__`) so Plan 05 honest-fails — never a templated reading (D-09).
- **`SafetyService.classify(question) -> ClassifyResult`** — Stage 1 is a pure compiled RU/EN crisis regex that returns `crisis_sensitive` instantly (and `normal` for empty/whitespace/`None`, HOME-02) with **no** API call (`meta=None`). Stage 2, for undecided questions, makes ONE tiny `messages.parse(model="claude-haiku-4-5", output_format=SafetyVerdict, temperature=0.0, max_tokens=64)` and returns its verdict plus a `ClassifyCallMeta` (model/tokens/latency) for the `generation_logs` row.
- **Pure `route(verdict) -> SafetyAction`** — total mapping over all 7 §20.4 categories: `crisis→REFUSAL`, `abusive_or_manipulative→REDIRECT`, `{relationship,financial,health,legal}_sensitive→SAFETY_MODIFIER`, `normal→GENERATE`. `SafetyAction.continues_to_draw` encodes the locked gate-before-draw boundary (D-03/04/05/06) Plan 05 branches on.
- **Tests:** `test_llm_service.py` (8 behaviours) + `test_safety_routing.py` (21 behaviours, Wave-0 skip removed), all against a mocked `AsyncAnthropic` — **no network**. Full unit suite green (72 passed).

## Task Commits

Each task was committed atomically (TDD: written RED → implemented GREEN within one cohesive commit per task):

1. **Task 1: LLMService — messages.parse + tenacity 1-retry (Haiku→Sonnet) + usage extraction** — `370a317` (feat)
2. **Task 2: SafetyService — regex pre-filter + Haiku classify → SafetyVerdict + routing** — `3bfa7b7` (feat)

**Plan metadata:** _(this SUMMARY + STATE/ROADMAP commit follows)_

## Files Created/Modified
- `backend/app/services/llm.py` — `LLMService` (injectable client), `GenerationResult` frozen dataclass, `LLMGenerationError`, `RETRYABLE`, model aliases `HAIKU_MODEL`/`SONNET_MODEL`, tunable `MAX_TOKENS`/`TEMPERATURE`/`ATTEMPT_TIMEOUT_SECONDS`/`MAX_ATTEMPTS`/`RETRY_WAIT_SECONDS` constants, internal `_NonSchemaStopReason` retry trigger.
- `backend/app/services/safety.py` — `SafetyService` (injectable client), pure `route()` + `SafetyAction` enum (with `continues_to_draw`), `_regex_prefilter` + compiled `_CRISIS_REGEX` (RU/EN), the §20.4 `_CLASSIFY_SYSTEM` instruction, `CLASSIFY_MODEL` alias + tunable classify constants.
- `backend/tests/unit/test_llm_service.py` — success-first-Haiku, corrective-retry-to-Sonnet, exhausted-reraises, usage/metadata-extracted, refusal-stop-triggers-retry, non-retryable-not-retried, alias-not-dated-snapshot, RETRYABLE-types (8 tests, mocked client).
- `backend/tests/unit/test_safety_routing.py` — regex-crisis-no-call (×4), empty-normal-no-call (×4), undecided-calls-classify, classify-uses-structured-output, routing-actions (×7), route-covers-every-category, normal→generate, sensitive-continues, structured-output-not-json-loads (21 tests; Wave-0 skip removed).

## Decisions Made
- **One call, one corrective retry, model escalation only (D-12).** `tenacity.AsyncRetrying` picks the model from `retry_state.attempt_number` (Haiku → Sonnet); no corrective prompt-turn (RESEARCH A4 baseline). Aliases only; the alias string is what gets logged (CLAUDE.md anti-pattern: no dated snapshot).
- **Refusal/truncation is a retry trigger, not a success (Pitfall 2).** A `refusal`/`max_tokens` `stop_reason` is wrapped into `_NonSchemaStopReason` (in `RETRYABLE`) so the corrective Sonnet attempt fires, rather than returning an untrustworthy reading.
- **Exhaustion raises a typed `LLMGenerationError` (D-09).** The real exception is preserved as `__cause__` for the server-side log; Plan 05 catches the typed error to mark `failed`, keep the limit, and return the soft §9.8 copy — no fake/templated output.
- **Crisis is caught for free before any call (D-03).** The regex pre-filter short-circuits the highest-signal self-harm/violence terms instantly (`meta=None`); the Haiku classify covers the nuanced rest. This is the only design that honors "gate before draw/charge".
- **Structured output, never `json.loads` (CLAUDE.md).** The classify call uses `output_format=SafetyVerdict` (constrained decoding → a valid enum member); the question is untrusted data inside the fixed §20.4 system frame, not an instruction (T-04-15).
- **`meta=None` distinguishes the no-call path.** Plan 05 writes a `classify` `generation_logs` row only when `meta is not None` (an actual call) — the regex/empty short-circuit logs nothing (ANALYTICS-02).
- **Both services injectable.** Constructor takes the `AsyncAnthropic` client (default = `core/llm_client` singleton via a local import so module import never constructs a client); tests pass a fake whose `messages.parse` is an `AsyncMock`.

## Deviations from Plan

None — plan executed exactly as written. (No bugs, missing-critical, blocking, or architectural triggers fired; deviation Rules 1–4 not invoked. Both auto-fixes below were within-task test refinements before each task's commit, not plan deviations.)

## Issues Encountered
- **`ruff` UP037 on a quoted type annotation.** With `from __future__ import annotations`, the `"AsyncAnthropic | None"` string annotation on `LLMService.__init__` was flagged as redundantly quoted. Unquoted it (annotations are deferred at runtime; the `TYPE_CHECKING` import covers static checkers). Within Task 1, before its commit.
- **`json.loads` anti-pattern grep tripped on the docstring.** The Task 2 source-scan test asserted the bare phrase `json.loads` was absent, but `safety.py`'s docstring legitimately names the anti-pattern ("never prompt-and-`json.loads`"). Tightened the assertion to the call form `json.loads(` (what actually matters) — the implementation uses structured output and contains no such call. Within Task 2, before its commit.

## User Setup Required
None — no external service configuration required. Both services run fully against a mocked client in tests; the live `ANTHROPIC_API_KEY` (already a required secret in `core/config.py`, set to a dummy in `tests/conftest.py`) is only exercised by Plan 05's real run, not by these unit tests.

## Next Phase Readiness
- The two call-layer services Plan 05 composes inside `ReadingService` in the locked gate→draw→generate→consume order are ready: `SafetyService.classify`/`route` (the pre-draw gate) and `LLMService.generate` (the resilient single call with the honest-fail signal). Both expose the exact `generation_logs` audit fields (ANALYTICS-02).
- `GenerationResult` and `ClassifyResult.meta` map 1:1 onto the `generation_logs` columns; `LLMGenerationError` is the typed seam for D-09; `SafetyAction.continues_to_draw` is the branch Plan 05 gates the draw on.
- No blockers introduced. No new dependencies (`anthropic` 0.109.1 + `tenacity` already present in the uv venv from the Wave-0/04-01 setup).

## Self-Check: PASSED

- Files verified present: `backend/app/services/llm.py`, `backend/app/services/safety.py`, `backend/tests/unit/test_llm_service.py`, `backend/tests/unit/test_safety_routing.py`, this SUMMARY.
- Commits verified in git history: `370a317` (Task 1), `3bfa7b7` (Task 2).
- Target tests green: `uv run pytest -q tests/unit/test_llm_service.py tests/unit/test_safety_routing.py` → 29 passed; full unit suite → 72 passed.
- Ruff clean: `uv run ruff check app/services/llm.py app/services/safety.py` → 0.
- Grep: `llm.py` contains `messages.parse`, `stop_after_attempt(2)`, `retry_if_exception_type`, `reraise=True`, `claude-haiku-4-5` AND `claude-sonnet-4-6`; **no** dated `-YYYYMMDD` snapshot. `safety.py` contains `output_format=SafetyVerdict` and `SafetyCategory`; **no** `json.loads(` call.

---
*Phase: 04-real-personal-reading-keystone*
*Completed: 2026-06-13*
