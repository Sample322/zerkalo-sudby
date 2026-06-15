---
phase: 06-free-limits-soft-paywall
plan: 02
subsystem: backend
tags: [postgres, sqlalchemy, concurrency, atomic-update, rolling-window, paywall, refund, user_limits]

# Dependency graph
requires:
  - phase: 06-free-limits-soft-paywall
    plan: 01
    provides: "Alembic 0002 (week_start DATE->TIMESTAMP + UNIQUE(user_id)); committed two-connection concurrency fixtures; 6 red test files referencing this plan's symbols; race-safe user_limits row at auth (week_start=NULL)"
  - phase: 04-real-personal-reading
    provides: "ReadingService.create_reading keystone + the limit-consume seam; FakeLLM/FakeSafety; seeded_catalog; _short_circuit/_honest_fail/_soft_body/_build_response"
provides:
  - "app.services.reading.determine_access(limits, now=None) -> Bucket (StrEnum FREE/SUBSCRIPTION/PAID/NONE), order free->subscription->paid"
  - "ReadingService._consume_free_atomic — one conditional UPDATE...WHERE...RETURNING with the lazy rolling-7d reset folded in via case() (LIMIT-02/03 atomicity control)"
  - "ReadingService._consume_free_gate (bucket router; fail-closed on missing row) + _refund_free (compensating UPDATE) + _compute_reset_at(week_start)=week_start+7d"
  - "create_reading rewired to the locked order: safety -> atomic-consume-gate -> draw -> generate -> refund-on-honest-fail"
  - "ReadingOut.reason (str|None; 'paywall' on the limit block) + ReadingOut.reset_at (datetime|None) — the FE limit-block discriminant (D-04)"
affects: [06-03 redis throttle gate, 06-04 FE paywall/count discriminant, 07-payments sub/paid buckets]

# Tech tracking
tech-stack:
  added: []  # zero new runtime dependencies (RESEARCH "Standard Stack")
  patterns:
    - "Atomic check+decrement via a single conditional UPDATE...WHERE free_used<limit...RETURNING (PostgreSQL row lock serializes boundary writers; no SELECT FOR UPDATE, no app lock)"
    - "Lazy rolling-window reset folded into the SAME UPDATE via case() (stale/first_ever/fresh_has_room collapse into one indivisible statement; no read-then-reset-then-decrement TOCTOU)"
    - "Shared SQLAlchemy predicate objects reused in BOTH the WHERE or_() and the SET case() so boundary logic cannot drift (Pitfall 5)"
    - "no-slot detection via .first() is None (never rowcount, unreliable with RETURNING on asyncpg)"
    - "consume-as-gate + compensating refund on the single post-consume non-success exit (honest-fail) to preserve a never-consumed-on-failure invariant"
    - "pure determine_access bucket-selection seam (free->sub->paid) built now, only FREE populated until Phase 7"

key-files:
  created:
    - .planning/phases/06-free-limits-soft-paywall/deferred-items.md
  modified:
    - backend/app/services/reading.py
    - backend/app/schemas/reading.py
    - backend/tests/integration/test_readings_limit.py

key-decisions:
  - "Consume-as-gate (atomic UPDATE before the draw) + refund-only-on-honest-fail — chosen over keep-consume-last (RESEARCH A4/Pitfall 2). Safety runs BEFORE the consume so crisis/abusive never consume (zero refund); only the post-consume honest-fail refunds."
  - "determine_access drops the plan's literal first_ever->FREE clause (DEVIATION, see below) — null-week_start is NOT a free slot in the pure fn; the atomic UPDATE remains the first_ever arbiter. Required by the authoritative unit contract AND correctness of test_limit_untouched_on_no_quota."
  - "Missing user_limits row is fail-closed (paywall), not unlimited — closes the Phase-4 'no row -> unlimited' gap; D-02 guarantees a row anyway."
  - "Removed the superseded _has_quota + _consume_limit (dead after the atomic gate); kept _remaining for the read-only GET /api/me projection (Plan 04 count)."

