---
plan: 07-03
title: ЮKassa money-path service
status: complete
requirements-completed: []
completed: 2026-06-29
commit: ac6bb3b
---

# 07-03 — ЮKassa money-path service (SUMMARY)

**Note:** finalized by the orchestrator (safe-resume). The executor implemented the service but hit
a provider session limit twice before committing; the code + tests were verified green and
committed as `ac6bb3b`.

## What shipped
`backend/app/services/payments.py` — the money-path core:
- **create payment** — server-recomputes price from the `products` row (T-07-AMOUNT: `CreatePaymentIn`
  carries no client amount); returns ЮKassa `confirmation_url`. No entitlement granted on create.
- **webhook grant** — grants ONLY on a re-`GET /v3/payments/{id}` `succeeded` from the API, never the
  unsigned webhook body (T-07-FORGERY). Idempotent via UNIQUE `provider_payment_id` + the atomic
  `UPDATE ... WHERE status=CREATED ... RETURNING` idiom (mirrors `reading.py`) → grant exactly once on
  redelivery (T-07-REPLAY).
- **recurring** — merchant-initiated saved-card charge (`payment_method_id`); subscription is
  **window-gated unlimited** (`SUBSCRIPTION_WINDOW_UNLIMITED` sentinel, D-09 owned here);
  `subscription_spreads_used` reset to 0 on grant/renewal.
- **refund** — decrements `paid_spreads_balance` by `Product.spreads_amount` (clamped ≥0), NOT the RUB
  amount (T-07-REFUND-OVERCREDIT).
- Official `yookassa` SDK (sync) wrapped in `anyio.to_thread.run_sync`.
- **migration 0004 (amended):** subscription timestamp columns → tz-aware (`TIMESTAMP(timezone=True)`)
  so grant/renewal `datetime.now(UTC)` comparisons don't mix naive/aware (real bug the recurring path
  would hit; additive-only, no live rows).

## Verification
- `payments_service` + `payments_api` RED tests (07-01) → **green** (6 xpassed); ruff clean on all
  changed files. The 8 still-`xfailed` tests are 07-04 (bucket consume) + 07-05 (routes) targets —
  correctly still red until those plans land.
- **Env caveat:** the broader DB-integration suite can't run locally here — a stray local Postgres is
  unclean (`DuplicateTableError: "topics" already exists`) and `YOOKASSA_SECRET_KEY` is unset →
  config fail-fast blocks `alembic`/app import. These 14 failures are ENVIRONMENT, not 07-03 logic
  (deploy sets `YOOKASSA_*` + migrates a fresh DB on boot). Full green requires the deploy env or
  local YOOKASSA_* + a clean test DB.

## Requirements
PAY-02/04/05/06/07 are delivered at the **service layer** here; they flip to Complete when 07-04
(gate) + 07-05 (API) wire them end-to-end. `requirements-completed: []` reflects that (service is
the substrate, not the user-facing delivery).

## Downstream
- 07-04: fill the SUBSCRIPTION/PAID seams in `reading.py` consuming `SUBSCRIPTION_WINDOW_UNLIMITED`
  (window-gated), expose `get_payment_service` dep.
- 07-05: routes (`/api/products`, create-payment, webhook IP-gated, refund) + async `project_limits`
  + `/api/me` window.
