---
phase: 04-real-personal-reading-keystone
plan: 04
subsystem: api
tags: [prompt-engineering, anthropic, structured-outputs, prompt-templates, safety, seed]

# Dependency graph
requires:
  - phase: 04-01
    provides: ReadingOutput/CardInterpretation/ReadingSummary contracts + SafetyCategory/SafetyVerdict + seeded_catalog/fake_llm fixtures
  - phase: 04-02
    provides: CardDrawService.DrawnCard records + brand_guard SAFE-06 ban-list port
  - phase: 04-03
    provides: SafetyService.SafetyAction routing + LLMService.generate(system, user_prompt) call shape
provides:
  - PromptEngine.build → fused single-call PromptBundle (system + user + prompt_version) eliciting the full ReadingOutput
  - Pure assembly helpers (build_system_block / build_user_block / compose_prompt_version) testable without a DB
  - D-02 mandatory per-deck signature seeded into all 6 deck_modifier rows (v2)
  - Generic D-04 crisis-refusal copy (no region/phone) + D-06 abusive-redirect copy (single source, admin-editable)
  - refusal_copy / redirect_copy resolvers for the crisis/abusive branches Plan 05 short-circuits to
affects: [04-05, reading-service, generation_logs, prompt-version-control]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure string-assembly helpers + thin async DB wrapper (most assertions need no Postgres)"
    - "prompt_version composed from active template type@version fields for the audit trail (ANALYTICS-02)"
    - "Deck-specific style (deck_cards) lifted into a frozen DeckCardStyle so the user-block builder stays DB-free"

key-files:
  created:
    - backend/app/services/prompt_engine.py
    - backend/tests/unit/test_prompt_engine.py
  modified:
    - backend/app/seed/data/prompts.json

key-decisions:
  - "Redirect copy (D-06) seeded as a safety-type prompt_templates row (slug 'redirect'), not a module constant — admin-editable, consistent with prompt-version control"
  - "prompt_version format = '<type>@<version>+...' in fixed order (system+deck_modifier+single_card+final_summary[+safety])"
  - "Orientation selects which universal meaning/keywords + which deck-specific modifier the per-card block injects"
  - "An absent active template raises ValueError (surfaced misconfiguration) — never a silently degraded prompt"

patterns-established:
  - "Pattern: PromptEngine.build reads ACTIVE prompt_templates by slug (mirrors catalog.py select(), no f-string SQL, no lazy load) and delegates to pure helpers"
  - "Pattern: each per-card block is anchored by position_index and the model is required to echo it (RESEARCH Pitfall 3)"
  - "Pattern: safety §20.3 fragment appended ONLY when safety_action == SAFETY_MODIFIER (D-05/SAFE-02)"

requirements-completed: [READ-03, READ-05, READ-06, READ-11, SAFE-02, SAFE-03, SAFE-04, SAFE-05]

# Metrics
duration: 30min
completed: 2026-06-13
---

# Phase 4 Plan 04: PromptEngine + Core-Value Prompt Content Summary

**Fused single-call PromptEngine that composes §16 system + §19 deck modifier (with a guaranteed D-02 signature) + §17 per-card context + §18 summary into one Russian, length-bounded, versioned `messages.parse` prompt — plus the seeded per-deck signatures, generic crisis refusal, and abusive-redirect copy that make "same question, different deck" guaranteed rather than emergent.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-13T15:00Z (approx)
- **Completed:** 2026-06-13
- **Tasks:** 2
- **Files modified:** 3 (1 created service, 1 created test, 1 edited seed)

## Accomplishments
- `PromptEngine.build` assembles ONE fused prompt (system §16 + the active `deck_modifier_<slug>` carrying the §19 tone AND the mandatory D-02 signature; user = one `position_index`-anchored §17 block per drawn card + the §18 summary instruction) that elicits the full `ReadingOutput`.
- The §20.3 safety fragment is appended **only** when the question is sensitive (`safety_action == SAFETY_MODIFIER`, D-05/SAFE-02); the prompt always restates Russian output (D-14) and the ≤140-char `short_meaning` target (D-10).
- `prompt_version` is composed from the active templates' `type@version` fields (e.g. `system@v1+deck_modifier@v2+single_card@v1+final_summary@v1`) → ready for `readings.prompt_version` + `generation_logs` (ANALYTICS-02 / T-04-22).
- All 6 `deck_modifier_*` rows now carry an explicit "Обязательная подпись колоды…" signature derived from their §19 tone (bumped to v2); the `refusal` row is generic D-04 wording (no region/phone, bumped to v2); a new `safety`-type `redirect` row carries the D-06 abusive redirect.
- Assembly logic lives in pure helpers — 9 unit tests cover the six locked behaviours with no DB and no network.

## Task Commits

Each task was committed atomically:

1. **Task 1: Seed content — D-02 signatures + generic D-04 refusal + D-06 redirect** - `4dfe5e1` (feat)
2. **Task 2: PromptEngine — fused prompt + safety modifier + prompt_version** - `d7b3cf1` (feat)