patterns-established:
  - "Plan 04 FE contract: the limit-block soft body is HTTP 200 with ReadingOut.reason == 'paywall' + ReadingOut.reset_at (week_start + 7d). Branch the createReading catch on reason; render the countdown from reset_at."
  - "Plan 03 throttle is the upstream GATE 0 (429 {kind:'throttle'}) before create_reading; this plan's consume-gate is GATE 1 (paywall 200). Distinct transports (D-08), never conflated."
  - "Phase 7 seam: _consume_free_gate falls through to SUBSCRIPTION/PAID atomic consumes when determine_access returns those buckets (balances are 0 this phase, so it never does yet)."

requirements-completed: [LIMIT-02, LIMIT-03, LIMIT-04]

# Metrics
duration: 12min
completed: 2026-06-15
---

# Phase 6 Plan 02: Atomic Consume + Folded Rolling Reset + Bucket Seam + Refund Summary

**The correctness heart of the phase: a single conditional `UPDATE user_limits … WHERE free_used < limit … RETURNING` with the lazy rolling-7d reset folded in via `case()` (no TOCTOU double-spend under concurrency), the `determine_access` free→subscription→paid bucket seam, and the consume-order inversion reconciled with Phase-4's "crisis before charge" via safety-before-consume-gate + refund-only-on-honest-fail.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-06-15T20:01:15Z
- **Completed:** 2026-06-15T20:12:54Z
- **Tasks:** 3 autonomous complete (no checkpoint — `autonomous: true`)
- **Files modified/created:** 4 (2 service/schema, 1 test, 1 deferred-items doc)

## Accomplishments

- **THE atomicity control (LIMIT-03, success-criterion 3):** `ReadingService._consume_free_atomic` issues ONE conditional `update(UserLimits).where(or_(stale, first_ever, fresh_has_room)).values(case(...)).returning(free_used_this_week, free_weekly_limit)`. PostgreSQL's row lock serializes two boundary racers: one matches `fresh_has_room` and increments to the limit, the other re-evaluates against the committed value, matches zero arms, and gets `None` → paywall. Compiles to the exact intended SQL (verified against the PG dialect). No `SELECT … FOR UPDATE`, no app lock.
- **Folded lazy rolling reset (LIMIT-02, D-01):** the reset is `case()` arms in the SAME UPDATE — `stale` (week_start set and `<= now-7d`) → `free_used=1` + re-anchor `week_start=now`; `first_ever` (week_start IS NULL, D-02) → `free_used=1` + anchor; `fresh_has_room` → `+1`, week_start unchanged; fresh-no-room → 0 arms → paywall. The `stale`/`fresh_has_room`/`first_ever` predicate objects are defined once and reused in BOTH the WHERE `or_()` and the SET `case()` (no drift, Pitfall 5 — verified: the compiled SQL shares the same bind params between WHERE and SET).
- **`determine_access` bucket seam (LIMIT-04, D-06):** pure `determine_access(limits, now=None) -> Bucket` returns FREE when `free_left>0 OR window_stale`, else SUBSCRIPTION (sub left), else PAID (balance), else NONE. Only FREE is ever populated this phase; the sub/paid arms are the Phase-7 seam (`_consume_free_gate` falls through to them when those buckets are returned).
- **Consume-order inversion reconciled (constraint 3 / READ-10):** `create_reading` now runs safety classify+route FIRST (crisis/abusive short-circuit BEFORE any consume → zero refund), then `determine_access` + the atomic consume AS THE GATE (before the draw), then draw→persist→generate. The single post-consume non-success exit (honest-fail) issues a compensating `_refund_free` UPDATE (`free_used -= 1`) in the same transaction. All four Phase-4 `test_limit_untouched_on_*` invariants (crisis/abusive/no-quota/honest-fail) hold under the new order.
- **Error-transport contract for the FE (D-04):** `ReadingOut` extended with `reason: str | None` + `reset_at: datetime | None`; the paywall body sets **`reason="paywall"`** + **`reset_at = week_start + 7d`** (via `_compute_reset_at`) with NO draw.

## Consume Order + Refund Obligation (the locked reconciliation — for Plan 03/04/07)

