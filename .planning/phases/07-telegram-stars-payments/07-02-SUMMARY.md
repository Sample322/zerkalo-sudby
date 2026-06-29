---
phase: 07-telegram-stars-payments
plan: 02
subsystem: payments
tags: [yookassa, payments, alembic, migration, pydantic, config, seed, rub, idempotency]

# Dependency graph
requires:
  - phase: 07-telegram-stars-payments
    provides: "Plan 01 Wave-0 RED substrate — FakeYooKassa + the 14 named xfail tests + the YOOKASSA_SHOP_ID/SECRET_KEY test-env defaults that let this plan's fail-fast config import under test"
  - phase: 01-foundation
    provides: "billing.py models (Product/Payment/Subscription/UserLimits), payments.payload UNIQUE + raw_update JSONB, the fail-fast config.Settings() spine, the upsert-by-slug seed loader, LimitsOut/project_limits"
provides:
  - "Migration 0004 (reversible): ЮKassa columns on payments (provider_payment_id UNIQUE, confirmation_url, idempotence_key, payment_method_id) + subscriptions (payment_method_id, provider_payment_id, last_charge_at, period_index) + flipped provider/currency server_defaults (yookassa/RUB) + nullable telegram_payment_charge_id"
  - "yookassa==3.11.* locked in deps behind the approved Task-1 legitimacy gate (official YooMoney SDK)"
  - "YOOKASSA_SHOP_ID/YOOKASSA_SECRET_KEY fail-fast required config + optional YOOKASSA_WEBHOOK_IPS (NoDecode split)"
  - "schemas/payment.py: ProductOut, CreatePaymentIn (product_slug-only, no client amount — T-07-AMOUNT), CreatePaymentOut, RefundIn, WebhookEnvelope"
  - "4 seeded products (pack_1=69 / pack_3=169 / pack_10=449 / sub_moon=299·30д RUB) upserted by slug"
  - "LimitsOut subscription_active + subscription_period_end (shop window fields, default inactive/None)"
affects: [07-03, 07-04, 07-05, 07-08, payments, yookassa, schemas]

# Tech tracking
tech-stack:
  added: ["yookassa==3.11.0 (official YooMoney SDK — sync, wrapped in anyio.to_thread by Plan 03)"]
  patterns:
    - "A1 price-unit decision locked: products.stars_price holds an INTEGER in RUBLES (column name kept, lowest-churn), formatted '{:.2f}' at ЮKassa-call time — NOT kopecks, NOT Stars"
    - "Additive migration 0004 flips only the server_default for NEW rows (D-02) and relaxes one NOT NULL — zero data migration (no real payments exist)"
    - "CreatePaymentIn carries product_slug ONLY (extra=forbid + no amount/price field) — the server-recompute posture (T-07-AMOUNT) is enforced at the schema boundary, asserted by a Wave-0 test"
    - "provider_payment_id UNIQUE index = the exactly-once grant backstop (T-07-REPLAY) the Plan-04 webhook grant relies on"

key-files:
  created:
    - "backend/alembic/versions/0004_yookassa_payment_fields.py — hand-written reversible migration (down_revision 0003)"
    - "backend/app/schemas/payment.py — ProductOut/CreatePaymentIn/CreatePaymentOut/RefundIn/WebhookEnvelope"
    - "backend/app/seed/data/products.json — 4 D-15 RUB product rows (brand-safe, SAFE-06)"
  modified:
    - "backend/app/models/billing.py — Payment + Subscription ЮKassa columns, flipped defaults, nullable charge id, A1 docstring"
    - "backend/app/core/config.py — YOOKASSA_SHOP_ID/SECRET_KEY (fail-fast) + YOOKASSA_WEBHOOK_IPS; WEBHOOK_SECRET note"
    - "backend/app/seed/loader.py — Product import + upsert-by-slug + products count"
    - "backend/app/schemas/auth.py — LimitsOut subscription_active + subscription_period_end"
    - "backend/app/services/telegram_auth.py — project_limits sets the two new fields (synthetic branch); sync signature unchanged"
    - "backend/pyproject.toml — yookassa==3.11.* dependency (lock-once comment)"
    - ".env.example — YOOKASSA_SHOP_ID/SECRET_KEY + YOOKASSA_WEBHOOK_IPS; WEBHOOK_SECRET no longer used by ЮKassa"
    - "DEPLOY.md — ЮKassa section (two secrets + dashboard webhook URL registration)"

