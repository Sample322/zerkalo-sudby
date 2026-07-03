---
plan: 07-07
title: ЮKassa shop UI (ShopTariffs + PaywallSheet + Profile)
status: complete
requirements-completed: [PAY-01, PAY-08]
completed: 2026-07-03
commit: e9a0a21
---

# 07-07 — ЮKassa shop UI (SUMMARY)

**Note:** executed inline by the orchestrator (the spawned executors kept hitting provider session
limits; inline has run clean for 07-04..07-07). The only user-visible deliverable of the phase.

## What shipped
**Shop API + hooks + bridge (Task 1)**
- `frontend/src/api/payments.ts` — `fetchProducts`, `createPayment` (slug-only body, NO amount —
  T-07-AMOUNT), `cancelSubscription`, `PaymentError` (mirrors `MeError`).
- `frontend/src/hooks/usePayments.ts` — `useProducts` (server state), `useCreatePayment`,
  `usePollMeUntilGranted` (polls `GET /api/me` until the webhook-granted balance/sub appears, first
  check immediate, bounded — D-07, never self-grants), `useCancelSubscription`.
- `frontend/src/lib/telegram.ts` — `openLink` (hands off to the ЮKassa-hosted page; **not**
  `openInvoice` — the v3 flow is a redirect, Pitfall 7) + `onActivated` (Bot API 8.0 `activated`
  event + `visibilitychange` fallback → detect return, then poll). Optional-chained no-ops outside
  Telegram.
- `frontend/src/api/auth.ts` — `SessionLimits` += `subscription_active?`/`subscription_period_end?`/
  `subscription_id?`.
- `frontend/src/reading/copy.ts` — `SHOP_*` constants (SAFE-06, honest-fail «деньги не списаны»,
  D-13); `frontend/src/reading/limitCopy.ts` — `formatRub`/`formatSpreads`/`formatDays` (pure,
  NaN-guarded).

**ShopTariffs + wiring (Task 2)**
- `frontend/src/components/shop/ShopTariffs.tsx` — reusable presentational surface: renders
  `useProducts` as tariff cards (title + hint + «NN ₽» + `SHOP_BUY_CTA`); buy → `createPayment` →
  `openLink(confirmation_url)` → `onActivated` → `usePollMeUntilGranted` (pack: balance grew; sub:
  `subscription_active`) → `SHOP_SUCCESS`, or `SHOP_FAILURE` on create-error/poll-timeout. `variant:
  "sheet" | "profile"` + `onClose`.
- `frontend/src/components/PaywallSheet.tsx` — the dead `PAYWALL_SOON_NOTE` block REPLACED with
  `<ShopTariffs variant="sheet" onClose={onDismiss} />` (scrim/dismiss/safe-area preserved, D-12).
- `frontend/src/components/profile/ProfileScreen.tsx` — new «Баланс / Магазин» section: paid balance
  + (if active) «Лунный доступ — активна до DD.MM» + «Отменить продление» (`cancelSubscription`) +
  `<ShopTariffs variant="profile" />`. Identity/toggles/admin intact.
- `frontend/src/components/shop/ShopTariffs.test.tsx` — 4 tests (renders tariffs; buy→openLink;
  activated+granted→success; create-fail→honest failure + no openLink), all network-mocked.

**Backend enabler (small, cross-cutting):** `LimitsOut` += `subscription_id`; `project_limits`
surfaces the active subscription's id from the same live-window query (`_active_subscription_end` →
`_active_subscription`, returns the row). Without it the FE cancel has no id to target.

## Verification
- **Frontend:** full `npx vitest run` → **123 passed / 20 files** (incl. the 4 new ShopTariffs tests
  + the brand-token `copy.test.ts`). `npx tsc --noEmit` clean; `npx vite build` succeeds;
  `grep openInvoice src` → nothing (Pitfall 7).
- **Backend:** `test_me` + `test_auth_flow` → 10 passed / 1 xpassed (the `subscription_id` addition
  is additive, defaults None); `ruff check` clean on the two backend files.
- **Test-stub fix (Rule 2):** `ProfileScreen.test.tsx`'s fetch stub now returns an empty
  `/api/products` list — ProfileScreen legitimately fetches the catalog now that it embeds
  `ShopTariffs` (without it the mounted shop's `products.map` crashed the existing profile tests).

## Deviations (1)
1. **[Rule 2] Backend `subscription_id` on `LimitsOut` + `project_limits`** (outside the plan's
   FE-only file set). The plan's Profile «Отменить продление» calls `POST /api/subscriptions/{id}/
   cancel`, but `/api/me` carried no subscription id — the FE could not target the cancel. The
   backend is the right place to surface it (the projection already queries the active row); a ~6-line
   additive change. Documented; defaults None for non-subscribers (no schema break).

## Phase 7 status
**07-07 is the last plan — Phase 7 (ЮKassa payments) is fully executed (7/7).** The money path is
now end-to-end: catalog → create (server-priced, no grant) → ЮKassa page → webhook grant (re-fetch,
idempotent, IP-gated) → consume-gate buckets → recurring sweep → refund → shop UI (buy/poll/cancel).

## Downstream (post-execution, not this plan)
- `/gsd-verify-work` for Phase 7; the standing debt `/gsd-code-review` + `/gsd-secure-phase` for
  Phases 4/5/6/7; secret rotation + ЮKassa merchant (shopId/secret, webhook, 54-ФЗ receipts) before
  a public launch; live HUMAN-UAT against the ЮKassa **test shop** (real confirmation_url + a
  simulated webhook), then a small real-ruble smoke.