**Plan metadata:** _(this docs commit)_

## Files Created/Modified
- `backend/app/services/prompt_engine.py` - PromptEngine + PromptBundle + pure assembly helpers (`build_system_block`, `build_user_block`, `compose_prompt_version`) + `refusal_copy`/`redirect_copy` resolvers; reads active `PromptTemplate` rows, no hardcoded prompt text.
- `backend/tests/unit/test_prompt_engine.py` - 9 tests for the six `<behavior>` items (system signature, one block per card, safety-only-when-sensitive, Russian + ≤140, prompt_version, refusal/redirect copy) + orientation/general-reading/brand-safe extras; all DB-free.
- `backend/app/seed/data/prompts.json` - 6 deck_modifier signature sentences (v2), generic refusal (v2), new `redirect` row (safety type).

## Decisions Made
- **Redirect copy as a seeded `safety`-type row** (slug `redirect`), per the plan's preferred option — keeps the D-06 copy admin-editable under prompt-version control rather than hardcoding a module constant. The `PromptTemplateType` enum was NOT extended (no `redirect` type exists; `safety` is reused).
- **`prompt_version` ordering is fixed** (`system+deck_modifier+single_card+final_summary[+safety]`) so the audit string is stable/deterministic per reading.
- **Orientation drives content selection** inside each per-card block (reversed → reversed universal meaning/keywords + the deck-specific reversed modifier).
- **Missing active template = `ValueError`** (surfaced seed/admin misconfiguration), never a silently degraded prompt.

## Deviations from Plan

None - plan executed exactly as written. Both Task-1 and Task-2 acceptance criteria were met as specified; the only judgement call (redirect as a seeded `safety` row vs a module constant) was an explicit either/or the plan offered, and the plan's preferred option was taken.

## Issues Encountered
- **Wave-0 stub absence:** the environment note said a skipped `tests/unit/test_prompt_engine.py` stub already existed; it did not (the Wave-0 commit `f349e3a` seeded a different stub set). Resolved by creating the test file fresh against the locked `<behavior>` list — no impact on scope.
- **Ban-list scope clarification (not a deviation):** the canonical SAFE-06 ban-list flags the pre-existing `system` and `final_summary` rows because those rows legitimately *name* the forbidden words ("не упоминай ИИ, модель…") as negative instructions to the model. Per the Scope Boundary rule these pre-existing rows are out of scope and were left untouched; the ban-list scan was scoped to the 8 plan-touched rows (6 signatures + refusal + redirect), all of which pass — matching the Task-1 acceptance criterion "every new/edited RU line passes the ban-list".

## Verification Evidence
- `uv run pytest -q tests/unit/test_prompt_engine.py` → **9 passed**.
- `uv run pytest -q tests/unit/` → **81 passed** (no regressions; 1 pre-existing unrelated JWT key-length warning).
- `uv run ruff check app/services/prompt_engine.py` → **All checks passed** (0).
- `uv run ruff check tests/unit/test_prompt_engine.py` → **All checks passed** (0).
- Task-1 JSON check: unique slugs, 6 deck_modifier rows carry the signature (v2), refusal generic + digit-free (v2), `redirect` is `safety` type with "Колода молчит", and all 8 touched rows pass `contains_banned_brand_token`.
- Grep `prompt_engine.py` for `prompt_version` / `PromptTemplate` → 22 occurrences; no hardcoded full system prompt (templates read dynamically by slug).
- `tests/integration/test_seed.py` skipped cleanly (Postgres not up) — seed structural integrity validated via the Task-1 parse + the unchanged loader upsert-by-slug shape.

## User Setup Required
None - no external service configuration required. (The engine consumes already-required `ANTHROPIC_API_KEY` only indirectly via `LLMService` in Plan 05.)

## Next Phase Readiness
- **Plan 05 (ReadingService) is unblocked:** it can now call `PromptEngine().build(session, deck=…, spread=…, draw_records=…, question=…, topic=…, safety_action=…)` to get a `PromptBundle`, feed `bundle.system`/`bundle.user` to `LLMService.generate(...)`, persist `bundle.prompt_version` to `readings.prompt_version` + `generation_logs`, and call `refusal_copy`/`redirect_copy` on the crisis/abusive short-circuit branches (before any draw/charge, D-03/D-04/D-06).
- A DB-backed `PromptEngine.build` round-trip against the real `seeded_catalog` belongs in the Plan-05 integration suite (the unit suite here is deliberately Postgres-free).
- No blockers. Wave 1 of Phase 4 is complete (04-04 was the last Wave-1 plan).

## Self-Check: PASSED

- Files: `backend/app/services/prompt_engine.py`, `backend/tests/unit/test_prompt_engine.py`, `backend/app/seed/data/prompts.json`, `04-04-SUMMARY.md` — all FOUND.
- Commits: `4dfe5e1` (Task 1), `d7b3cf1` (Task 2) — both FOUND in git history.

---
*Phase: 04-real-personal-reading-keystone*
*Completed: 2026-06-13*
