---
phase: 04-real-personal-reading-keystone
plan: 01
subsystem: api
tags: [anthropic, tenacity, pydantic, structured-outputs, safety-classifier, pytest, fastapi]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: "readings/reading_cards/generation_logs models, ANTHROPIC_API_KEY config secret, seed loader (run_seed), pytest substrate (ASGITransport client + isolated session + make_init_data)"
  - phase: 03-the-ritual-mock
    provides: "frontend MockReading/MockReadingCard/MockReadingSummary contract + canonical SAFE-06 BANNED_BRAND_TOKENS the backend mirrors"
provides:
  - "anthropic + tenacity dependencies pinned, locked (uv.lock), and importable"
  - "schemas/reading.py: fused single-call LLM output contract (ReadingOutput/CardInterpretation/ReadingSummary)"
  - "classify contract: SafetyCategory (7×§20.4) + SafetyVerdict + ClassifyResult/ClassifyCallMeta"
  - "request/response contract: ReadingCreate (HOME-01/02 validation) + ReadingOut mirroring frontend MockReading"
  - "core/llm_client.py: module-level AsyncAnthropic singleton (env key, never logged)"
  - "Wave-0 test substrate: fake_llm/fake_safety/fake_reading_output/seeded_catalog fixtures + 8 skipped stubs"
affects: [04-02, 04-03, 04-04, 04-05, 04-06]

# Tech tracking
tech-stack:
  added: ["anthropic>=0.69,<1 (0.109.1)", "tenacity>=9,<10 (9.1.4)"]
  patterns:
    - "LLM-output length target lives in Field(description), NEVER max_length (SDK strips length constraints — Pitfall 1)"
    - "Injectable FakeLLM/FakeSafety service stand-ins so integration tests never hit Anthropic; substituted later via app.dependency_overrides"
    - "seeded_catalog reuses run_seed inside the savepoint transaction (one source of truth, rolled back per test)"

key-files:
  created:
    - backend/app/schemas/reading.py
    - backend/app/core/llm_client.py
    - backend/tests/unit/test_reading_schema.py
    - backend/tests/unit/test_card_draw.py
    - backend/tests/unit/test_safety_routing.py
    - backend/tests/unit/test_brand_guard.py
    - backend/tests/integration/test_readings_auth.py
    - backend/tests/integration/test_readings_flow.py
    - backend/tests/integration/test_readings_limit.py
    - backend/tests/integration/test_safety_gate.py
    - backend/tests/integration/test_generation_logs.py
    - backend/uv.lock
  modified:
    - backend/pyproject.toml
    - backend/app/schemas/__init__.py
    - backend/tests/integration/conftest.py

key-decisions:
  - "Three §17/§18 LLM fields without a dedicated DB column (soft_advice/attention_point/closing_phrase/connection) are carried in the schema and persisted later via the lossless mapping (RESEARCH Pattern 1, A1); ReadingOut surfaces all five summary fields named to mirror the frontend MockReading shape"
  - "ReadingCreate.question is server-side validated (HOME-01 10–500, HOME-02 empty→None) on the request model — distinct from the LLM output_format where length must NOT be a constraint"
  - "SafetyCategory is a StrEnum mirroring app.models.enums style (lowercase slug values); ClassifyResult/ClassifyCallMeta added so the gate's regex-fast-path vs API-call distinction + generation_logs metadata have a typed home"

patterns-established:
  - "Pattern 1: LLM-output schemas put the length/shape target in Field(description) only — never max_length/min_length (the Anthropic SDK strips them; constrained decoding would ignore them)"
  - "Pattern 2: FakeLLM(output, raise_times=N) + FakeSafety(category=...) are injectable async stand-ins; FakeLLM.calls / FakeSafety.calls let a test assert gate-before-draw ordering with zero network"
  - "Pattern 3: seeded_catalog reuses run_seed in the auth_session savepoint so the flow draws from real catalog rows; skips cleanly when Postgres is down"

requirements-completed: [READ-03, READ-05, READ-06, SAFE-01]

# Metrics
duration: 8min
completed: 2026-06-13
---

# Phase 04 Plan 01: Wave-0 Foundation (contracts + LLM client + test substrate) Summary