key-decisions:
  - "A1 locked: products.stars_price = integer RUBLES (column name retained — additive, lowest-churn); ProductOut exposes it as price_rub via validation_alias; the '{:.2f}' formatter lives in the Plan-03 service"
  - "ADD provider_payment_id (UNIQUE/indexed/nullable) rather than rename telegram_payment_charge_id — keeps the existing indexed column untouched; the legacy charge-id column is retained (unused under ЮKassa) and made nullable on subscriptions so a ЮKassa sub insert is legal (D-08)"
  - "LimitsOut subscription_active/subscription_period_end default inactive/None NOW (shape-complete GET /api/me); project_limits sync signature deliberately unchanged — Plan 05 owns the async/session-aware migration that fills them from the live Subscription window"
  - "uv sync installs only the default group; ran `uv sync --extra dev` to restore pytest/ruff (operational invocation, not a code change)"

patterns-established:
  - "Reversible hand-written migration mirroring 0003 style: op.add_column for additive cols, op.alter_column(server_default=...) for the D-02 default flip, op.create_index(unique=True) for the grant backstop, full inverse in downgrade()"
  - "ЮKassa fail-fast secrets join the existing no-default Settings spine (like JWT_SECRET); the optional IP allowlist reuses the CORS_ORIGINS NoDecode+split footgun guard"

requirements-completed: [PAY-01, PAY-02, PAY-06]

# Metrics
duration: 9min
completed: 2026-06-29
---

# Phase 7 Plan 02: ЮKassa Data + Config Foundation Summary

**The additive ЮKassa foundation the whole phase stands on — reversible migration 0004 (provider-agnostic payment id UNIQUE, saved-method id, confirmation url, idempotence key, RUB/yookassa server-defaults, nullable subscription charge id), fail-fast YOOKASSA_* secrets, 4 RUB seed products, the product_slug-only payment schemas (no client amount), and the LimitsOut shop-window fields — with yookassa==3.11.* locked behind the approved legitimacy gate.**

## Performance

- **Duration:** ~9 min (active execution; Task-1 legitimacy gate approved out-of-band before this run)
- **Started:** 2026-06-29T10:13Z
- **Completed:** 2026-06-29T10:23Z
- **Tasks:** 2 executed (Task 2 + Task 3; Task 1 was the pre-approved package-legitimacy checkpoint)
- **Files modified:** 12 (3 created + 9 modified)

## Accomplishments
- **Migration 0004 + model fields (reversible):** `payments` gains `provider_payment_id` (UNIQUE/indexed/nullable — the T-07-REPLAY exactly-once backstop), `confirmation_url`, `idempotence_key`, `payment_method_id`; `provider`→`yookassa` / `currency`→`RUB` server-defaults for new rows (D-02). `subscriptions` gains `payment_method_id`, `provider_payment_id`, `last_charge_at`, `period_index`, and a **nullable** `telegram_payment_charge_id` (a ЮKassa sub has no Telegram charge id — D-08). `down_revision="0003_reading_answer_style"`, fully reversed in `downgrade()`.
- **Fail-fast config + dep lock:** `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` are required (no default → `Settings()` raises at import without them, verified); optional `YOOKASSA_WEBHOOK_IPS` (NoDecode split). `yookassa==3.11.*` added to `pyproject.toml` + `uv sync` (official YooMoney SDK, approved Task 1; unofficial async forks rejected).
- **Seed products + payment schemas + shop fields:** 4 D-15 RUB rows (`pack_1`=69 / `pack_3`=169 / `pack_10`=449 / `sub_moon`=299·30д), brand-safe (SAFE-06), upserted by slug. `schemas/payment.py` exports `ProductOut` (`price_rub`←`stars_price` alias), `CreatePaymentIn` (`product_slug` ONLY, `extra=forbid`, **no** `amount`/`price` — T-07-AMOUNT), `CreatePaymentOut`, `RefundIn`, `WebhookEnvelope`. `LimitsOut` gains `subscription_active` + `subscription_period_end`.
- **Suite green throughout + Plan-01 baseline preserved:** **84 passed / 91 skipped / 3 xpassed**, exit 0, after each task; `ruff check` clean on every changed file. Both `<verify>` blocks print `models ok` / `migration ok` / `seed ok` / `schemas ok`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Package-legitimacy checkpoint (yookassa SDK)** — pre-approved out-of-band ("approved: yookassa==3.11.*"); no commit (a gate, not code).
2. **Task 2: billing.py fields + migration 0004 + yookassa dep + fail-fast config** - `d066b8f` (feat)
3. **Task 3: Seed products + payment schemas + LimitsOut/GET /api/me extension + docs** - `fefa38a` (feat)

