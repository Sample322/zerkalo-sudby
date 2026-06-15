---
phase: 06-free-limits-soft-paywall
plan: 01
subsystem: database
tags: [postgres, sqlalchemy, alembic, migration, redis, pytest, concurrency, user_limits]

# Dependency graph
requires:
  - phase: 01-foundation
    provides: user_limits table (migration 0001), telegram_auth._ensure_user_limits, savepoint test harness
  - phase: 04-real-personal-reading
    provides: ReadingService.create_reading keystone + the limit-consume seam, FakeLLM/FakeSafety, seeded_catalog
provides:
  - "Alembic 0002: user_limits.week_start DATE->TIMESTAMP(tz) + UNIQUE(user_id), fully reversible"
  - "UserLimits.week_start typed Mapped[datetime|None] (TIMESTAMP) + uq_user_limits_user_id constraint"
  - "LimitsOut.week_start typed datetime|None"
  - "Race-safe _ensure_user_limits (ON CONFLICT DO NOTHING, week_start=NULL); _current_week_start removed"
  - "committed_seeded_catalog + two_committed_sessions fixtures (true cross-connection concurrency substrate)"
  - "6 red/extended test files (LIMIT-01..05 + paywall/refund/D-02) referencing every symbol Plans 02/03 must provide"
affects: [06-02 atomic consume + determine_access, 06-03 redis throttle, 06-04 FE paywall/count, 07-payments]

# Tech tracking
tech-stack:
  added: []  # zero new runtime dependencies (verified — RESEARCH "Standard Stack")
  patterns:
    - "Hand-written reversible Alembic alter_column with postgresql_using cast (self-heals existing rows)"
    - "INSERT ... ON CONFLICT (unique) DO NOTHING for race-safe 1:1 row-ensure"
    - "Committed two-connection pytest fixture for true PostgreSQL row-lock concurrency (vs the savepoint harness)"
    - "Red stub: import the not-yet-existing symbol INSIDE the test body + xfail(strict=False) so collection stays clean and the stub xpasses when the impl lands"

key-files:
  created:
    - backend/alembic/versions/0002_user_limits_rolling_window.py
    - backend/tests/integration/test_limit_concurrency.py
    - backend/tests/integration/test_limits_reset.py
    - backend/tests/integration/test_throttle.py
    - backend/tests/integration/test_paywall_block.py
    - backend/tests/unit/test_determine_access.py
  modified:
    - backend/app/models/billing.py
    - backend/app/schemas/auth.py
    - backend/app/services/telegram_auth.py
    - backend/tests/integration/conftest.py
    - backend/tests/integration/test_auth_flow.py

key-decisions:
  - "week_start migrated DATE->TIMESTAMP(timezone=True) (A1) — USER-APPROVED override of CONTEXT 'no schema change'; postgresql_using cast self-heals existing ISO-Monday dates to midnight timestamptz"
  - "UNIQUE(user_id) added (A2) so the auth ON CONFLICT (user_id) DO NOTHING has a target + structurally prevents duplicate rows"
  - "_ensure_user_limits returns None now ('ensure exists' contract); auth reads limits via get_user_limits for the response — no returning row needed"
  - "Red stubs import Plan-02/03 symbols inside the test body (not module top) so a missing symbol xfails loudly instead of erroring collection"

patterns-established:
  - "Plan 02 contract: app.services.reading.determine_access(limits) -> Bucket (StrEnum FREE/SUBSCRIPTION/PAID/NONE), order free->sub->paid"
  - "Plan 02 contract: ReadingService consumes the free slot AS THE GATE (atomic UPDATE) then REFUNDS on every non-success exit; paywall body carries reason='paywall' + reset_at"
  - "Plan 03 contract: app.api.deps.throttle_gate (FastAPI dep, 429 over cap) + a throttle_ok(redis, user_id, *, window_s, burst_cap) -> bool primitive"

requirements-completed: [LIMIT-01, LIMIT-02]

# Metrics
duration: 11min
completed: 2026-06-15
---

# Phase 6 Plan 01: Free-Limits Schema Foundation + Wave-0 Test Substrate Summary

**Reversible Alembic 0002 (week_start DATE→TIMESTAMP + UNIQUE(user_id)), a race-safe ON CONFLICT user_limits row at auth (week_start=NULL), and the committed two-connection concurrency fixture + 6 red test files the atomic-consume/throttle slices stand on.**

## Performance

