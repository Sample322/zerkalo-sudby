---
phase: 07-telegram-stars-payments
plan: 04
subsystem: backend
tags: [buckets, consume-gate, subscription, paid, refund, reading-service, yookassa, d-11, wave-3]

# Dependency graph
requires:
  - phase: 06-free-limits-soft-paywall
    provides: "the atomic consume-gate (_consume_free_gate/_consume_free_atomic) + Bucket(free→subscription→paid) seam + refund-on-honest-fail in reading.py"
  - plan: 07-03
    provides: "SUBSCRIPTION_WINDOW_UNLIMITED (D-09 window-gated encoding, owned in payments.py) + PaymentService + the grant that writes subscription_spreads_limit/_used + paid_spreads_balance"
  - plan: 07-01
    provides: "test_reading_buckets.py RED contract (subscription/paid consume + correct-bucket refund) + the get_payment_service dependency_overrides seam name"
provides:
  - "Filled SUBSCRIPTION/PAID arms in _consume_free_gate — each an atomic conditional UPDATE ... RETURNING (window-gated sub via _used<_limit; paid via balance>0), free→sub→paid order (D-11)"
  - "Bucket-aware honest-fail refund (_refund_subscription/_refund_paid + _refund_consumed_bucket) — refunds the bucket ACTUALLY consumed, never free by default"
  - "get_payment_service FastAPI dependency (app/api/payments.py) mirroring get_reading_service — the DI seam Plan 05's routes + the payment tests override"
affects: [07-05, payments, reading]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every bucket arm is an atomic conditional UPDATE ... RETURNING (no SELECT-then-UPDATE, no rowcount — 'no slot' is always the absent RETURNING row); the PG row lock is the cross-connection over-spend guard, mirroring _consume_free_atomic (T-07-OVERSPEND)"
    - "The gate return was widened from tuple[int,int]|None to tuple[Bucket, int|None]|None so the consumed bucket is threaded to the honest-fail refund (T-07-REFUND-WRONG-BUCKET); the subscription arm reads Plan-03's SUBSCRIPTION_WINDOW_UNLIMITED contract BY NAME (never redefines the sentinel)"
    - "get_payment_service lives in the payments ROUTER module (app/api/payments.py), the exact analog of get_reading_service in readings.py — routes are added onto the same module by Plan 05"

key-files:
  created:
    - "backend/app/api/payments.py — the get_payment_service dependency seam (router placeholder; routes are Plan 05)"
  modified:
    - "backend/app/services/reading.py — filled SUBSCRIPTION/PAID consume arms + _consume_subscription_atomic/_consume_paid_atomic + _refund_subscription/_refund_paid/_refund_consumed_bucket; gate return widened to carry Bucket; _honest_fail routes the refund by consumed bucket; create_reading threads consumed_bucket"

key-decisions:
  - "Gate return widened to tuple[Bucket, int|None]|None (was tuple[int,int]|None): FREE→(FREE, max(0,limit-used)); SUBSCRIPTION→(SUBSCRIPTION, None) because a window-gated bucket has no meaningful count to surface; PAID→(PAID, post-decrement balance); NONE/no-slot→None (paywall unchanged). This is the plan's explicit 'extend the gate return so the caller can route the refund' instruction."
  - "Subscription arm is count-atomic ONLY for concurrency — the WHERE subscription_spreads_used < subscription_spreads_limit condition serializes concurrent reads via the row lock; the real bound is the window (determine_access selects SUBSCRIPTION only in a live window, and Plan-03's grant sets _limit = SUBSCRIPTION_WINDOW_UNLIMITED so it never blocks a real subscriber). The sentinel is NOT re-imported/redefined here (D-09 owned by payments.py)."
  - "get_payment_service placed in a NEW app/api/payments.py (not deps.py) because that is where the mirror-target get_reading_service lives (readings.py, the router module) and where Plan 01's test does `from app.api.payments import get_payment_service`; the module is a routes-less placeholder this plan, and Plan 05 adds the /api/products/create/webhook/refund routes onto the same router."

patterns-established:
  - "_refund_consumed_bucket(session, user_id, bucket) is the single refund router: FREE→_refund_free, SUBSCRIPTION→_refund_subscription, PAID→_refund_paid, None/NONE→no-op — the seam any future post-consume non-success exit reuses to give back the RIGHT bucket."

requirements-completed: [PAY-06]

# Metrics
duration: 34min
completed: 2026-07-03
---

# Phase 7 Plan 04: SUBSCRIPTION/PAID Consume-Gate Arms Summary

**Filled the Phase-6 SUBSCRIPTION and PAID seams in `reading.py`'s atomic consume-gate so a ЮKassa-granted pack or «Лунный доступ» subscription is spendable through the same gate (free→subscription→paid, D-11) — each bucket consumed via its own atomic `UPDATE ... RETURNING`, the subscription arm reading Plan-03's window-gated `SUBSCRIPTION_WINDOW_UNLIMITED` contract by name, and the honest-fail path now refunding the bucket that was ACTUALLY consumed — plus the `get_payment_service` DI seam mirroring `get_reading_service`.**

