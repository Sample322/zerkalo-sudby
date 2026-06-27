# Phase 7: Telegram Stars Payments → **ЮKassa (YooKassa) Payments** - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

> ⚠️ **PROVIDER PIVOT (locked this discussion):** The roadmap/ТЗ name this phase "Telegram
> Stars Payments" and `CLAUDE.md` §Payments + ТЗ §2.2 lock **Stars-only**. The product owner has
> **decided against Stars** and chosen **ЮKassa (YooKassa) direct API** instead (RUB payouts, no
> Stars→fiat conversion/withdrawal friction). **Downstream agents: IGNORE the Telegram Stars
> implementation in CLAUDE.md / ROADMAP AC for Phase 7 — implement ЮKassa direct API per the
> decisions below.** The PAY-01..08 *intent* (products, idempotent grant-after-confirmed-payment,
> refunds, subscription entitlement window) still holds; only the provider/transport changes.

<domain>
## Phase Boundary

The user can **pay to keep reading** — buying one-time **reading packs (1 / 3 / 10)** or a
**recurring 30-day subscription «Лунный доступ»** via **ЮKassa (direct API, RUB)**. Entitlement
(`paid_spreads_balance` or an active subscription window) is granted **only after a ЮKassa-confirmed
payment**, idempotently, and is immediately usable in the existing reading-consume gate. Includes:
products/tariffs API, ЮKassa payment creation (redirect/widget `confirmation_url`), a ЮKassa
**webhook** that re-verifies payment status authoritatively before granting, recurring auto-charge
of the subscription, refunds via ЮKassa API, and the shop UI (paywall sheet + profile).

**Out of scope (this phase):** Telegram Stars, the aiogram bot module (NOT needed — ЮKassa is
direct HTTP, no Telegram Payments transport), extended history for subscribers (HIST-06), admin
product CRUD (ADMIN-06 → Phase 8), analytics events (ANALYTICS-01 → Phase 8).
</domain>

<decisions>
## Implementation Decisions

### Provider & transport
- **D-01:** Payment provider = **ЮKassa (YooKassa) direct API** (`yookassa` Python SDK or `httpx`
  to `https://api.yookassa.ru/v3`). NOT Telegram Stars, NOT Telegram Payments API / `provider_token`.
- **D-02:** Currency = **RUB** everywhere. `payments.currency` default flips `XTR`→`RUB`,
  `payments.provider` `telegram_stars`→`yookassa` (billing.py models already carry these columns).
- **D-03:** Owner accepts the moderation risk (external acquirer for a digital service inside a
  Telegram Mini App may draw Telegram-ToS scrutiny / catalog rejection on apps.pro·tApps). Decision
  is the owner's; surfaced explicitly during discussion.

### Payment flow (one-time packs)
- **D-04:** Backend creates a ЮKassa payment (amount RUB, `capture=true`, `confirmation:
  { type: "redirect", return_url }`), returns the `confirmation_url`; frontend opens it via Telegram
  `openLink` (or ЮKassa checkout widget). A per-attempt **Idempotence-Key** is sent to ЮKassa.
- **D-05:** **Webhook** (`POST /api/payments/yookassa/webhook`) receives `payment.succeeded` /
  `payment.canceled` / `refund.succeeded`. **Never trust the webhook body** — re-`GET
  /v3/payments/{id}` from ЮKassa (authenticated) and grant strictly on the API-confirmed `succeeded`
  status (defense vs forged callbacks; ЮKassa does not sign webhooks — IP allowlist + re-fetch).
- **D-06:** **Idempotent grant** — `payments.payload` UNIQUE + the ЮKassa payment id stored UNIQUE
  (reuse/rename `telegram_payment_charge_id` → a provider-agnostic `provider_payment_id`, or add a
  column via a new migration). The same event delivered twice grants access exactly once; access is
  NEVER granted on payment creation, only on confirmed `succeeded`.
- **D-07:** Frontend, after returning from ЮKassa, **polls `GET /api/me`** until the balance/sub
  updates (the webhook is the source of truth; the return_url is just UX).