**Single-call `ReadingOutput`/classify/request-response contracts in `schemas/reading.py`, an `AsyncAnthropic` singleton, the human-approved `anthropic`+`tenacity` deps, and the `fake_llm`/`fake_safety`/`seeded_catalog` substrate + 8 skipped stubs every later Phase-4 plan composes on.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-06-13T10:16:37Z
- **Completed:** 2026-06-13T10:24:43Z
- **Tasks:** 3
- **Files modified:** 14 (12 created, 3 modified — `pyproject.toml`/`schemas/__init__.py`/`integration/conftest.py`; `uv.lock` generated)

## Accomplishments
- Added the two MISSING locked dependencies (`anthropic>=0.69,<1` → 0.109.1, `tenacity>=9,<10` → 9.1.4) behind the human-approved legitimacy gate, with an aiogram-style provenance comment; refreshed `uv.lock`; `python -c "import anthropic, tenacity; from anthropic import AsyncAnthropic"` exits 0.
- Defined the fused single-call LLM output contract (`ReadingOutput`/`CardInterpretation`/`ReadingSummary`) where the §17 length target lives in field descriptions only — the validation seam Plan 03's corrective-retry depends on round-trips and rejects bad shapes.
- Defined the classify contract (`SafetyCategory` with exactly the 7 §20.4 members + `SafetyVerdict`) and the request/response contract (`ReadingCreate` with HOME-01/02 validation; `ReadingOut` mirroring the frontend `MockReading` shape so Plan 06's seam is mechanical).
- Created the `AsyncAnthropic` singleton that reads `ANTHROPIC_API_KEY` from env via the SDK default — never passed explicitly, never logged (T-04-10).
- Built the deterministic Wave-0 substrate: `fake_reading_output`/`fake_llm`/`fake_safety`/`seeded_catalog` fixtures (none touch the network) + 8 skipped stubs that collect clean; full suite green (35 passed, 47 skipped, 0 collection errors).

## Task Commits

Each task was committed atomically:

1. **Task 1: Package legitimacy gate + add anthropic + tenacity to pyproject** — `26084f9` (chore) + `f3b1564` (chore, uv.lock)
2. **Task 2: Schema contracts + AsyncAnthropic client singleton** — `4eb8585` (feat)
3. **Task 3: Wave-0 test stubs (8) + fake_llm/fake_safety/seeded_catalog fixtures** — `f349e3a` (test)

**Plan metadata:** committed with this SUMMARY (docs).

## Files Created/Modified
- `backend/pyproject.toml` — added `anthropic>=0.69,<1` + `tenacity>=9,<10` with provenance comment (mirrors aiogram precedent).
- `backend/uv.lock` — resolved lockfile pinning the new deps + transitive (distro, docstring-parser, jiter, sniffio).
- `backend/app/schemas/reading.py` — LLM output (`ReadingOutput`/`CardInterpretation`/`ReadingSummary`), classify (`SafetyCategory`/`SafetyVerdict`/`ClassifyResult`/`ClassifyCallMeta`), request/response (`ReadingCreate`/`ReadingOut`/`ReadingCardOut`/`ReadingSummaryOut`).
- `backend/app/schemas/__init__.py` — re-exports the reading contracts.
- `backend/app/core/llm_client.py` — module-level `AsyncAnthropic()` singleton.
- `backend/tests/unit/test_reading_schema.py` — born-green (6 tests): roundtrip, bad-shape rejection, length-in-description-not-constraint, 7 safety categories, HOME-01/02 bounds, frontend-shape mirror.
- `backend/tests/integration/conftest.py` — `fake_reading_output`/`FakeLLM`+`fake_llm`/`FakeSafety`+`fake_safety`/`seeded_catalog`.
- 8 skipped Wave-0 stubs (unit: `test_card_draw`, `test_safety_routing`, `test_brand_guard`; integration: `test_readings_auth`, `test_readings_flow`, `test_readings_limit`, `test_safety_gate`, `test_generation_logs`) — each docstring names its requirement ID + owning plan.

## Decisions Made
- **LLM-field overflow carried in schema, mapped losslessly later (RESEARCH A1):** `soft_advice`/`attention_point`/`closing_phrase`/`connection` have no dedicated DB column; the contract keeps them and `ReadingOut` surfaces all five summary fields under the frontend names (`linkage`/`main_factor`/`attention`/`soft_advice`/`closing_phrase`) so the Plan-06 mapping is mechanical. Persistence mapping is Plan 05's to wire.
- **`ClassifyResult`/`ClassifyCallMeta` added beyond the literal plan list:** the plan named `SafetyCategory`/`SafetyVerdict`; I added two small typed companions so the gate's "regex fast-path (no call) vs API classify call" distinction and the per-call `generation_logs` metadata (ANALYTICS-02) have a home in the contract module rather than being invented ad hoc in Plan 03/05. Additive, no behavior, fully within the classify-contract intent.
- **`protected_namespaces=()` on `ClassifyCallMeta`:** allows a plain `model_name` field (mirroring `generation_logs.model_name`) without Pydantic's `model_`-prefix warning.

## Deviations from Plan

None — plan executed exactly as written. (Task 1's blocking package-legitimacy checkpoint was pre-approved by the user before this run; both deps installed cleanly and import. The two extra typed companions in Task 2 are documented above as a decision, not a deviation — they add no behavior and stay within the stated classify-contract scope.)

## Issues Encountered
- **System Python lacks pytest/anthropic; the project uses a `uv` venv.** The first `python -m pytest` reported "No module named pytest" (exit 0, misleading). Resolved by running all verification through `uv run pytest` / `uv run ruff` / `uv run python`, which targets the project venv where the deps are installed. No code impact.
- **Pre-existing `InsecureKeyLengthWarning`** in `tests/unit/test_initdata.py` (test JWT secret < 32 bytes) surfaces in the full-suite run. Out of scope (not caused by this plan's changes); left untouched.

## Environment Notes
- **Docker/Postgres not available in this sandbox.** The 5 integration stubs (and the existing DB-dependent integration tests) skip cleanly via the root conftest `_db_ready` pattern, so `pytest -q` is green and fully collectable without `docker compose up`. The `seeded_catalog` fixture will run `run_seed` against a live test DB when Postgres is present.
- **`uv pip install -e ".[dev]"` succeeded in-sandbox** and installed `anthropic==0.109.1` + `tenacity==9.1.4` (within the pinned floors), so no install-sandbox limitation applies — the human does not need to re-install, though `uv sync` locally will reconcile against the committed `uv.lock`.

## Known Stubs
The 8 Wave-0 test files are **intentional skipped stubs** — this plan's explicit deliverable (the Nyquist substrate). Each carries `@pytest.mark.skip(reason="Wave 0 stub — implemented in Plan 04-0X")` and a docstring naming its requirement + owning plan. They are NOT goal-blocking: this plan's goal is the contracts + substrate, which are complete and green. Resolution owners:

| Stub | Requirement | Resolved in |
|------|-------------|-------------|
| `tests/unit/test_card_draw.py` | READ-02 | Plan 04-02 |
| `tests/unit/test_brand_guard.py` | SAFE-06 (backend) | Plan 04-02 |
| `tests/unit/test_safety_routing.py` | SAFE-01/02/04/05 | Plan 04-03 |
| `tests/integration/test_readings_auth.py` | READ-01 | Plan 04-05 |
| `tests/integration/test_readings_flow.py` | READ-03/04/05/06 | Plan 04-05 |
| `tests/integration/test_readings_limit.py` | READ-10 | Plan 04-05 |
| `tests/integration/test_safety_gate.py` | SAFE-03 / D-06 | Plan 04-05 |
| `tests/integration/test_generation_logs.py` | ANALYTICS-02 | Plan 04-05 |

## User Setup Required
None — `ANTHROPIC_API_KEY` is already a required config secret (Phase 1, INFRA-04) and present in the test env; no new secret or dashboard config introduced by this plan.

## Next Phase Readiness
- The interface-first wave is complete: Plans 02–06 can import `ReadingOutput`/`SafetyVerdict`/`ReadingCreate`/`ReadingOut`/`SafetyCategory` and run against `fake_llm`/`fake_safety`/`seeded_catalog` without ever touching Anthropic.
- Plan 02 (CardDrawService + backend brand guard) and Plan 03 (SafetyService + PromptEngine) can begin immediately; Plan 05 (ReadingService orchestration) is the consumer of the fixtures + stubs.
- No blockers. The single hard prerequisite (the two missing packages) is cleared.

## Self-Check: PASSED

All 14 created files verified present on disk; all 4 task commits (`26084f9`, `f3b1564`, `4eb8585`, `f349e3a`) verified in git history.

---
*Phase: 04-real-personal-reading-keystone*
*Completed: 2026-06-13*