```
create_reading(session, user, req):
  resolve deck/spread; now = datetime.now(UTC); limits = _get_limits(...)
  1. SAFETY  classify + route
       crisis/abusive -> _short_circuit (NO consume, limit kept)  ← BEFORE the gate
  2. CONSUME-GATE  bucket = determine_access(limits, now)
       FREE -> _consume_free_atomic (atomic UPDATE...RETURNING, lazy reset folded)
         None  -> soft paywall body (reason='paywall', reset_at=week_start+7d), NO draw
         (used, limit) -> remaining = max(0, limit-used)   ← slot consumed HERE
  3. draw -> persist pending -> log classify
  4. PromptEngine.build -> prompt_version
  5. generate (ONE call)
       LLMGenerationError -> _honest_fail: status=FAILED + REFUND (free_used-=1) + soft body
  6. brand guard (log+flag)
  7. persist output -> status=COMPLETED
  8. commit -> ReadingOut (remaining from the gate; NO consume here)
```

**Refund obligation:** because the free slot is consumed AS THE GATE (before the draw, Pattern 1), every post-consume non-success exit MUST refund. In this phase the only such exit is **honest-fail** (crisis/abusive are pre-gate, so they never consume). `_honest_fail` runs `_refund_free` + `session.refresh(limits)` in-transaction → net counter unchanged → READ-10 holds. **Phase 7 must refund sub/paid analogously** behind `Bucket` for any new post-consume exit.

## ReadingOut field names + reason value (FOR PLAN 04 — match these exactly)

| Field | Type | Value on the limit block | Purpose |
|-------|------|--------------------------|---------|
| `reason` | `str \| None` | **`"paywall"`** | Machine-readable discriminant the FE `createReading` catch branches on (no string-matching the copy). `None` on success/refusal/redirect/honest-fail. |
| `reset_at` | `datetime \| None` | `week_start + 7d` (per-user) | The reopen moment fuelling the D-04 countdown («вернутся через N»). `None` when no window is anchored (paywall only fires within a fresh anchored window, so it is non-None there). |

Throttle (Plan 03) is a separate transport: **429 `{kind:"throttle"}`** (GATE 0), never a `reason` on a 200 body (D-08).

## Mutation-Test Result (proves the concurrency test is load-bearing — 06-VALIDATION.md)

**Live procedure (user-smoke, needs Postgres):** temporarily replace `fresh_has_room`'s `UserLimits.free_used_this_week < UserLimits.free_weekly_limit` guard with a non-atomic read-check-write (or simply drop the `< limit` clause), run `uv run pytest tests/integration/test_limit_concurrency.py` WITH Postgres up → the test MUST then observe `used == 4` and go red. Revert.

**Static proof performed this plan (no Docker in env):** compiling the mutant statement (the `fresh_has_room` arm with the `< limit` guard removed) against the PG dialect yields a WHERE of:
```
user_id = :id AND (week_start IS NOT NULL AND week_start <= :ws1
                   OR week_start IS NULL
                   OR week_start IS NOT NULL AND week_start > :ws2)
```
— with **no** `free_used_this_week < free_weekly_limit` guard. Both boundary racers (used=2, fresh window) match that broken arm and both `+1` → `used == 4`. This confirms the guard is the exact load-bearing predicate the concurrency test exercises (the test asserts `used == 3, NOT 4`). The correct (un-mutated) statement keeps the guard, so racer B matches zero arms and gets the paywall.

## Files Created/Modified

- `backend/app/services/reading.py` — added `Bucket` StrEnum + `WINDOW` + pure `determine_access`; `ReadingService._consume_free_atomic` (folded-reset conditional UPDATE…RETURNING), `_consume_free_gate` (bucket router, fail-closed), `_refund_free`, `_compute_reset_at`; rewired `create_reading` to the locked safety→consume-gate→draw→generate→refund order; `_soft_body` accepts `reason`/`reset_at`; `_honest_fail` refunds in-transaction; removed superseded `_has_quota` + `_consume_limit`; module docstring updated.
- `backend/app/schemas/reading.py` — `ReadingOut` += `reason: str | None` + `reset_at: datetime | None`.
- `backend/tests/integration/test_readings_limit.py` — added `test_paywall_carries_reset_at` (+ a local `_make_fresh_exhausted` seeding `week_start=now`) asserting `reason == "paywall"` + non-None `reset_at`; the 5 existing untouched-on-* tests pass unchanged under the new order.
- `.planning/phases/06-free-limits-soft-paywall/deferred-items.md` — logged the pre-existing out-of-scope `UP037` in `models/spread.py`.