### Subscription «Лунный доступ» (recurring)
- **D-08:** Recurring via ЮKassa **saved payment method**: first payment with
  `save_payment_method=true` → store `payment_method_id` on the subscription; renewals are
  **merchant-initiated** auto-charges (ЮKassa does not auto-charge — we must trigger). A
  **scheduled charge mechanism is required** (RESEARCH: in-process APScheduler vs timeweb cron vs
  lazy charge-on-access at expiry; Celery/RQ/Arq remain banned per ТЗ). DB = source of truth for the
  entitlement window (`subscriptions.current_period_end`), not ЮKassa.
- **D-09:** Subscription grants **unlimited readings for the 30-day window** (`user_limits`
  subscription bucket; simplest premium value). Extended history (HIST-06) is **deferred**.
- **D-10:** **Cancel** = stop future auto-charge (mark `subscriptions.status=canceled`,
  `canceled_at`), **keep access until `current_period_end`**. Self-serve cancel button in profile.

### Consumption order & gate (carried from Phase 6)
- **D-11:** Reading-consume order stays **free → subscription → paid packs** (Phase 6 LIMIT-04).
  Paid/subscription buckets plug into the SAME atomic consume gate (safety-before-gate, refund slot
  on honest-fail) — extend, do not fork it.

### Shop / UI
- **D-12:** Tariffs/buy shown in **BOTH** the existing soft-paywall sheet (when the weekly free
  limit is hit — Phase 6 reserved a «скоро» slot for this) **AND** a permanent «Баланс / Магазин»
  section in the Profile screen.
- **D-13:** Success / failure copy is brand-safe (SAFE-06) and honest: «звёзды не списаны»→
  «деньги не списаны / оплата не прошла — доступ не выдан» on failure; balance/sub state visible.

### Refunds
- **D-14:** **Auto refund endpoint** via ЮKassa refund API (`POST /v3/refunds`), 21-day-ish window;
  flips `payments.status=refunded`, sets `refunded_at`, and adjusts access (decrement
  `paid_spreads_balance` / end subscription). Admin-triggered for MVP (a self-serve refund button is
  optional); the webhook also handles `refund.succeeded` idempotently.

### Pricing (seed defaults — admin-tunable later)
- **D-15:** Owner wants prices **приятные для ЦА но покрывающие расходы**. Marginal cost ≈ **1–3₽**/
  reading (Haiku ~$0.01) + ЮKassa fee ~3.5%; host fixed ≈ 1500–2500₽/мес. So margin is large at any
  sane price — price for conversion/perceived value. **Recommended seed (RUB):**
  `1 расклад = 69`, `3 = 169` (≈56/шт), `10 = 449` (≈45/шт), `подписка 30д = 299/мес`. Stored as
  `products` rows → editable without code (ADMIN-06 CRUD lands Phase 8). Treat as defaults, not law.

### Claude's Discretion
- Exact ЮKassa client (official `yookassa` SDK vs thin `httpx` wrapper) — researcher/planner choose.
- Scheduler approach for recurring auto-charge (D-08) — researcher evaluates; prefer the lightest
  thing that survives the timeweb container model without a broker.
- Schema delta (rename vs add `provider_payment_id` / `payment_method_id`) — planner decides; a new
  Alembic migration (0004) is expected.
- Webhook source-verification details (ЮKassa IP ranges + re-fetch) — researcher confirms current
  ЮKassa guidance.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase intent & requirements
- `.planning/ROADMAP.md` §"Phase 7: Telegram Stars Payments" — goal + acceptance criteria (the
  PROVIDER is overridden to ЮKassa per this CONTEXT; the *intent* — idempotent grant, pre-confirm,
  refunds, subscription window — still applies).
- `.planning/REQUIREMENTS.md` PAY-01..PAY-08 — reinterpret "Stars/XTR/provider_token" as "ЮKassa
  direct API / RUB / saved payment method". PAY intent unchanged.

### Data model (already migrated in Phase 1)
- `backend/app/models/billing.py` — `UserLimits` (free/paid/subscription buckets + week_start),
  `Product` (slug/title/product_type/stars_price→price RUB/spreads_amount/subscription_days),
  `Payment` (payload UNIQUE, telegram_payment_charge_id indexed → provider_payment_id, status, raw_update
  JSONB audit), `Subscription` (current_period_start/end, status, charge id). Reuse; add ЮKassa
  fields via migration 0004.