**Plan metadata:** _(this commit)_ (docs: complete plan)

## Files Created/Modified
- `backend/alembic/versions/0004_yookassa_payment_fields.py` - Reversible additive migration: ЮKassa columns, UNIQUE index on `provider_payment_id`, the two server_default flips, nullable `subscriptions.telegram_payment_charge_id`.
- `backend/app/models/billing.py` - `Payment` + `Subscription` ЮKassa columns; flipped `provider`/`currency` defaults; nullable charge id; module + `Product` docstrings note the provider pivot + A1 (integer RUBLES).
- `backend/app/core/config.py` - `YOOKASSA_SHOP_ID`/`YOOKASSA_SECRET_KEY` required (fail-fast) + optional `YOOKASSA_WEBHOOK_IPS` with a NoDecode splitter; `WEBHOOK_SECRET` comment updated (unused by ЮKassa).
- `backend/app/seed/data/products.json` - 4 D-15 RUB product rows (brand-safe titles/descriptions).
- `backend/app/seed/loader.py` - `Product` import + `upsert_by_slug(session, Product, products)` + `products` in the return-count dict.
- `backend/app/schemas/payment.py` - `ProductOut`, `CreatePaymentIn` (no client amount), `CreatePaymentOut`, `RefundIn`, `WebhookEnvelope`.
- `backend/app/schemas/auth.py` - `LimitsOut.subscription_active` + `subscription_period_end` (default inactive/None).
- `backend/app/services/telegram_auth.py` - `project_limits` sets the two new fields on the synthetic-unlimited branch; sync signature unchanged (Plan-05 seam documented).
- `backend/pyproject.toml` - `yookassa==3.11.*` (lock-once comment mirroring anthropic/aiogram).
- `.env.example` - ЮKassa secrets + commented `YOOKASSA_WEBHOOK_IPS`; `WEBHOOK_SECRET` note.
- `DEPLOY.md` - ЮKassa section: the two secrets + the dashboard webhook URL `https://<backend>/api/payments/yookassa/webhook`.

## Decisions Made
- **A1 price unit = integer RUBLES, column name kept** (`stars_price`). Lowest-churn additive choice (RESEARCH Open Q2 / Schema Delta Option A); `ProductOut` speaks `price_rub` via `validation_alias`; the `"{:.2f}"` ЮKassa formatter is the Plan-03 service's job.
- **ADD `provider_payment_id` rather than rename** the indexed `telegram_payment_charge_id` (D-06 recommendation): the existing indexed column stays untouched; the legacy column is retained (unused under ЮKassa) and made nullable on `subscriptions` so a ЮKassa sub insert is legal (D-08).
- **`LimitsOut` window fields default inactive/None now; `project_limits` sync signature unchanged.** Shape-completes `GET /api/me` so the shop FE can render «активна до DD.MM», while leaving the async/session-aware migration that fills them from the live `Subscription` window as Plan 05's explicit scope (per the plan's own NOTE).

## Deviations from Plan

None - plan executed exactly as written. (Operational note, not a code deviation: a plain `uv sync` installs only the default dependency group and dropped the dev extras (pytest/ruff); re-ran `uv sync --extra dev` to restore them. No file or scope change.)