- **Duration:** ~11 min
- **Started:** 2026-06-15T19:44:02Z
- **Completed:** 2026-06-15T19:55:05Z
- **Tasks:** 3 autonomous complete (Task 4 is the human-verify checkpoint — migration apply)
- **Files modified/created:** 11 (1 migration, 2 model/schema, 1 service, 1 conftest, 6 test files — counting test_auth_flow extend once)

## Accomplishments
- **A1+A2 migration (LIMIT-02 foundation):** one hand-written, fully-reversible Alembic revision `0002_user_limits_rolling_window` casts `week_start` `DATE → TIMESTAMP(timezone=True)` via `postgresql_using="week_start::timestamptz"` (self-heals existing ISO-Monday dates to midnight timestamptz, no NULL/no error) and adds `uq_user_limits_user_id`.
- **D-02 race-safe row at auth (LIMIT-01 foundation):** `_ensure_user_limits` rewritten to a single `INSERT … ON CONFLICT (user_id) DO NOTHING` with `week_start` omitted (→ NULL, anchors on first reading). The `_current_week_start()` ISO-Monday helper (which encoded the model D-01 overrides) is deleted.
- **The single most load-bearing test asset in the phase:** `committed_seeded_catalog` + `two_committed_sessions` fixtures provide TWO independent committed `AsyncSession`s on real connections — the only substrate that can exercise a genuine cross-connection PostgreSQL row lock (the savepoint harness cannot, research Pitfall 3).
- **6 red/extended test files** covering LIMIT-01..05 + paywall/refund/D-02, each importing the exact symbols Plans 02/03 must create, `xfail(strict=False)` until those plans land (so they xpass automatically), skip cleanly without Docker.

## Task Commits

Each task was committed atomically:

1. **Task 1: Alembic 0002 + model + schema** — `1a61897` (feat)
2. **Task 2: race-safe user_limits row at auth** — `e26bf75` (feat)
3. **Task 3: Wave-0 substrate — fixtures + 6 test files** — `ab80539` (test)

**Plan metadata:** (this SUMMARY + STATE/ROADMAP) committed separately.

## Files Created/Modified
- `backend/alembic/versions/0002_user_limits_rolling_window.py` — reversible week_start DATE→TIMESTAMP + UNIQUE(user_id)
- `backend/app/models/billing.py` — `UserLimits.week_start` now `Mapped[datetime|None]` TIMESTAMP; `__table_args__` UniqueConstraint(user_id)
- `backend/app/schemas/auth.py` — `LimitsOut.week_start: datetime | None`; dropped unused `date` import
- `backend/app/services/telegram_auth.py` — `_ensure_user_limits` → ON CONFLICT DO NOTHING (week_start NULL); removed `_current_week_start` + `date`/`timedelta` imports
- `backend/tests/integration/conftest.py` — `committed_seeded_catalog` + `two_committed_sessions` (true-concurrency substrate, explicit teardown)
- `backend/tests/integration/test_limit_concurrency.py` — LIMIT-03 boundary-race stub (asserts `used == 3`, never 4; documents the mutation-test break-step)
- `backend/tests/integration/test_limits_reset.py` — LIMIT-02 stale / within-window / first-ever reset stubs
- `backend/tests/integration/test_throttle.py` — LIMIT-05 burst / window-expiry / short-circuit-before-PG stubs
- `backend/tests/integration/test_paywall_block.py` — LIMIT-01 paywall `reason`/`reset_at` + refund-on-honest-fail stubs
- `backend/tests/unit/test_determine_access.py` — LIMIT-04 bucket-order stub (SUBSCRIPTION before PAID, pure fn)
- `backend/tests/integration/test_auth_flow.py` — extended with `test_limits_row_created` (week_start IS NULL at creation) + `test_double_login_single_limits_row` (xfail until migration applied)

## Symbols Plans 02/03 MUST provide (so the stubs xpass)

These names are asserted by the red stubs — Plans 02/03 must match them exactly:

| Symbol | Module | Created by | Stub file |
|--------|--------|-----------|-----------|
| `determine_access(limits) -> Bucket` | `app.services.reading` | Plan 06-02 | test_determine_access.py |
| `Bucket` (StrEnum: `FREE`/`SUBSCRIPTION`/`PAID`/`NONE`) | `app.services.reading` | Plan 06-02 | test_determine_access.py |
| `ReadingService.create_reading` w/ folded lazy reset + consume-as-gate + refund | `app.services.reading` | Plan 06-02 | test_limit_concurrency / test_limits_reset / test_paywall_block |
| `ReadingOut.reason` (`"paywall"`) + `ReadingOut.reset_at` | `app.schemas.reading` | Plan 06-02 | test_paywall_block.py |
| `throttle_gate` (FastAPI dependency, 429 over cap) | `app.api.deps` | Plan 06-03 | test_throttle.py |
| `throttle_ok(redis, user_id, *, window_s, burst_cap) -> bool` | `app.api.deps` (or `app.core.redis`) | Plan 06-03 | test_throttle.py |