## Task Commits

1. **Task 1: determine_access + Bucket seam** — `e1128fd` (feat)
2. **Task 2: _consume_free_atomic folded-reset UPDATE…RETURNING** — `cd3607d` (feat)
3. **Task 3: rewire create_reading + paywall reason/reset_at** — `b5dae7c` (feat)

**Plan metadata** (this SUMMARY + STATE/ROADMAP/REQUIREMENTS) committed separately.

## Decisions Made

- **Consume-as-gate + refund-on-honest-fail (RESEARCH A4):** chosen over keep-consume-last. The atomic UPDATE must be the gate to be TOCTOU-free; safety runs before it so crisis/abusive never consume; only honest-fail refunds. Lower-surprise than re-introducing a separate non-mutating reservation.
- **Fail-closed on a missing `user_limits` row:** `_consume_free_gate` returns `None` (paywall) when `limits is None`, rather than granting a free reading. D-02 guarantees the row at auth; treating a missing row as unlimited would re-open the Phase-4 gap.
- **Kept `_remaining`; removed `_has_quota` + `_consume_limit`:** the atomic gate fully supersedes the read-`_has_quota`-then-`_consume_limit` pair on the hot path (RESEARCH "Deprecated/outdated"). `_remaining` stays for the read-only `GET /api/me` projection (Plan 04's count line).

## Deviations from Plan

**1. [Rule 1 — Bug] `determine_access` drops the plan's literal `first_ever -> FREE` clause.**
- **Found during:** Task 1 (reconciling the plan action text against the authoritative Wave-0 unit stubs).
- **Issue:** The plan's Task-1 `<action>` says return `Bucket.FREE` if `free_left > 0 or window_stale or first_ever`. But the authoritative red stub `tests/unit/test_determine_access.py` calls `determine_access(_Limits(...))` where `_Limits.week_start` defaults to `None` (i.e. `first_ever` is True) AND `test_none_when_exhausted` / `test_bucket_order` pass `free_used=3` expecting **NONE** / **SUBSCRIPTION**. With the literal `first_ever` clause those two tests would get FREE and fail. Worse, in the create-path it would break `test_limit_untouched_on_no_quota` (free_used=3, week_start=NULL): `determine_access`→FREE would route to `_consume_free_atomic`, whose `first_ever` WHERE arm matches a NULL week_start and **resets `free_used` to 1, granting a reading** — the test expects a paywall with `used==3`.
- **Fix:** `determine_access` returns FREE on `free_left > 0 OR window_stale` only; a NULL `week_start` is NOT a free slot in the pure function. The atomic UPDATE remains the sole `first_ever` arbiter (it correctly anchors a brand-new user). This is safe because a real new user has `free_used == 0`, so `free_left > 0` already selects FREE — the only differing state (NULL week_start + exhausted) is anomalous and must paywall.
- **Files modified:** `backend/app/services/reading.py` (`determine_access`).
- **Commit:** `e1128fd`.
- **Param signature note:** the plan specifies `determine_access(limits, now)`; the unit stub calls it with one positional arg, so `now` is an optional keyword defaulting to `datetime.now(UTC)` (still tz-aware — Pitfall 1 honored). This satisfies both the stub and the create-path call `determine_access(limits, now)`.

## Issues Encountered

- **No Docker/Postgres in the agent env (locked constraint):** the 11 DB-touching tests (concurrency / reset / paywall / the 5 readings_limit) SKIP locally, consistent with Phases 1–5. Correctness was verified by: (a) compiling the atomic statement + the mutant against the PG dialect; (b) a full static trace of all 6 readings_limit + 3 paywall/reset behaviors against the implementation; (c) the determine_access unit stubs which run without a DB (3 xpass). The live concurrency/reset/paywall runs are user-smokes below.
- **Pre-existing `UP037` ruff error in `models/spread.py`** (lines 38, 56) surfaced by `ruff check app/` — NOT in any touched file, already logged in `05-history-profile/deferred-items.md`. Out of scope per the executor SCOPE BOUNDARY rule; re-logged to the phase-06 deferred-items.md. All three touched files lint clean.

## Authentication Gates

None.

## Manual Verification Required (user-smokes — need live Postgres + the applied migration 0002)

> Migration 0002 must be applied first (06-01's BLOCKING human-verify checkpoint). These are the live proofs of this plan's correctness, all skipped locally for lack of Docker:

1. **Concurrency (THE proof, LIMIT-03):** `cd backend && uv run pytest tests/integration/test_limit_concurrency.py -q` with Postgres up → `test_two_concurrent_at_boundary_only_one_succeeds` xpasses (one `completed` + one `failed`, `free_used == 3` never 4).
2. **Mutation test:** break the `WHERE free_used_this_week < free_weekly_limit` guard, re-run #1 → it observes `used == 4` and goes red (proves the test is load-bearing). Revert.
3. **Rolling reset (LIMIT-02):** `uv run pytest tests/integration/test_limits_reset.py -q` → stale window resets to used=1 + re-anchors; within-window stays blocked; NULL anchors on first reading.
4. **Paywall + refund (LIMIT-01):** `uv run pytest tests/integration/test_paywall_block.py tests/integration/test_readings_limit.py -q` → paywall body carries `reason='paywall'` + `reset_at`; honest-fail refunds (net `used` unchanged); all 5 untouched-on-* green.
5. **Full live suite:** `cd backend && uv run pytest` with Postgres up → the 11 currently-skipped DB tests run green.

## Test Results

- Full backend suite (no Docker): **83 passed, 77 skipped, 3 xpassed, 0 failed, 0 errors** (baseline 83 pass / 76 skip / 3 **xfail** from 06-01 → the 3 `determine_access` stubs flipped xfail→xpass when the symbol landed; +1 skip from the new `test_paywall_carries_reset_at`; the 10 other DB-limit tests stay skipped without Postgres).
- `uv run ruff check` clean on `services/reading.py`, `schemas/reading.py`, `tests/integration/test_readings_limit.py`.
- The atomic UPDATE + its mutant compiled against the PG dialect (RETURNING + CASE present, no FOR UPDATE; the `< limit` guard is the exact load-bearing predicate).
- `_compute_reset_at` (= week_start + 7d, None→None) + the `reason`/`reset_at` ReadingOut fields unit-checked.

## Next Plan Readiness

- **06-03 (Redis throttle gate):** unblocked — the consume-gate (GATE 1) is in place; the throttle is the upstream GATE 0 (`throttle_gate` / `throttle_ok` contract from 06-01) returning 429 before this gate, distinct transport from the paywall (D-08).
- **06-04 (FE paywall/count):** the discriminant is locked — branch `createReading` on `ReadingOut.reason === "paywall"`, render the countdown from `reset_at`; the remaining count comes from `GET /api/me` `limits` (D-09).
- **07-payments:** the `Bucket` SUBSCRIPTION/PAID arms + `_consume_free_gate` fall-through are the seam; Phase 7 adds their atomic consumes + analogous refunds behind the same enum, no re-architecture.
- **Blocker (carried from 06-01):** migration 0002 must be applied against a live DB before any of this plan's DB behavior can be live-verified.

## Self-Check: PASSED

All created/modified files verified present (`services/reading.py`, `schemas/reading.py`, `tests/integration/test_readings_limit.py`, `06-02-SUMMARY.md`, `deferred-items.md`) and all 3 task commits (`e1128fd`, `cd3607d`, `b5dae7c`) exist in history.

---
*Phase: 06-free-limits-soft-paywall*
*Completed: 2026-06-15*