---

**Total deviations:** 0
**Impact on plan:** None — both tasks landed exactly as specified; every `<verify>` and `<acceptance_criteria>` item passed, and the Plan-01 baseline (84 pass / 91 skip / 3 xpass) is preserved.

## Issues Encountered
- The Task-2/Task-3 `<verify>` one-liners import `app.core.config`, which fail-fasts on the full required secret set (not just the ЮKassa pair). Ran them with the complete env mirroring `tests/conftest.py` `_TEST_ENV_DEFAULTS` (the suite itself sets these via `os.environ.setdefault` before importing app modules). This is the intended fail-fast behaviour, not a defect — confirmed `Settings()` raises with exactly `{YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY}` missing when only those two are absent.
- Postgres/Redis are not running in the execution environment, so the 14 ЮKassa Wave-0 tests (and other DB-touching tests) clean-skip rather than running. This plan is additive schema/config/contracts — its model/migration/schema/seed correctness is verified by direct import/exec/instantiation (the `<verify>` blocks) and ruff; the live `alembic upgrade head` apply + the xfail→xpass flips land in Plans 03/04/05 + the HUMAN-UAT deploy smoke.

## User Setup Required
**External service configuration is required for LIVE payments** (the app builds + tests fully in test mode without it). Owner-provisioned at deploy time (documented in `DEPLOY.md` → "ЮKassa (YooKassa) payments — Phase 7"):
- `YOOKASSA_SHOP_ID` / `YOOKASSA_SECRET_KEY` in the backend app env (boot fails fast if absent).
- Register the webhook URL `https://<backend>/api/payments/yookassa/webhook` (events `payment.succeeded` / `payment.canceled` / `refund.succeeded`) in the ЮKassa dashboard.

## Known Stubs
- **`LimitsOut.subscription_active` / `subscription_period_end` default to `False`/`None` (intentional forward-seam, NOT a blocking stub).** This plan's goal is the data + config + schema foundation; the live values come from the `Subscription` window once Plan 05 makes `project_limits` async + session-aware (explicitly that plan's scope, per the PLAN.md NOTE). Documented in the schema docstring + `project_limits` docstring. `GET /api/me` is shape-complete today so the shop FE renders against a stable contract; no UI claims an active subscription that isn't there (the default is honestly "inactive").

## Next Phase Readiness
- **Plan 03 (PaymentService) unblocked:** the ЮKassa columns, the fail-fast secrets, and `yookassa==3.11.*` are all present; the service can `Configuration.configure(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)` and wrap the sync SDK in `anyio.to_thread`. The `"{:.2f}"` RUB formatter (A1) is the service's to add.
- **Plan 04 (routes) unblocked:** `schemas/payment.py` contracts exist; `GET /api/products` projects `ProductOut` from the seeded rows; the create route consumes `CreatePaymentIn` (no client amount); the webhook consumes `WebhookEnvelope` + the UNIQUE `provider_payment_id` backstop.
- **Plan 05 (gate + window fill):** must make `project_limits` async/session-aware and fill `subscription_active`/`subscription_period_end` from the live `Subscription` window (updating BOTH the `/api/me` and `/api/auth/telegram` call sites); the fields + defaults are already in place.
- **Deferred debt (carried, not introduced here):** `/gsd-code-review` + `/gsd-secure-phase` for Phases 4, 5, 6 (and now 7's money path) remain before milestone close.

## Self-Check: PASSED

All claimed created files exist on disk and both task commits are in git history:
- `backend/alembic/versions/0004_yookassa_payment_fields.py` — FOUND
- `backend/app/schemas/payment.py` — FOUND
- `backend/app/seed/data/products.json` — FOUND
- `.planning/phases/07-telegram-stars-payments/07-02-SUMMARY.md` — FOUND
- commit `d066b8f` (Task 2) — FOUND
- commit `fefa38a` (Task 3) — FOUND

---
*Phase: 07-telegram-stars-payments*
*Completed: 2026-06-29*