New fixtures available to Plans 02/03: `committed_seeded_catalog`, `two_committed_sessions` (in `tests/integration/conftest.py`).

## Decisions Made
- **week_start DATE→TIMESTAMP migration (A1):** USER-APPROVED (resolved before planning) override of the CONTEXT "no schema change expected" note — required for D-01's hour-accurate rolling window + the D-04 countdown. The `postgresql_using` cast self-heals legacy rows; no data backfill.
- **UNIQUE(user_id) (A2):** required for the auth `ON CONFLICT (user_id)` target and structurally prevents the double-login duplicate-row bug (T-06-01).
- **`_ensure_user_limits` contract changed to return `None`** ("ensure exists"): `ON CONFLICT DO NOTHING` returns no row on conflict, and `authenticate()` reads limits separately via `get_user_limits` for the response, so no `.returning()` is needed.
- **Red-stub import placement:** Plan-02/03 symbols are imported INSIDE each test body (not at module top) so a missing symbol surfaces as the xfailed assertion rather than a collection-time `ImportError` that would error the whole module.

## Deviations from Plan

None - plan executed exactly as written. (The only non-verbatim choice — importing not-yet-existing symbols inside the test body rather than at module top — is the mechanism the plan's own acceptance criterion "collects with zero errors … reports only xfailed/skipped" requires, not a scope change.)

## Issues Encountered
- The plan's `<automated>` verify commands run `uv run python -c "import …"` directly, which triggers `Settings()` at import and needs the required secrets present. There is no `.env` in `backend/` (tests get them via the root conftest's `os.environ.setdefault`). Resolved by prepending the same test-env defaults when running the bare-import verifies; `uv run pytest` already supplies them. No code change.

## Authentication Gates
None.

## Manual Verification Required (Task 4 — human-verify checkpoint, BLOCKING)

**Migration 0002 is authored but NOT applied** — the agent environment has no Docker/Postgres (locked env constraint, consistent with Phases 1–5). Apply + verify against a real database:

1. `cd backend && uv run alembic upgrade head` — applies without error; `uv run alembic current` shows `0002_user_limits_rolling_window`.
2. `\d user_limits` in psql — `week_start` is `timestamp with time zone`; `uq_user_limits_user_id` is a UNIQUE constraint.
3. Confirm existing rows survived — any pre-existing ISO-Monday `DATE` values are now midnight `timestamptz` (not NULL, not errored).
4. Reversibility: `uv run alembic downgrade -1` then `upgrade head` again succeeds.

Once applied against a live DB, `test_double_login_single_limits_row` (currently xfail) xpasses — it is the live proof the UNIQUE constraint dedupes concurrent first-logins.

## Test Results
- Full backend suite: **83 passed, 76 skipped, 3 xfailed** (baseline 83 pass / 65 skip preserved; the new stubs add +11 skip without Docker + 3 xfail for the pure-fn `determine_access` stubs). Zero failures, zero collection errors.
- `uv run ruff check` clean on every created/modified file.
- The 11 DB/Redis-touching stubs skip cleanly without Postgres/Redis (live behavior is the Plan-02/03 green target + the user-smokes above).

## Next Plan Readiness
- 06-02 (atomic consume + lazy reset + determine_access + refund) has its full test target + the committed concurrency fixture ready; the schema (TIMESTAMP + UNIQUE) it depends on is authored.
- 06-03 (Redis throttle gate) has its stub contract (`throttle_gate` / `throttle_ok`) defined.
- **Blocker until the human checkpoint clears:** migration 0002 must be applied against a real DB before 06-02 can be live-verified (the atomic `UPDATE` re-anchors `week_start` as a TIMESTAMP and the auth `ON CONFLICT` needs the UNIQUE constraint).

## Self-Check: PASSED

All created files verified present (migration, 6 test files, SUMMARY) and all 3 task commits (`1a61897`, `e26bf75`, `ab80539`) exist in history.

---
*Phase: 06-free-limits-soft-paywall*
*Completed: 2026-06-15*
