---
phase: 04-real-personal-reading-keystone
plan: 05
subsystem: api
tags: [reading-service, orchestration, anthropic, structured-outputs, safety-gate, generation-logs, honest-fail, keystone]

# Dependency graph
requires:
  - phase: 04-01
    provides: ReadingCreate/ReadingOut + ReadingOutput/CardInterpretation/ReadingSummary + SafetyVerdict/ClassifyResult contracts; seeded_catalog/fake_llm/fake_safety fixtures
  - phase: 04-02
    provides: CardDrawService.draw → frozen DrawnCard records; core/brand_guard SAFE-06 ban-list port
  - phase: 04-03
    provides: SafetyService.classify (ClassifyResult) + route() → SafetyAction (continues_to_draw boundary); LLMService.generate(system, user_prompt) → GenerationResult; typed LLMGenerationError
  - phase: 04-04
    provides: PromptEngine.build → PromptBundle (system + user + prompt_version); refusal_copy / redirect_copy resolvers
provides:
  - ReadingService.create_reading — the gate→draw→generate→consume keystone orchestration (owns the AsyncSession transaction + ordering + generation_logs + honest-fail)
  - POST /api/readings thin router (Bearer JWT, ReadingCreate→ReadingOut), mounted under /api beside decks/spreads
  - get_reading_service dependency seam (tests inject a fakes-backed ReadingService via app.dependency_overrides)
  - seeded_catalog now synthesizes the deck_cards style layer (the seed JSON omits it) so the backend-only draw has an active pool
affects: [04-06, frontend-createReading-seam, reading-history-phase-5, payments-limit-phase-6]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ReadingService owns the transaction + the LOCKED order; collaborators injected via constructor params (default = real services) — the same seam tests use to pass FakeSafety/FakeLLM"
    - "Adapter seams (_normalize_classify / _unpack_generation) tolerate BOTH the real services (ClassifyResult / GenerationResult) and the bare-value test fakes (SafetyVerdict / ReadingOutput) through one injection point"
    - "Single ReadingOutput mapped onto DB BY position_index (Pitfall 3); soft_advice folded into reading_cards.interpretation; full ReadingSummary JSON serialized losslessly into readings.summary_full"
    - "Limit consumed in EXACTLY one place (the success branch, before commit); every non-success exit returns a soft 200 body with status set and the limit untouched"
    - "Crisis/abusive persist a FAILED parent reading FIRST so the NOT-NULL generation_logs.reading_id FK holds before any classify log row"

key-files:
  created:
    - backend/app/services/reading.py
    - backend/app/api/readings.py
  modified:
    - backend/app/services/__init__.py
    - backend/app/main.py
    - backend/tests/integration/conftest.py
    - backend/tests/integration/test_readings_flow.py
    - backend/tests/integration/test_readings_limit.py
    - backend/tests/integration/test_safety_gate.py
    - backend/tests/integration/test_generation_logs.py
    - backend/tests/integration/test_readings_auth.py

key-decisions:
  - "Honest fail (D-09) returns a deliberate 200 soft body with status=failed and the §9.8 copy carried in summary.soft_advice — NEVER a 500 and NEVER a templated stand-in reading (no base-meaning assembly)"
  - "soft_advice / connection / attention_point / closing_phrase have no dedicated DB column → soft_advice folds into reading_cards.interpretation; the FULL ReadingSummary is JSON-serialized into readings.summary_full (lossless, no migration) and read back to build all five §14.5 summary fields"
  - "One generation_logs row per ACTUAL LLM call: a classify row ONLY when classify() returned a non-None call-meta (regex/empty short-circuit makes none), plus one row per generation outcome (LLMService.generate encapsulates the corrective retry and surfaces a single terminal result → one completed row, or one failed row on exhaustion)"
  - "get_reading_service dependency is the router's injection seam; the service stays constructor-injectable so the bot (Phase 7) can call it directly"

patterns-established:
  - "Pattern: thin router delegates to ReadingService; ReadingInputError → 404; no-quota/refusal/redirect/honest-fail are soft 200 bodies from the service, not errors"
  - "Pattern: user derived ONLY from get_current_user (JWT sub) — user_id is not a ReadingCreate field and is ignored (T-04-23)"
  - "Pattern: card names + position titles in the response come from the persisted reading_cards + the spread (authoritative server-side), NOT the model echo"

requirements-completed: [READ-01, READ-03, READ-04, READ-05, READ-06, READ-10, READ-11, SAFE-01, SAFE-02, SAFE-03, ANALYTICS-02]

# Metrics
duration: 55min
completed: 2026-06-13
---

# Phase 4 Plan 5: Reading Service Keystone Composition Summary

