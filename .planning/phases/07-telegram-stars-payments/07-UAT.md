---
status: partial
phase: 07-telegram-stars-payments
source: [07-01-SUMMARY.md, 07-02-SUMMARY.md, 07-03-SUMMARY.md, 07-04-SUMMARY.md, 07-05-SUMMARY.md, 07-06-SUMMARY.md, 07-07-SUMMARY.md]
started: 2026-07-03
updated: 2026-07-03
---

## Current Test

[testing complete — all live tests deploy-gated; run post-deploy against the ЮKassa test-shop]

## Note

Phase 7 is the ЮKassa money path. It is **fully implemented + committed on `master`** and **green under
automated tests** (backend: payments_api 6 xpassed, payments_service 5 xpassed, reading_buckets 3
xpassed, scheduler 3 passed, test_me/auth_flow green, ruff clean; frontend: 123 vitest passed, tsc
clean, vite build OK, no `openInvoice`). But it is **NOT deployed and NOT user-testable locally**: it
needs (a) a ЮKassa merchant (`YOOKASSA_SHOP_ID` + `YOOKASSA_SECRET_KEY` + a webhook URL — test-shop for
UAT), and (b) the NL apps redeployed with those env vars (local has no Docker + no ЮKassa creds, so the
DB-integration suite skips, as in P1–6). Every user-facing test below is therefore recorded `blocked`
(deploy / third-party prereq), mirroring the 04/05/06-HUMAN-UAT pattern. Re-run `/gsd-verify-work 7`
after deploy + test-shop wiring to convert these to live pass/fail.

## Tests

### 1. Cold Start Smoke Test
expected: Redeploy the backend with `YOOKASSA_*` env set. The container boots without errors, `alembic upgrade head` applies migration 0004 (provider_payment_id UNIQUE / payment_method_id / confirmation_url / RUB defaults / subscriptions.telegram_payment_charge_id nullable / tz-aware sub timestamps), the seed loads the 4 products (pack_1=69 / pack_3=169 / pack_10=449 / sub_moon=299 ₽), the APScheduler renewal sweep starts in the lifespan, and `/healthz` → `{"db":"ok","redis":"ok"}`.
result: blocked
blocked_by: server
reason: "Needs the NL backend redeployed with YOOKASSA_* env (config fail-fast requires the keys). Local has no Docker. Migration 0004 + seed products auto-apply on boot (docker-entrypoint) — verify in `tw.mjs logs 213035`."

### 2. Tariffs visible (PaywallSheet + Profile «Магазин»)
expected: In the deployed Mini App, exhaust the weekly free limit → the PaywallSheet shows the tariff list (1/3/10 packs + «Лунный доступ») with «NN ₽» prices and a per-reading / «30 дней» hint (no dead «скоро» note). Profile shows a «Баланс / Магазин» section with the same tariffs + the paid balance.
result: blocked
blocked_by: server
reason: "Needs the deployed Mini App (FE fetches GET /api/products). Frontend rendering is green under vitest (ShopTariffs.test.tsx 4/4), but the live catalog needs the deployed backend + seeded products."

### 3. Buy → ЮKassa page opens (openLink)
expected: Tapping a tariff creates a payment (`POST /api/payments/create`, slug only — no client amount) and opens the ЮKassa-hosted `confirmation_url` via Telegram `openLink` (not a Stars invoice). The «Ждём подтверждение оплаты…» pending state shows.
result: blocked
blocked_by: third-party
reason: "Needs ЮKassa test-shop creds so create returns a real confirmation_url. Server-authoritative price + no-grant-on-create are green under automated tests (test_create_recomputes_price, test_create_payment_no_grant)."

### 4. Webhook grant → balance / subscription updates
expected: After paying on the ЮKassa test-shop page (test card), the webhook (`POST /api/payments/yookassa/webhook`) — IP-gated, re-fetching the payment by id — grants exactly once; returning to the Mini App and polling `GET /api/me` shows the increased paid balance (pack) or the active subscription window «активна до DD.MM».
result: blocked
blocked_by: third-party
reason: "Needs a live ЮKassa test-shop webhook hitting the deployed backend. Grant-on-re-fetched-succeeded + idempotency + IP-gate are green under automated tests (test_webhook_grants_on_refetched_succeeded, test_webhook_idempotent_and_ip_gated)."

### 5. Honest failure on decline
expected: If the payment is cancelled / the poll times out, the shop shows «Оплата не прошла — деньги не списаны, доступ не выдан» (no charge, no grant, no AI/brand tokens) — never a scary alarm.
result: blocked
blocked_by: third-party
reason: "Needs a live declined-payment flow. The honest-failure copy + no-openLink-without-url path are green under automated tests (ShopTariffs create-failure test) + the SAFE-06 brand scan (copy.test.ts)."

### 6. Recurring renewal sweep
expected: A due «Лунный доступ» subscription (ACTIVE, `current_period_end` passed) is charged by the daily APScheduler sweep via the saved card (deterministic key `renew:<sub>:<period>`, no double-charge); a failed charge sets PAYMENT_FAILED but keeps access to period end, and one failure does not abort the sweep.
result: blocked
blocked_by: third-party
reason: "Needs a deployed instance + a saved-card subscription + a due window (or a manual sweep trigger). Sweep due-selection + deterministic-key charge + per-sub failure isolation are green under automated tests (test_payments_scheduler 3/3)."

### 7. Admin refund
expected: An admin `POST /api/payments/{id}/refund` refunds at ЮKassa and claws back the granted entitlement (decrements paid_spreads_balance by the pack's spreads, never the RUB amount); a non-admin JWT → 403.
result: blocked
blocked_by: third-party
reason: "Needs a live PAID payment to refund + admin JWT. Admin-gate + refund-by-entitlement are green under automated tests (test_refund_requires_admin, test_refund_recon_flips_status_and_adjusts_access)."

### 8. Self-serve subscription cancel
expected: In Profile, «Отменить продление» calls `POST /api/subscriptions/{id}/cancel`; the subscription flips to CANCELED but access is kept until `current_period_end` (the sweep won't recharge a canceled row).
result: blocked
blocked_by: server
reason: "Needs an active subscription in the deployed app. Cancel-keeps-access-to-period-end (D-10) + JWT-scoping are wired (07-05 route); the FE cancel targets limits.subscription_id (07-07 backend addition)."

## Summary

total: 8
passed: 0
issues: 0
pending: 0
blocked: 8
skipped: 0

## Gaps

[none — no code issues found; all 8 tests are deploy/third-party prereq gates, not defects]
