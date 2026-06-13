---
phase: 04-real-personal-reading-keystone
plan: 02
subsystem: api
tags: [csprng, secrets, card-draw, brand-guard, safe-06, sqlalchemy, pytest, tdd]

# Dependency graph
requires:
  - phase: 04-01
    provides: "app.schemas.reading contracts (ReadingOutput etc.); Wave-0 test stubs + seeded_catalog/auth_session fixtures; catalog.py async-service pattern"
  - phase: 03
    provides: "frontend reading/copy.ts BANNED_BRAND_TOKENS (canonical SAFE-06 ban-list ported here)"
provides:
  - "CardDrawService.draw — backend-only CSPRNG card draw (secrets.SystemRandom shuffle + 70/30 orientation), returns immutable DrawnCard records"
  - "DrawnCard dataclass — the (card_id/deck_card_id/position_id/position_index/orientation + joined universal meaning) record Plan 05 persists into reading_cards"
  - "_assign_orientations — pure, injectable-rng orientation helper (deterministic 70/30)"
  - "core/brand_guard.py — backend SAFE-06 ban-list (BANNED_BRAND_TOKENS + contains_banned_brand_token), 1:1 port of the frontend regex"
affects: [04-05, reading-orchestration, prompt-engine, reading-service, persistence]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Module-level CSPRNG default (_rng = secrets.SystemRandom) + injectable rng port on pure helpers → deterministic, seeded ratio tests without weakening production randomness"
    - "Pure DB-free helper (orientation/ratio) split from the async DB draw, mirroring catalog.py's _build_reason split → unit-testable in isolation"
    - "Frozen dataclass draw record (no DB write in the service; persistence owned by the consuming service) — clean service/transaction boundary"
    - "One-source-of-truth cross-stack ban-list: backend regex mirrors frontend reading/copy.ts exactly (W-1)"

key-files:
  created:
    - "backend/app/services/card_draw.py"
    - "backend/app/core/brand_guard.py"
    - "backend/tests/integration/test_card_draw_db.py"
  modified:
    - "backend/tests/unit/test_card_draw.py"
    - "backend/tests/unit/test_brand_guard.py"

key-decisions:
  - "Card draw randomness via secrets.SystemRandom for BOTH shuffle and orientation coin; never stdlib random (TZ §12.5, D-13, CLAUDE.md anti-pattern) — CSPRNG asserted by test_uses_csprng (source + instance check)."
  - "Orientation/ratio logic lives in a pure _assign_orientations helper with an injectable rng port, so the 70/30 ratio is tested deterministically with a seeded random.Random as a test double, while production defaults to the module CSPRNG."
  - "CardDrawService writes nothing (no reading_cards INSERT); it returns frozen DrawnCard records carrying exactly the reading_cards columns + joined universal meaning — persistence + transaction are Plan 05's (ReadingService)."
  - "Per RESEARCH A5 / OQ1 there is no seed/debug_hash column → none invented; immutable reading_cards rows are the durable record."
  - "Backend brand guard is a 1:1 port of frontend BANNED_BRAND_TOKENS (one source of truth, W-1); disposition is LOG+FLAG (RESEARCH OQ2) — documented in the module, never fails the reading."
  - "DB-touching draw assertions moved to tests/integration/test_card_draw_db.py (where seeded_catalog/auth_session live + skip cleanly when Postgres is down); the unit test stays pure."

patterns-established:
  - "Injectable-rng CSPRNG pattern: secure module default + deterministic test double via the same _RNG Protocol."
  - "Cross-stack single-source ban-list: backend mirror of a frontend canonical regex, validated by mirrored test cases."

requirements-completed: [READ-02, READ-11, SAFE-04, SAFE-05]

# Metrics
duration: 30min
completed: 2026-06-13
---

# Phase 04 Plan 02: Backend Draw + Brand-Guard Primitives Summary

**Backend-only CSPRNG card draw (`secrets.SystemRandom` shuffle + 70/30 orientation, returning immutable `DrawnCard` records) and a `core/brand_guard.py` SAFE-06 ban-list that mirrors the canonical frontend regex without false-positiving benign «ии» words.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-13T14:10Z (approx)
- **Completed:** 2026-06-13T14:40Z
- **Tasks:** 2
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments
- `CardDrawService.draw` — backend-only draw from the active deck's `deck_cards` (joined to `cards` for universal meaning), CSPRNG shuffle, first `card_count` cards assigned to spread positions by `position_index`, with reversals OFF → all upright / ON → 70/30 orientation via the CSPRNG coin. Returns immutable `DrawnCard` records and writes nothing (persistence is Plan 05).
- Pure `_assign_orientations` helper with an injectable rng port → the 70/30 ratio is verified deterministically over a 20k-sample seeded run (within ±0.02), and CSPRNG usage is asserted both by instance type and by source-scan (no `import random` / `random.shuffle` / `random.random`).
- `core/brand_guard.py` — a 1:1 backend port of the frontend `BANNED_BRAND_TOKENS` (`ai|нейросет|модель|сгенерирован` + the Cyrillic-word-boundary «ии» branch, `re.IGNORECASE`), detecting AI/ИИ/нейросеть/модель/сгенерировано without false-positiving гармонии/линии/версии/комиссии. LOG+FLAG disposition documented.
- All Wave-0 skips removed; target tests green; integration draw tests skip cleanly when Postgres is down.

