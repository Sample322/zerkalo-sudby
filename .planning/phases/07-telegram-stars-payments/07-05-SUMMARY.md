---
plan: 07-05
title: ЮKassa HTTP surface + live subscription window
status: complete
requirements-completed: [PAY-01, PAY-02, PAY-03, PAY-04, PAY-05, PAY-07]
completed: 2026-07-03
commit: 2973d52
---

# 07-05 — ЮKassa HTTP surface + live subscription window (SUMMARY)

**Note:** executed inline by the orchestrator (safe-resume). The spawned executor hit a provider
session limit immediately (10 tool-uses, no commits); the working tree was clean at `e1e34c7`
(07-04), so this plan was implemented directly, verified green, and committed as `2973d52`.

## What shipped
The thin HTTP surface wiring the money-path end-to-end (all logic stays in `PaymentService`
Plan 03 / the gate Plan 04):

**`backend/app/api/payments.py`** — routes added onto the existing router (07-04's
`get_payment_service` seam kept):
- `GET /api/products` (behind `get_current_user`) — active products only; `ProductOut` maps
  `stars_price`→`price_rub`.
- `POST /api/payments/create` — resolves the product by slug (active-only → 404), delegates to
  `create_payment`; returns `{confirmation_url, payment_id, provider_payment_id}`. User = JWT `sub`
  (T-07-IDOR); no client amount (T-07-AMOUNT); NEVER grants (Pattern 2).
- `POST /api/payments/yookassa/webhook` — **IP-allowlist gate** (`is_from_yookassa`, left-most
  `X-Forwarded-For` behind the timeweb proxy) rejects non-ЮKassa sources with 403 **before** any
  re-fetch/DB work (T-07-WEBHOOK-FORGE/DOS); delegates to `handle_webhook_event` (the body-status-
  blind, re-fetch-before-grant dispatcher, D-05). **Always 200** on handled/duplicate (T-07-REPLAY);
  500 only on a genuine processing failure (so ЮKassa retries).
- `POST /api/payments/{payment_id}/refund` — behind `require_admin` (T-07-IDOR); typed UUID path
  (malformed → 422, missing → 404); delegates to `refund_payment` (claws back granted units, not
  RUB). Optional body (`None` ⇒ full refund).
- `POST /api/subscriptions/{subscription_id}/cancel` — JWT-scoped (non-owned → 404, no leak); flips
  `CANCELED` + `canceled_at`, KEEPS `current_period_end` (access to period end, D-10).

**`backend/app/main.py`** — `app.include_router(payments.router, prefix="/api")`.

**`backend/app/services/telegram_auth.py`** — `project_limits` is now **async + session-aware**:
for a real limits row it reads the user's live subscription window (`_active_subscription_end`:
ACTIVE + `current_period_end > now`, **tz-aware** compare) and fills
`subscription_active`/`subscription_period_end`. Both call sites migrated to `await` +
pass `session`: `users.get_me` (`GET /api/me`) and `auth.auth_telegram` (`POST /api/auth/telegram`).

## Verification
- **Target RED → GREEN:** `tests/integration/test_payments_api.py` → **6 xpassed** (products,
  create-no-grant, recompute-price, webhook-grant-on-refetched-succeeded, webhook-idempotent+IP-gated,
  refund-requires-admin).
- **No regression:** `test_reading_buckets` + `test_payments_service` + `test_auth_flow` + `test_me`
  + `test_settings_patch` + `test_paywall_block` + `test_readings_limit` = 16 passed / 12 xpassed /
  2 xfailed (the 2 are `test_settings_patch`'s "pending 05-03" Phase-5 targets — unrelated to this
  plan, pre-existing). `ruff check` clean on all 6 changed files.
- **Local-DB hygiene:** the local `zerkalo` test DB held **committed** leaked rows from prior seed
  runs (4 products + 3 users; `committed_seeded_catalog`'s teardown deletes the catalog but NOT
  `products`/`users`). These collided with the tests' own `_make_product`/user inserts (false
  `UniqueViolationError` at test SETUP, before any route). Cleared the billing/user tables (the DB
  is disposable + re-seeds on boot) to demonstrate real green; the routes were never implicated.

## Deviations (2, both auto-fixed + documented)
1. **[Rule 2] `CreatePaymentIn` `extra="forbid"` → `extra="ignore"`** (schemas/payment.py, outside
   the plan's declared file set). The Plan-01 `test_create_recomputes_price` POSTs a tampered
   `{price, amount}` and asserts **200** (proving the smuggled amount is inert because the server
   recomputes from the product row). `forbid` would 422 that request, contradicting the locked test
   contract. No test asserts `forbid`. Server-authoritative price still closes T-07-AMOUNT (the
   service reads `product.stars_price`); ignoring just makes create robust to additive client fields.
2. **[Rule 2] Fixed a latent bug in the Plan-01 webhook RED tests** (test_payments_api.py). Both
   `test_webhook_*` manually inserted a second `UserLimits` for a user whose row `authenticate`
   already auto-creates (`_ensure_user_limits`, D-02) → `uq_user_limits_user_id` violation on ANY
   DB (not leaked-data). Changed them to UPDATE the auth-created row to the exhausted-free
   precondition (`free_used_this_week=3`) — the grant asserts `paid_spreads_balance`, not the free
   counter, so intent is preserved and the tests reflect correct system behavior.

## Requirements
PAY-01/02/03/04/05/07 are now delivered END-TO-END (catalog + create + webhook grant + idempotency/
IP gate + refund over HTTP, on the Plan-03 service + Plan-04 gate). PAY-06 (recurring renewal) is
the service method `renew_subscription` (Plan 03) awaiting its **scheduler/trigger** — Plan 07-06
(CHECKPOINT: approve/lazy-only/cron).

## Downstream
- **07-06** (recurring scheduler, autonomous:false CHECKPOINT): decide how `renew_subscription` is
  triggered for due subscriptions (lazy-on-access vs cron sweep) + wire it. `GET /api/me` already
  exposes the window the shop reads.
- **07-07** (shop UI): `ShopTariffs` in the PaywallSheet + Profile, consuming `GET /api/products`
  (`price_rub`) + `POST /api/payments/create` (`openLink(confirmation_url)` then poll `GET /api/me`)
  + the `subscription_active`/`subscription_period_end` window badge.