`ReadingService.create_reading()` wires CardDrawService + SafetyService + PromptEngine + LLMService + the SAFE-06 brand guard + persistence + `generation_logs` + the weekly limit into the LOCKED order, then exposes it behind the thin Bearer-gated `POST /api/readings` router — the moment the Core Value goes live end-to-end on the backend.

## What was built

**`backend/app/services/reading.py` — the keystone orchestration.** `create_reading(session, user, req)` owns the `AsyncSession` transaction and executes the RESEARCH System-Architecture order EXACTLY:

1. **limit check** — read `user_limits`; no quota → soft §9.8 paywall body, NO draw (Phase-4 scope = "has quota?" + "consume on success"; weekly reset/buckets are Phase 6);
2. **SAFETY GATE — BEFORE any draw/charge** (`SafetyService.classify` + `route`): crisis → seeded refusal copy, abusive → seeded redirect copy (both: persist a FAILED parent reading first so the NOT-NULL `generation_logs.reading_id` FK holds, log classify only when a real call was made, NO draw, NO generation, limit kept); `*_sensitive` → `SAFETY_MODIFIER` flag + continue (D-05); normal → continue;
3. **CSPRNG draw** → persist `readings` (PENDING) + the immutable `reading_cards`; log the classify call (if one was made) against the now-existing reading;
4. **PromptEngine.build** → `(system, user, prompt_version)`; set `readings.prompt_version`;
5. status=GENERATING; ONE `LLMService.generate` call; on `LLMGenerationError` → HONEST FAIL (status=FAILED, truncated `generation_error` server-side, final failed log row, NO consume, NO templated stand-in, soft §9.8 body);
6. **brand guard** over the generated text → LOG+FLAG only (never fails the reading);
7. **persist the mapping** — each `CardInterpretation` matched BY `position_index` (Pitfall 3) → `reading_cards.short_meaning/interpretation/mystical_accent` (`soft_advice` folded into `interpretation`); `readings.summary_short/main_factor/advice` + the full `ReadingSummary` JSON into `summary_full`; `model_name`/`completed_at`; status=COMPLETED;
8. **consume the limit in EXACTLY this one place** — `free_used_this_week += 1` (Pitfall 4);
9. commit; return `ReadingOut` with per-card names/orientations authoritative from the persisted rows + the spread, all five §18 summary fields, and `remaining_limits`.

Collaborators are injected via constructor params defaulting to the real services. Two adapter seams keep the injection point clean: `_normalize_classify` accepts either a real `ClassifyResult` or a bare `SafetyVerdict` (the test fake) and `_unpack_generation` accepts either a real `GenerationResult` or a bare `ReadingOutput` — so `FakeSafety`/`FakeLLM` plug in through the same seam with no real Anthropic call.

**`backend/app/api/readings.py` — the thin router.** Mirrors `decks.py`/`spreads.py`: `POST /api/readings` (`response_model=ReadingOut`), Bearer JWT via `get_current_user`, `ReadingCreate` body validation, delegates ALL orchestration to `ReadingService.create_reading`, maps `ReadingInputError` → 404. The user is derived ONLY from the JWT (never the body). The `ReadingService` arrives via a `get_reading_service` dependency so tests inject a fakes-backed service through `app.dependency_overrides`. Mounted in `main.py` under `/api` beside decks/spreads; exported from `services/__init__.py`.

**Integration tests (Wave-0 stubs replaced).** `test_readings_flow` (success / honest-fail / corrective-retry), `test_readings_limit` (consume-once-on-success + unchanged on no-quota / crisis / abusive / honest-fail), `test_safety_gate` (crisis & abusive short-circuit before draw with zero `reading_cards`; sensitive continues), `test_generation_logs` (one row per actual LLM call; classify row only when a call was made; failed-attempt row), `test_readings_auth` (401 without Bearer, 422 on bad body, 200 + ReadingOut, body `user_id` ignored). All drive `FakeSafety`/`FakeLLM` against `seeded_catalog`, never the real Anthropic API.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `seeded_catalog` never created `deck_cards` — the backend-only draw had no pool**
- **Found during:** Task 1 (offline verification of `create_reading`).
- **Issue:** `app.seed.loader.run_seed` (which `seeded_catalog` reuses) seeds the 78 universal `cards` but NOT the `deck_cards` style layer — per `app/seed/data/_gen_cards.py` deck imagery is "a later content task". But `CardDrawService.draw` selects from the active deck's `deck_cards`, so the draw raised `deck … has 0 active cards`. This also silently blocks the prior-wave `test_card_draw_db.py` draw tests (they share `seeded_catalog`; they only ever ran skipped because Postgres is down).
- **Fix:** Added `_ensure_deck_cards(session)` to `tests/integration/conftest.py` and called it from `seeded_catalog` — synthesizes one active, style-free `deck_cards` row per (active deck, card) pair (placeholder imagery, no deck-specific meaning; the universal meaning stays on `cards`). Idempotent within a test.
- **Files modified:** `backend/tests/integration/conftest.py`
- **Commit:** d47b10f

