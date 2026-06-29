---
phase: 07-telegram-stars-payments
plan: 01
subsystem: testing
tags: [yookassa, payments, pytest, idempotency, webhook, fakes, tdd, wave-0]

# Dependency graph
requires:
  - phase: 06-free-limits-soft-paywall
    provides: "the atomic consume-gate + Bucket(free→subscription→paid) seam in reading.py, the FakeLLM/FakeSafety dependency_overrides pattern, the seeded_catalog/auth_session test substrate"
  - phase: 01-foundation
    provides: "billing.py models (Product/Payment/Subscription/UserLimits), payments.payload UNIQUE + charge-id index + raw_update JSONB, the fail-fast config.Settings() spine"
provides:
  - "FakeYooKassa — the no-real-charge ЮKassa client stand-in (create_payment/find_payment/create_refund/find_refund) with controllable re-fetch status + recorded_calls"
  - "fake_yookassa pytest fixture + the get_payment_service dependency_overrides seam (mirrors get_reading_service)"
  - "YOOKASSA_SHOP_ID / YOOKASSA_SECRET_KEY test env defaults so the Plan-02 fail-fast config imports under test"
  - "14 named red tests (xfail targets) covering PAY-01..07 + subscription/paid bucket consume + correct-bucket refund — the green targets Plans 03/04/05 turn green"
affects: [07-02, 07-03, 07-04, 07-05, payments, yookassa]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "FakeYooKassa is the ONLY ЮKassa surface in the suite (no real SDK import, no live host) — the test-harness→ЮKassa trust boundary is severed at the fake (T-07-TEST-LIVE); a grep gate asserts it"
    - "Red tests import not-yet-existing symbols (PaymentService / get_payment_service / app.api.payments) INSIDE the test body so collection never errors; module-level imports use only existing models/enums/fakes"
    - "Service-name-agnostic resolution helper (_resolve) keeps xfail tests documenting the CONTRACT without hard-coding a method name Plan 03 is free to finalize (and stays clear of ruff B009)"

key-files:
  created:
    - "backend/tests/integration/fakes_payments.py — FakeYooKassa stand-in + ЮKassa-shaped SimpleNamespace objects with .json() accessor"
    - "backend/tests/integration/test_payments_service.py — 5 red service tests (grant/idempotency/recurring/refund)"
    - "backend/tests/integration/test_payments_api.py — 6 red route tests (products/create/webhook/refund + IP gate)"
    - "backend/tests/integration/test_reading_buckets.py — 3 red gate tests (subscription/paid consume + correct-bucket refund)"
  modified:
    - "backend/tests/conftest.py — added YOOKASSA_SHOP_ID/YOOKASSA_SECRET_KEY to _TEST_ENV_DEFAULTS"
    - "backend/tests/integration/conftest.py — fake_yookassa fixture + FakeYooKassa re-export + the dependency_overrides seam note"

key-decisions:
  - "Test files placed under backend/tests/integration/ (NOT the top-level backend/tests/ the plan frontmatter listed) so they reuse the established auth_session/seeded_catalog/fake_safety fixtures + the _history_helpers/test_readings_flow shared helpers that live there — placing them top-level would orphan them from the fixture seam the plan mandates"
  - "FakeYooKassa.find_payment status is construction-time controllable (succeeded=/next_status=) so a single fake drives both the grant and the no-grant (pending/canceled) branches; recorded_calls captures every call so a test asserts the deterministic recurring key + the server-recomputed amount"
  - "The two forbidden grep literals (live ЮKassa host + an import of the SDK) are deliberately kept out of every docstring/comment in backend/tests so the acceptance-criteria grep gates stay green"

patterns-established:
  - "get_payment_service dependency_overrides seam: a test injects PaymentService(yookassa=FakeYooKassa(...)) exactly like ReadingService(safety=FakeSafety(), llm=FakeLLM(...)) — the established no-network seam, now for payments"
  - "ЮKassa-shaped fake objects: SimpleNamespace with id/status/amount{value,currency}/confirmation{confirmation_url}/payment_method{id,saved}/metadata + a json() returning the dict for the payments.raw_update audit column"

requirements-completed: []

# Metrics
duration: 19min
completed: 2026-06-29
---

# Phase 7 Plan 01: ЮKassa Wave-0 RED Test Substrate Summary

**A FakeYooKassa client stand-in + 14 named xfail tests fixing the ЮKassa contract first — idempotent grant-only-on-refetched-succeeded, server-authoritative price, deterministic recurring key, refund reconciliation, and subscription/paid bucket consume — with zero real-charge surface in the suite.**

## Performance

- **Duration:** ~19 min
- **Started:** 2026-06-29T09:38Z
- **Completed:** 2026-06-29T09:57Z
- **Tasks:** 2
- **Files modified:** 6 (3 created test files + 1 created fakes module + 2 conftest edits)