- `backend/app/models/enums.py` — `ProductType`, `PaymentStatus`, `SubscriptionStatus` enums.

### Existing gate / surfaces to extend (do NOT rebuild)
- `backend/app/services/reading.py` — the atomic consume-gate (free-limit, UNLIMITED allowlist,
  honest-fail refund). Paid/subscription buckets plug in here (D-11).
- `backend/app/api/users.py` + `backend/app/schemas/auth.py` (`LimitsOut`) + `GET /api/me` — surfaces
  balances; extend with paid/subscription state for the shop.
- `frontend/src/components/PaywallSheet.tsx` — Phase 6 soft-paywall sheet (reserved a «скоро» slot
  for tariffs — wire buy buttons here, D-12).
- `frontend/src/components/profile/ProfileScreen.tsx` — add «Баланс / Магазин» section (D-12).
- `frontend/src/reading/limitCopy.ts` + `frontend/src/reading/copy.ts` — brand-safe limit/paywall
  copy lives here (add purchase/success/refund copy, D-13).

### Superseded (do NOT follow for the provider)
- `CLAUDE.md` §"Telegram Stars Payments — EXACT Flow" + §Payments constraint + "What NOT to Use →
  External acquirers" — **superseded by D-01** for this phase. Keep everything else in CLAUDE.md.

### Owner-provided (external, owner sets up)
- ЮKassa merchant account (ИП / самозанятость / юрлицо required for payout) → `shop_id` +
  `secret_key` (env: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`), webhook URL configured in the
  ЮKassa dashboard. ЮKassa API docs: `https://yookassa.ru/developers/api`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `billing.py` models (UserLimits/Product/Payment/Subscription) — schema already migrated Phase 1;
  idempotency columns (`payload` UNIQUE, charge-id indexed, `raw_update` JSONB) already present.
- Reading consume-gate in `services/reading.py` — extend buckets, don't fork.
- `PaywallSheet.tsx` (Phase 6) + `ProfileScreen.tsx` (Phase 5) — shop surfaces.
- `apiFetch` Bearer seam (`frontend/src/api/client.ts`) — for the buy/products/poll calls.
- `settings`/config fail-fast (`backend/app/core/config.py`) — add `YOOKASSA_*` env with presence
  validation at startup (security rule).

### Established Patterns
- SQLAlchemy 2.0 async `select()` + `AsyncSession`; Alembic migrations (next = 0004); seed via
  `app/seed/loader.py` upsert-by-slug (seed `products` rows there).
- Server-authoritative everything (cards, limits) — payments must be server-verified too (D-05).
- TanStack Query for server state (`useMe`); Zustand for UI; motion for the shop UI.

### Integration Points
- New `backend/app/api/payments.py` (products list, create-payment, webhook, refund) + a
  `services/payments.py` (ЮKassa client + grant/idempotency + recurring + refund logic).
- `GET /api/me` (LimitsOut) extended → frontend shop reads balance/sub there.
- New Alembic migration 0004 (ЮKassa fields) + seed `products`.
- Config: `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` (+ webhook secret/allowlist) in env +
  DEPLOY.md + .env.example.
</code_context>

<specifics>
## Specific Ideas

- «Лунный доступ» = the subscription's product name (already in ТЗ voice).
- Prices in round RUB; packs discount per-reading vs single (D-15).
- Buy UX must feel premium/in-character (reuse the dark-mystical surfaces + motion already built).
</specifics>

<deferred>
## Deferred Ideas

- **Telegram Stars** as an alternative/parallel rail — dropped for now (owner chose ЮKassa).
- **aiogram bot module** — the roadmap assumed "bot first appears with payments"; with ЮKassa
  direct it is NOT needed for Phase 7. Defer the bot (webhook/notifications) to a later phase if ever.
- **Extended history for subscribers** (HIST-06) — keep the 10-reading cap for now.
- **Admin product CRUD** (ADMIN-06) + **payment analytics events** (ANALYTICS-01) → Phase 8.
- **Self-serve refund button** — MVP refund is endpoint/admin-triggered; user-facing refund later.

### Reviewed Todos (not folded)
None — no pending todos matched Phase 7.
</deferred>

---

*Phase: 7-telegram-stars-payments (provider pivoted to ЮKassa)*
*Context gathered: 2026-06-24*