## Performance

- **Duration:** ~34 min
- **Tasks:** 2
- **Files modified:** 2 (1 created `app/api/payments.py` + 1 modified `services/reading.py`)

## Accomplishments

- **SUBSCRIPTION/PAID arms filled (Task 1):** `_consume_free_gate` now routes all four buckets in the D-11 order. Added `_consume_subscription_atomic` (window-gated: `UPDATE ... WHERE subscription_spreads_used < subscription_spreads_limit ... RETURNING`, the count-atomic UPDATE existing only to serialize concurrent reads via the PG row lock — the window is the real bound) and `_consume_paid_atomic` (`UPDATE ... WHERE paid_spreads_balance > 0 ... RETURNING`, returning the post-decrement balance). Both mirror `_consume_free_atomic` exactly: no `SELECT`-then-`UPDATE`, no rowcount — "no slot" is always the absent RETURNING row. The FREE arm is unchanged.
- **Gate return widened to thread the consumed bucket:** `tuple[Bucket, int | None] | None`. `create_reading` unpacks `consumed_bucket, remaining` and threads `consumed_bucket` into `_honest_fail`. The paywall / `remaining` / unlimited-allowlist behavior is preserved.
- **Bucket-aware honest-fail refund (Task 2):** added `_refund_subscription` (`subscription_spreads_used -= 1`) and `_refund_paid` (`paid_spreads_balance += 1`), both mirroring `_refund_free`, plus `_refund_consumed_bucket` which routes the compensating refund to the bucket ACTUALLY consumed. `_honest_fail` now takes `consumed_bucket` and refunds the matching bucket in-transaction (READ-10 net-unchanged), never free by default (T-07-REFUND-WRONG-BUCKET). The safety-before-gate order, the crisis/abusive short-circuit (never consumes), and the unlimited-allowlist `refund=False` path are untouched.
- **`get_payment_service` dependency added:** new `backend/app/api/payments.py` exposing `get_payment_service() -> PaymentService` (default = real ЮKassa client), the direct analog of `get_reading_service` in `readings.py`. This is the `app.dependency_overrides[get_payment_service]` seam the Plan-01 conftest + `test_payments_api.py` reference; routes are Plan 05's to add onto the same `router`.

## Task Commits

1. **Task 1 + Task 2: SUBSCRIPTION/PAID arms + bucket-aware refund in reading.py** — see commit log below (single `feat` commit — the two tasks share one file and the gate-return change couples them: `_honest_fail`'s new `consumed_bucket` param is required for the module to import after Task 1 widens the gate return, so they were implemented and committed together to keep every commit importable/green).
2. **`get_payment_service` dependency (app/api/payments.py)** — separate `feat` commit.

## Files Created/Modified

- `backend/app/services/reading.py` — `_consume_free_gate` fills SUBSCRIPTION (window-gated) + PAID arms in free→sub→paid order, returning `(Bucket, remaining)`; new atomic `_consume_subscription_atomic` / `_consume_paid_atomic`; new `_refund_subscription` / `_refund_paid` / `_refund_consumed_bucket`; `_honest_fail` refunds the consumed bucket; `create_reading` threads `consumed_bucket`; `Bucket` docstring updated (arms now filled, not a "Phase-7 seam").
- `backend/app/api/payments.py` — **created**: `get_payment_service` FastAPI dependency + a `payments`-tagged `router` placeholder (Plan 05 adds routes).

## Decisions Made

- **Subscription arm consumes the D-09 contract by name, never redefines it.** `_consume_subscription_atomic` relies solely on the `subscription_spreads_used < subscription_spreads_limit` invariant that Plan-03's grant guarantees (`_limit = SUBSCRIPTION_WINDOW_UNLIMITED`, `_used = 0` per period). The sentinel is NOT imported into `reading.py` — the gate is window-gated by construction (`determine_access` selects SUBSCRIPTION only inside a live window). This honors the plan's "read it from Plan 03; do NOT redefine the encoding" constraint.
- **`remaining_limits` semantics per bucket:** FREE → free remaining (`max(0, limit-used)`, unchanged display); SUBSCRIPTION → `None` (window-gated, no count to show — matches the detail-read `remaining=None` convention); PAID → post-decrement paid balance. Documented on `_consume_free_gate`.
- **`get_payment_service` module placement.** Placed in `app/api/payments.py` (the router module), not `deps.py`, because the mirror target `get_reading_service` lives in `readings.py` and the Plan-01 test imports it from `app.api.payments`. Routes-less this plan; Plan 05 extends the same module.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Target test path corrected to `tests/integration/test_reading_buckets.py`**
- **Found during:** Task 1 (before running the RED contract)
- **Issue:** The plan's `<verify>` blocks and context reference `backend/tests/test_reading_buckets.py`; the actual file (created by Plan 01, per the 07-01 SUMMARY's own documented location fix) lives at `backend/tests/integration/test_reading_buckets.py` (co-located with `auth_session`/`seeded_catalog`/`fake_safety` + the `test_readings_flow` helpers it imports). Running the top-level path would collect nothing.
- **Fix:** Ran + verified against `backend/tests/integration/test_reading_buckets.py`. No code impact — a path correction only.
- **Verification:** `uv run pytest tests/integration/test_reading_buckets.py -q` → all 3 xpass.

