---
plan: 07-06
title: APScheduler recurring-renewal sweep
status: complete
requirements-completed: [PAY-06]
completed: 2026-07-03
commit: fb04f1c
---

# 07-06 — APScheduler recurring-renewal sweep (SUMMARY)

**Checkpoint (Task 1):** the developer **approved** adding `APScheduler` (via AskUserQuestion,
"APScheduler (recommended)"). Evidence presented: `APScheduler 3.11.x`
(github.com/agronholm/apscheduler, maintainer agronholm, 3.x since 2015, Py3.12 ✓, broker-free —
respects the Celery/RQ/Arq ban D-08). Executed inline (the spawned executor kept hitting provider
session limits; inline avoids that).

## What shipped
- **`backend/pyproject.toml`** — `"APScheduler>=3.11,<4"` with a lock-once comment; `uv sync`
  installed `apscheduler==3.11.3` (+ tzlocal/tzdata). `uv.lock` updated.
- **`backend/app/core/scheduler.py`** (new) — in-process `AsyncIOScheduler` (in-MEMORY, NO PG
  jobstore, since a daily idempotent sweep self-heals a missed tick):
  - `sweep_due_subscriptions(*, service=None, session=None)` — the daily job. In production it
    builds a `PaymentService` + opens its OWN `AsyncSession` from `SessionLocal` (runs outside a
    request); the `service`/`session` seams exist ONLY for tests (inject `FakeYooKassa` + the
    isolated session). Loops the due set, charging each via `renew_subscription` inside a per-sub
    `try/except` (T-07-SWEEP-ABORT — one failed charge never aborts the sweep); returns a
    `{due, charged, failed}` summary.
  - `start_scheduler()` / `shutdown_scheduler()` — lifespan hooks; daily `interval` job
    (`misfire_grace_time=6h`, `coalesce=True`, fixed id + `replace_existing`). Start NEVER raises
    into boot (logged + swallowed — the lazy consume-gate stays the correctness floor).
- **`backend/app/services/payments.py`** — `PaymentService.find_due_subscriptions(session, *, now=None,
  grace_days=0)`: ACTIVE subs with `current_period_end <= now + grace` (tz-aware). CANCELED / EXPIRED
  / PAYMENT_FAILED are NEVER re-charged (cancel keeps access to period end via the gate, D-10).
- **`backend/app/main.py`** — lifespan: `start_scheduler()` after `init_sentry()`,
  `shutdown_scheduler()` in `finally` (alongside `engine.dispose()` / `redis_client.aclose()`).
- **`backend/tests/integration/test_payments_scheduler.py`** (new) — 3 tests (all via FakeYooKassa,
  no live charge): due-selection (only ACTIVE + past-window), deterministic-key charge
  (`renew:<sub_id>:1` + saved `payment_method_id`, no confirmation), per-subscription failure
  isolation (one charge fails → that sub PAYMENT_FAILED, the OTHER still charged, sweep completes).

## Security (threat register)
- **T-07-DOUBLE-CHARGE** — the renewal reuses the deterministic per-period Idempotence-Key
  `renew:<sub_id>:<period_index>` (ЮKassa 24h idempotency), so an overlapping/re-run tick is a no-op.
- **T-07-SWEEP-ABORT** — per-subscription `try/except`; `renew_subscription` additionally swallows a
  charge failure internally (→ PAYMENT_FAILED, keep access D-10).
- **T-07-SC** — package legitimacy human-gate before the dep was added (Task 1).
- **T-07-MULTI-INSTANCE** — accepted for the single-container timeweb deploy (A2); the documented
  swap if it ever scales is a timeweb cron hitting one endpoint (the charge logic already lives in
  the service, so only the trigger moves).

## Verification
- **Scheduler tests:** `test_payments_scheduler.py` → **3 passed**. Import smoke
  (`find_due_subscriptions` + `sweep_due_subscriptions` coroutine) prints `scheduler ok`.
- **No regression (standalone):** `test_payments_service` 5 xpassed, `test_payments_api` 6 xpassed,
  `test_reading_buckets`/`test_me`/`test_auth_flow` green. `ruff check` clean on
  scheduler.py / main.py / payments.py / the test.
- **Test-isolation note (pre-existing, NOT 07-06):** running `test_payments_service` in the SAME
  process before `test_payments_api` flips the api tests back to xfail (a products-slug pollution
  between the Plan-01/03 fixtures). Each suite is green standalone (CI runs a clean DB); none of
  07-06's files (scheduler + the service query) touch that seeding. Cleaned the local `zerkalo`
  billing tables (disposable, re-seeds on boot) to demonstrate green.
- Lifespan wiring does not run under the test ASGITransport (no LifespanManager), so the scheduler
  never starts during the suite — zero interference.

## Downstream
- **07-07** (shop UI, last plan): `ShopTariffs` in the PaywallSheet + Profile consuming
  `GET /api/products` + `POST /api/payments/create` (`openLink(confirmation_url)` → poll `GET /api/me`)
  + the `subscription_active`/`subscription_period_end` window badge. Cancel via
  `POST /api/subscriptions/{id}/cancel`.