**2. [Rule 1 - Bug] Seeded `spread_positions.position_index` is 1-based, not 0-based**
- **Found during:** Task 1 (offline verification — the index-set validator tripped: model returned `[0,1,2]` ≠ drawn `[1,2,3]`).
- **Issue:** `CardInterpretation.position_index`'s field description says "0-based", but the seed data (`spreads.json`) numbers positions 1..N. The conftest `fake_reading_output` fixture builds indices `range(3)` (0,1,2), which would never match a drawn `[1,2,3]` and would (incorrectly) push every success path into the honest-fail branch.
- **Fix:** The service is CORRECT to reject a mismatched index set (RESEARCH Pitfall 3 — match by index, not order; a wrong set is a bad shape → retry/honest-fail). The tests were made robust instead of hardcoding either base: a `_spread_position_indices()` helper reads the actual seeded indices and `_output_for_indices()` builds a matching `ReadingOutput`, so the fake output always echoes the drawn indices. No production code changed — the discovery hardened the tests against the seed's indexing.
- **Files modified:** `backend/tests/integration/test_readings_flow.py` (+ imports in the other three flow-driven test files)
- **Commit:** d47b10f

## Verification & Environment Note

- `uv run pytest -q` → **82 passed, 49 skipped, 0 errors/failures** (clean collection; the integration tests skip cleanly because Postgres is unreachable in this environment — the Wave-0 convention).
- `uv run ruff check app/services/reading.py app/api/readings.py app/main.py` → **0**.
- **The integration tests REQUIRE Postgres and SKIP here** (no Docker/PG available). To gain real confidence without the stack, the full orchestration AND the HTTP path were exercised against an ephemeral **in-memory SQLite** DB (PG-only `ARRAY`/`JSONB`/`UUID` types neutralized for SQLite via temporary compiler/processor shims; the real models, real `run_seed`, real `conftest._ensure_deck_cards`, real `ReadingService`, real router, and the real auth flow). All paths passed:
  - **SUCCESS** → completed, 3 cards, `remaining_limits=2`, `summary_full` populated, authoritative card name + position title, `soft_advice` folded into interpretation;
  - **CRISIS** → failed, 0 cards, 0 `reading_cards`, 0 LLM calls, limit kept (gate ran before the draw);
  - **HONEST FAIL** → failed, limit kept, `generation_error` set, `summary_full=None` (no stand-in), one `failed` log row;
  - **CORRECTIVE RETRY** → completed via Sonnet escalation (`model_name=claude-sonnet-4-6`), limit consumed once;
  - **NO QUOTA** → soft paywall body, empty `reading_id`, 0 LLM calls, limit unchanged;
  - **CLASSIFY LOG** → both `classify` + `completed` rows when a real classify call was made;
  - **HTTP**: no-Bearer → 401, bad body / missing slug → 422, valid → 200 + ReadingOut, forged body `user_id` → ignored (200), unknown deck → 404.
  The SQLite shims were temporary verification scaffolding and were removed — they are NOT committed.
- **Human-verifiable once the stack is up:** run `cd backend && alembic upgrade head && uv run pytest -q tests/integration/test_readings_flow.py tests/integration/test_readings_limit.py tests/integration/test_safety_gate.py tests/integration/test_generation_logs.py tests/integration/test_readings_auth.py` against a live Postgres — all should pass (not skip).

## Notes for Plan 06 (the frontend seam swap)

- `ReadingOut` carries every field the existing result screen renders: per-card `name`/`position_title`/`orientation`/`short_meaning`/`interpretation`/`deck_accent` + summary `linkage`/`main_factor`/`attention`/`soft_advice`/`closing_phrase` + `remaining_limits`. The Plan-06 mapping onto `MockReading` is mechanical (`linkage`←connection, `attention`←attention_point, etc.).
- On the soft paths (paywall / refusal / redirect / honest-fail) `status="failed"`, `cards=[]`, and the human in-character copy rides in `summary.soft_advice` — the frontend's «Колода замолчала…» + Повторить/Сменить колоду UX (D-08) reads it there.

## Self-Check: PASSED

- Created files exist: `backend/app/services/reading.py`, `backend/app/api/readings.py`, `.planning/phases/04-real-personal-reading-keystone/04-05-SUMMARY.md`.
- Per-task commits exist: `d47b10f` (Task 1 — ReadingService + tests), `d72a2ed` (Task 2 — router + auth tests).