## Task Commits

Each task was committed atomically (TDD: written RED → implemented GREEN within one cohesive commit per task):

1. **Task 1: CardDrawService — backend-only CSPRNG draw + 70/30 orientation** — `16e7219` (feat)
2. **Task 2: Backend brand guard (core/brand_guard.py) — SAFE-06 output ban-list port** — `62327ad` (feat)

**Plan metadata:** _(this SUMMARY + STATE/ROADMAP commit follows)_

## Files Created/Modified
- `backend/app/services/card_draw.py` — `CardDrawService` (CSPRNG draw), `DrawnCard` frozen dataclass, pure `_assign_orientations` helper, `REVERSED_PROBABILITY=0.30`.
- `backend/app/core/brand_guard.py` — `BANNED_BRAND_TOKENS` (compiled, `re.IGNORECASE`) + `contains_banned_brand_token`; LOG+FLAG disposition in the docstring.
- `backend/tests/unit/test_card_draw.py` — count/reversals-off/both-orientations/70-30-ratio/CSPRNG behaviours (skip removed; pure, DB-free).
- `backend/tests/integration/test_card_draw_db.py` — DB-touching draw over `seeded_catalog`: count==positions, well-formed records, reversals-on domain, backend-only/no-client-card-seam (T-04-12); skips when Postgres is down.
- `backend/tests/unit/test_brand_guard.py` — banned-stems, standalone-ИИ, benign-«ии» guard, brand-safe copy, stateless-pattern (skip removed; mirrors frontend `copy.test.ts`).

## Decisions Made
- **CSPRNG everywhere in the draw.** `secrets.SystemRandom` for shuffle AND the orientation coin (TZ §12.5, D-13). The pure helper takes an injectable rng (a `_RNG` Protocol) so seeded determinism in tests never weakens production randomness.
- **Service is pure — no persistence.** `draw` returns frozen `DrawnCard` records carrying exactly the `reading_cards` columns Plan 05 writes + the joined universal `meaning_*`/`keywords_*` the PromptEngine needs. ReadingService (Plan 05) owns the INSERT + transaction. No seed/debug_hash invented (RESEARCH A5/OQ1).
- **One source of truth for the ban-list.** The backend regex mirrors the frontend `reading/copy.ts` exactly (W-1); LOG+FLAG (not fail) per RESEARCH OQ2.
- **Test placement matches fixture scope.** DB-touching draw assertions went to `tests/integration/` (where `seeded_catalog`/`auth_session` live and skip cleanly without Postgres); the unit test stays pure — consistent with the existing `test_recommend_reason` (pure) vs `test_catalog` (integration) split.

## Deviations from Plan

None — plan executed exactly as written. (No bugs, missing-critical, blocking, or architectural triggers fired; Rules 1–4 not invoked.)

## Issues Encountered
- **`test_uses_csprng` tripped on a comment substring.** The CSPRNG source-scan asserts the literal phrase `import random` is absent from the module; my initial "NEVER `import random`" warning comment contained that exact phrase. Resolved by rewording the comment ("deliberately NOT the stdlib pseudo-random module") so the source contains no `import random` / `random.shuffle` / `random.random` token — this also makes the acceptance-criteria grep clean. (Within Task 1, before its commit.)
- **DB-touching draw test initially placed in the unit file.** `seeded_catalog`/`auth_session` are defined in `tests/integration/conftest.py`, so a unit-file test could not resolve them (errored). Moved that test (expanded into three) to a new `tests/integration/test_card_draw_db.py`; it skips cleanly here (Postgres/Docker unavailable) and will exercise the real draw once the stack is up. (Within Task 1, before its commit.)

## User Setup Required
None — no external service configuration required. Both primitives are pure (no LLM, no network).

## Next Phase Readiness
- The two deterministic building blocks the Plan-05 orchestration wires between the safety gate and the LLM call are ready: `CardDrawService.draw` (fair, unforgeable hand) and `contains_banned_brand_token` (post-generation output guard).
- Note for the verifier: 4 of the plan's tests are integration tests that **skip** in this environment (Docker/Postgres unavailable, per the established Wave-0 convention); they will run when the stack is up. All pure unit behaviours run fully and pass (9 target tests, 43 in the full unit suite).
- No blockers introduced.

## Self-Check: PASSED

- Files verified present: `card_draw.py`, `core/brand_guard.py`, `test_card_draw_db.py`, `test_card_draw.py`, `test_brand_guard.py`, this SUMMARY.
- Commits verified in git history: `16e7219` (Task 1), `62327ad` (Task 2).
- Target tests green: `pytest -q tests/unit/test_card_draw.py tests/unit/test_brand_guard.py` → 9 passed.
- Ruff clean: `ruff check app/services/card_draw.py app/core/brand_guard.py` → 0.
- CSPRNG grep: no `import random` / `random.shuffle` / `random.random` in `card_draw.py`; `secrets.SystemRandom` present.

---
*Phase: 04-real-personal-reading-keystone*
*Completed: 2026-06-13*