## Accomplishments
- `FakeYooKassa` — the single no-real-charge ЮKassa surface for the whole phase: async-compatible `create_payment` / `find_payment` / `create_refund` / `find_refund`, controllable re-fetch status (`succeeded=`/`next_status=`), saved-method id for recurring (PAY-06), and an ordered `recorded_calls` audit so tests assert the deterministic recurring Idempotence-Key and the server-recomputed amount. No real ЮKassa SDK import anywhere in `backend/tests`.
- conftest wiring: `YOOKASSA_SHOP_ID`/`YOOKASSA_SECRET_KEY` added to `_TEST_ENV_DEFAULTS` (so Plan-02's fail-fast config imports under test), a `fake_yookassa` fixture, and a documented `get_payment_service` `dependency_overrides` seam mirroring `get_reading_service`.
- 14 red tests, every PAY-0x behavior + the subscription/paid bucket consume + correct-bucket refund present by name and the green target for Plans 03/04/05:
  - service (5, Plan 03): grant-on-refetched-`succeeded`, **THE** idempotent-redelivery no-double-grant, no-grant-on-unconfirmed-status, deterministic recurring key (`renew:<sub_id>:<period_index>`), refund reconciliation;
  - route (6, Plan 04): `GET /api/products` active-only, create→`confirmation_url` + NO grant, server-recomputed price + inactive→4xx, webhook grant-on-refetch, webhook idempotent + IP-gated (body status never trusted), refund `require_admin`;
  - gate (3, Plan 05): subscription/paid bucket consume + honest-fail refunds THE consumed bucket (free→sub→paid, D-11).
- Full backend suite green and baseline preserved: **84 passed / 91 skipped / 3 xpassed**, exit 0; both acceptance-criteria grep gates return nothing.

## Task Commits

Each task was committed atomically:

1. **Task 1: FakeYooKassa client + conftest fixture (the no-real-charge seam)** - `65fdf5f` (test)
2. **Task 2: Red test files for PAY-01..07 + bucket consume (xfail targets)** - `ba3bf5b` (test)

**Plan metadata:** _(this commit)_ (docs: complete plan)

## Files Created/Modified
- `backend/tests/integration/fakes_payments.py` - `FakeYooKassa` stand-in: the 4 ЮKassa ops returning ЮKassa-shaped `SimpleNamespace` objects (`id`/`status`/`amount`/`confirmation`/`payment_method`/`metadata` + a `json()` accessor), controllable status, `recorded_calls`. Never imports the real SDK.
- `backend/tests/integration/test_payments_service.py` - 5 xfail service tests (grant idempotency, recurring key discipline, refund reconciliation) driving the future `PaymentService` via the injected fake.
- `backend/tests/integration/test_payments_api.py` - 6 xfail route tests through `auth_client` + a real Bearer JWT + the admin monkeypatch, with the `get_payment_service` override injecting the fake.
- `backend/tests/integration/test_reading_buckets.py` - 3 xfail gate tests EXTENDING (not duplicating) the Phase-6 free tests: the SUBSCRIPTION/PAID arms of `_consume_free_gate` + correct-bucket refund.
- `backend/tests/conftest.py` - added the two ЮKassa fail-fast config secrets to `_TEST_ENV_DEFAULTS` (test-only dummies; T-07-SECRET-LEAK).
- `backend/tests/integration/conftest.py` - `fake_yookassa` fixture + `FakeYooKassa` re-export + the `dependency_overrides` seam note for Plans 03/04.

## Decisions Made
- **Test-file location corrected to `tests/integration/`** (the plan frontmatter listed top-level `backend/tests/`): the fixtures these tests depend on (`auth_session`, `seeded_catalog`, `fake_safety`, the new `fake_yookassa`) and the reused helpers (`_output_for_indices`, `_spread_position_indices`, `_AlwaysInvalidClient` from `test_readings_flow`) all live under `tests/integration/`. The plan explicitly mandates "mirror the Phase-6 Wave-0 stub pattern" and "use the existing `db_session`/`_db_ready` fixtures" — both only reachable from `tests/integration/`. Placing the files top-level would have broken that seam.
- **FakeYooKassa status is construction-time controllable** so one fake drives both grant and no-grant branches; `recorded_calls` is the single assertion surface for the deterministic recurring key + the server-recomputed RUB amount (`"299.00"`).
- **Forbidden grep literals kept out of all docstrings/comments** in `backend/tests` so the acceptance-criteria gates (`import yookassa`, the live host string) stay clean even though the fakes module documents that those literals are banned.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test files placed under `tests/integration/` instead of the top-level path in the plan frontmatter**
- **Found during:** Task 2 (red test files)
- **Issue:** The plan's `files_modified` frontmatter listed the four test files at `backend/tests/<file>.py`. The fixtures + shared helpers they MUST reuse (per the plan body: the Phase-6 Wave-0 stub pattern, `auth_session`/`seeded_catalog`/`fake_safety`, `_output_for_indices`/`_AlwaysInvalidClient`) live exclusively under `backend/tests/integration/`. Top-level placement would orphan the tests from the fixture seam and break collection/imports.
- **Fix:** Created the three test files under `backend/tests/integration/` (and the fakes module there too, next to `FakeLLM`/`FakeSafety`). The `conftest.py` env-var edit stayed at the root `backend/tests/conftest.py` exactly as the plan specified (that is where `_TEST_ENV_DEFAULTS` + the import-before-app env pattern lives).
- **Files modified:** `backend/tests/integration/{fakes_payments,test_payments_service,test_payments_api,test_reading_buckets}.py`
- **Verification:** `uv run pytest tests/ --co` collects all new files with zero errors (164 → 178 tests); full suite exit 0.
- **Committed in:** `65fdf5f` + `ba3bf5b` (Task 1 + Task 2 commits)

**2. [Rule 1 - Bug] Reworded fakes/conftest docstrings to keep the banned grep literals out of `backend/tests`**
- **Found during:** Task 1 (FakeYooKassa)
- **Issue:** My initial `fakes_payments.py` + integration-conftest docstrings spelled out the two forbidden strings (the live ЮKassa host and `import yookassa`) while describing the grep gate — which itself tripped the very acceptance-criteria gates (`grep -rn "import yookassa" backend/tests` / the live-host string must return nothing).
- **Fix:** Reworded both docstrings to reference the literals descriptively without spelling them out.
- **Files modified:** `backend/tests/integration/fakes_payments.py`, `backend/tests/integration/conftest.py`
- **Verification:** `grep` for both literals across `backend/tests` returns 0 matches.
- **Committed in:** `65fdf5f` (Task 1 commit)

**3. [Rule 3 - Blocking] Replaced `getattr(obj, "constant")` fallbacks with a name-variable `_resolve` helper (ruff B009)**
- **Found during:** Task 2 (service tests)
- **Issue:** The defensive `getattr(service, "handle_webhook_event", None) or getattr(service, "handle_payment_succeeded")` pattern (used so the xfail tests don't hard-code a method name Plan 03 finalizes) trips ruff `B009` ("Do not call getattr with a constant attribute value"). The pre-commit hook runs lint, so this would block the commit.
- **Fix:** Added a `_resolve(obj, *names)` helper that resolves via `getattr(obj, name)` where `name` is a runtime variable (B009-safe), and routed all five call sites through it.
- **Files modified:** `backend/tests/integration/test_payments_service.py`
- **Verification:** `uv run ruff check` on all three new files → "All checks passed!".
- **Committed in:** `ba3bf5b` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (2 blocking, 1 bug)
**Impact on plan:** All three were necessary for the plan to collect/lint/commit and to satisfy its own acceptance-criteria grep gates. No scope change — the deliverables (FakeYooKassa + conftest wiring + the 14 named red tests) are exactly as specified; only their location and a couple of docstring/lint details were corrected.

## Issues Encountered
- Postgres/Redis are not running in the execution environment, so every DB-touching new test **clean-skips** (via `seeded_catalog` → `auth_session` → `_db_ready`) rather than xfailing. This is the intended Wave-0 contract ("xfail/xpass or clean-skip without PG"): the module-level imports all resolve today, and the not-yet-existing payment symbols are imported inside the test bodies, so collection is clean (verified: all 14 collect by name) and the tests will xfail-then-xpass against the real symbols once Plans 03/04/05 land and PG is available.

## Known Stubs
None — this plan is a deliberate Wave-0 RED test substrate. The "stubs" are the xfail tests themselves, which are the intended green targets for Plans 03 (service), 04 (routes), and 05 (bucket consume). FakeYooKassa is a test double by design (the no-real-charge mandate), not production stub code.

## User Setup Required
None - no external service configuration required for this plan. (The ЮKassa merchant account + `YOOKASSA_*` production secrets + the dashboard webhook URL are owner-provisioned at deploy time, surfaced in later plans; tests use dummy values.)

## Next Phase Readiness
- The full Nyquist substrate is in place: every later payment task (Plans 03/04/05) now has an automated `<verify>` (a named xfail test) that exists BEFORE the code — turning each test green is the implementation contract.
- Plan 02 (config + migration 0004 + the `yookassa`/`APScheduler` package-legitimacy checkpoint) is unblocked: the two ЮKassa config secrets already import under test.
- The `get_payment_service` `dependency_overrides` seam name is referenced by the route tests; Plan 04 should expose exactly that dependency (mirroring `get_reading_service`) so the override wires the fake.
- Method names the service tests resolve defensively (`handle_webhook_event`/`handle_payment_succeeded`, `charge_renewal`/`renew_subscription`, `handle_refund_succeeded`) are Plan 03's to finalize; pick one of each pair and the `_resolve` helper binds it.

## Self-Check: PASSED

All claimed files exist on disk and both task commits are in git history:
- `backend/tests/integration/fakes_payments.py` — FOUND
- `backend/tests/integration/test_payments_service.py` — FOUND
- `backend/tests/integration/test_payments_api.py` — FOUND
- `backend/tests/integration/test_reading_buckets.py` — FOUND
- `.planning/phases/07-telegram-stars-payments/07-01-SUMMARY.md` — FOUND
- commit `65fdf5f` (Task 1) — FOUND
- commit `ba3bf5b` (Task 2) — FOUND

---
*Phase: 07-telegram-stars-payments*
*Completed: 2026-06-29*