**2. [Rule 2 - Missing critical infra] Created `app/api/payments.py` to host `get_payment_service`**
- **Found during:** the `get_payment_service` requirement
- **Issue:** The orchestrator success criterion + the Plan-01 conftest/tests require a `get_payment_service` dependency importable from `app.api.payments`, but that module did not exist (Plan 05 owns the routes). Without it the payment-API override seam is unreachable.
- **Fix:** Created a minimal, routes-less `app/api/payments.py` mirroring `get_reading_service` exactly (`return PaymentService()`). Plan 05 adds the routes onto the same `router`; no conflict.
- **Files modified:** `backend/app/api/payments.py` (created).
- **Verification:** `uv run pytest tests/integration/test_payments_service.py -q` → 5 xpass; `ruff check` clean.

**3. [Note - not a deviation] Tasks 1 + 2 committed as they were implemented, with the gate-return change spanning both.** The plan's two tasks both edit `reading.py` and are coupled by the gate-return widening (`_honest_fail`'s `consumed_bucket` param is required for the module to import after Task 1). Implemented together so every commit is importable and green. This is structural, not a scope change — both tasks' acceptance criteria are met.

**Total deviations:** 2 auto-fixed (1 blocking path-correction, 1 missing-infra module) + 1 structural note. No scope change — the SUBSCRIPTION/PAID arms, the correct-bucket refund, and `get_payment_service` are exactly as specified.

## Verification

- **Target RED contract → GREEN:** `tests/integration/test_reading_buckets.py` — was `2 xfailed / 1 xpassed`, now **`3 xpassed`** (subscription consume, paid consume, honest-fail-refunds-correct-bucket). These are `xfail(strict=False)`, so xpass is the non-failing "already green" state.
- **No regression to the gate invariants:** `test_readings_limit.py` + `test_readings_flow.py` + `test_paywall_block.py` → `9 passed, 2 xpassed`; `tests/unit/test_determine_access.py` → `3 xpassed`; `test_payments_service.py` → `5 xpassed` (the 07-03 service + the new `get_payment_service` seam). The Phase-4 `test_limit_untouched_on_crisis/_abusive` and Phase-6 free honest-fail invariants hold.
- **Lint clean:** `ruff check app/services/reading.py app/api/payments.py` → "All checks passed!".
- **Full-suite env caveat (pre-existing, NOT this plan):** `uv run pytest -q` reports `14 failed` — the SAME ~14 documented in 07-01/07-03: an unclean local Postgres (`ProgrammingError` / `UNIQUE (slug)` / `DuplicateTableError` on migration/seed) + no local Redis (`ConnectionError localhost:6379` in the full-app `test_readings_auth` client). Confirmed by inspecting the failures — every one is an infra/schema-setup failure at the migration/seed/Redis layer, none touch the gate logic. The deploy env (fresh DB + `YOOKASSA_*` + Redis) runs these green.

## Known Stubs

- `backend/app/api/payments.py` currently exposes only `get_payment_service` + an empty `router` (no routes). This is INTENTIONAL and by design: the `/api/products`, create-payment, IP-gated webhook, and admin-refund routes are **Plan 07-05**'s scope (the phase's route wave). The dependency seam is the only surface this plan needs so the SUBSCRIPTION/PAID gate's spendable grant is reachable through the established override. Documented in the module docstring and in `provides`/`affects` so Plan 05 extends the same module.

## Next Plan Readiness

- **Plan 07-05 (routes + `/api/me` window + async `project_limits`)** is unblocked: the consume-gate now spends sub/paid so the paid/subscription flow is end-to-end once the routes land; `get_payment_service` already exists in `app/api/payments.py` for the route + webhook + refund handlers and the test overrides.
- The gate is EXTENDED, never forked: safety-before-gate, the crisis/abusive short-circuit (zero consume), the free-quota lazy-reset atomic, and the `test_limit_untouched_on_*` invariants are all preserved.

## Self-Check: PASSED

- `backend/app/api/payments.py` — FOUND
- `backend/app/services/reading.py` (SUBSCRIPTION/PAID arms) — FOUND (`Bucket.SUBSCRIPTION`/`Bucket.PAID` arms + `_refund_consumed_bucket` present)
- `.planning/phases/07-telegram-stars-payments/07-04-SUMMARY.md` — FOUND
- Task commits — recorded in the completion output below (verified present in `git log` before the metadata commit)

---
*Phase: 07-telegram-stars-payments*
*Completed: 2026-07-03*
