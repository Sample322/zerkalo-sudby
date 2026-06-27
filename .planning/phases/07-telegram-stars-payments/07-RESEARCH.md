# Phase 7: ЮKassa (YooKassa) Payments - Research

**Researched:** 2026-06-27
**Domain:** Payment integration (ЮKassa v3 REST API, RUB) for a FastAPI backend + React Telegram Mini App; idempotent grant-after-confirmed-payment, recurring saved-card subscription, refunds, soft-paywall shop UI.
**Confidence:** HIGH (API shapes verified against live yookassa.ru/developers docs + package registries; one MEDIUM area — the recurring-charge scheduler choice — is a discretion call with documented tradeoffs)

<user_constraints>
## User Constraints (from CONTEXT.md)

> ⚠️ **PROVIDER PIVOT (locked):** Roadmap/ТЗ/CLAUDE.md name this phase "Telegram Stars" and lock Stars-only. The owner **decided against Stars** and chose **ЮKassa direct API** (RUB). Implement ЮKassa; IGNORE the Stars flow in CLAUDE.md §Payments / ROADMAP AC for this phase. PAY-01..08 *intent* still holds — only the provider/transport changes.

### Locked Decisions

**Provider & transport**
- **D-01:** Provider = **ЮKassa direct API** (`yookassa` Python SDK or `httpx` to `https://api.yookassa.ru/v3`). NOT Telegram Stars / Telegram Payments / `provider_token`.
- **D-02:** Currency = **RUB** everywhere. `payments.currency` default `XTR`→`RUB`; `payments.provider` `telegram_stars`→`yookassa`.
- **D-03:** Owner **accepts the moderation risk** (external acquirer for a digital service inside a Telegram Mini App may draw Telegram-ToS scrutiny / catalog rejection). Owner's decision; surfaced explicitly.

**Payment flow (one-time packs)**
- **D-04:** Backend creates a ЮKassa payment (amount RUB, `capture=true`, `confirmation:{type:"redirect", return_url}`), returns `confirmation_url`; frontend opens it via Telegram `openLink` (or widget). A per-attempt **Idempotence-Key** is sent to ЮKassa.
- **D-05:** **Webhook** (`POST /api/payments/yookassa/webhook`) receives `payment.succeeded`/`payment.canceled`/`refund.succeeded`. **Never trust the webhook body** — re-`GET /v3/payments/{id}` and grant strictly on API-confirmed `succeeded` (ЮKassa does not sign webhooks → IP allowlist + re-fetch).
- **D-06:** **Idempotent grant** — `payments.payload` UNIQUE + ЮKassa payment id stored UNIQUE (reuse/rename `telegram_payment_charge_id`→provider-agnostic `provider_payment_id`, or add column via migration). Same event twice ⇒ access granted exactly once; access NEVER granted on creation, only on confirmed `succeeded`.
- **D-07:** Frontend, after returning from ЮKassa, **polls `GET /api/me`** until balance/sub updates (webhook is source of truth; return_url is UX only).

**Subscription «Лунный доступ» (recurring)**
- **D-08:** Recurring via ЮKassa **saved payment method**: first payment `save_payment_method=true` → store `payment_method_id` on the subscription; renewals are **merchant-initiated** auto-charges (ЮKassa does NOT auto-charge — we must trigger). A **scheduled charge mechanism is required** (RESEARCH: APScheduler vs timeweb cron vs lazy charge-on-access; Celery/RQ/Arq banned). DB = source of truth for the entitlement window (`subscriptions.current_period_end`).
- **D-09:** Subscription grants **unlimited readings for the 30-day window** (subscription bucket). Extended history (HIST-06) deferred.
- **D-10:** **Cancel** = stop future auto-charge (`status=canceled`, `canceled_at`), **keep access until `current_period_end`**. Self-serve cancel button in profile.

**Consumption order & gate (carried from Phase 6)**
- **D-11:** Reading-consume order stays **free → subscription → paid packs**. Paid/subscription buckets plug into the SAME atomic consume gate (safety-before-gate, refund slot on honest-fail) — extend, do not fork it.

**Shop / UI**
- **D-12:** Tariffs/buy shown in **BOTH** the soft-paywall sheet **AND** a permanent «Баланс / Магазин» section in Profile.
- **D-13:** Success/failure copy brand-safe (SAFE-06) and honest: «деньги не списаны / оплата не прошла — доступ не выдан» on failure; balance/sub visible.

**Refunds**
- **D-14:** **Auto refund endpoint** via ЮKassa refund API (`POST /v3/refunds`); flips `payments.status=refunded`, sets `refunded_at`, adjusts access. **Admin-triggered for MVP**; webhook also handles `refund.succeeded` idempotently.

**Pricing (seed defaults — admin-tunable later)**
- **D-15:** Recommended seed (RUB): `1 расклад = 69`, `3 = 169`, `10 = 449`, `подписка 30д = 299/мес`. Stored as `products` rows. Treat as defaults, not law.

### Claude's Discretion
- Exact ЮKassa client (official `yookassa` SDK vs thin `httpx` wrapper) — researcher/planner choose. **→ See Standard Stack: recommendation = official SDK in a threadpool.**
- Scheduler approach for recurring auto-charge (D-08) — **→ See Architecture Pattern 4: recommendation = lazy charge-on-access + a lightweight in-process APScheduler sweep.**
- Schema delta (rename vs add `provider_payment_id`/`payment_method_id`) — **→ See Schema Delta: recommendation = ADD columns (additive migration 0004).**
- Webhook source-verification details (ЮKassa IP ranges + re-fetch) — **→ confirmed current; see Security Domain + Pattern 5.**

### Deferred Ideas (OUT OF SCOPE)
- **Telegram Stars** as an alternative/parallel rail — dropped (owner chose ЮKassa).
- **aiogram bot module** — NOT needed for Phase 7 (ЮKassa is direct HTTP). The webhook is a plain FastAPI route. Defer the bot to a later phase if ever.
- **Extended history for subscribers** (HIST-06) — keep the 10-reading cap.
- **Admin product CRUD** (ADMIN-06) + **payment analytics events** (ANALYTICS-01) → Phase 8.
- **Self-serve refund button** — MVP refund is endpoint/admin-triggered; user-facing refund later.
- Receipts / 54-ФЗ fiscalization (`receipt` object) — NOT in scope here (no decision; flag as Open Question if the merchant is an ИП/ООО subject to 54-ФЗ).
</user_constraints>

<phase_requirements>
## Phase Requirements

PAY-01..08 reinterpreted for the ЮKassa pivot (Stars/XTR/provider_token → ЮKassa direct API / RUB / saved payment method). Intent unchanged.

| ID | Description (reinterpreted) | Research Support |
|----|----------------------------|------------------|
| **PAY-01** | `GET /api/products` — packs 1/3/10 + subscription | Seed `products` rows (loader upsert-by-slug pattern); `Product` model exists. RUB prices in `stars_price`→`price` column. Standard Stack + Schema Delta. |
| **PAY-02** | Create a ЮKassa payment with a `payload` (user_id, product_id, purchase_type, idempotency_key) | `POST /api/payments/create` → `Payment.create` (SDK) with `amount/capture/confirmation:{redirect,return_url}` + per-attempt `Idempotence-Key`; store `payments.payload` UNIQUE; return `confirmation_url`. Pattern 2 + Code Examples. |
| **PAY-03** | Validate product is active + payload unused (server-side recompute price) | Recompute `amount` from `Product` row, never from client (threat T-07-AMOUNT). No `pre_checkout_query` exists for ЮKassa — validation is at create-time. Security Domain. |
| **PAY-04** | On confirmed payment — store payment + provider id, grant `paid_spreads_balance` or subscription, update entitlements | Webhook `payment.succeeded` → **re-GET** payment → grant inside one transaction. Pattern 3 + 5. |
| **PAY-05** | Idempotency: `payload`/provider id UNIQUE; grant only after confirmed payment; redelivery never double-grants | UNIQUE constraints + status-transition guard (`CREATED→PAID` once). Pattern 5 + Pitfall 2. |
| **PAY-06** | Subscription «Лунный доступ» — recurring via saved card + 30-day entitlement window; renewal; cancel | `save_payment_method=true` → `payment_method_id`; merchant-initiated renewal charge; DB window source-of-truth; cancel stops next charge. Pattern 4 + D-10. |
| **PAY-07** | Refunds (`POST /v3/refunds`) — payment→refunded, adjust access | `Refund.create(payment_id, amount)`; webhook `refund.succeeded` idempotent; flip status + adjust. Pattern 6 + D-14. |
| **PAY-08** | UI for tariffs + success; clear error copy («деньги не списаны / доступ не выдан») | PaywallSheet buy buttons + Profile «Магазин»; `openLink(confirmation_url)`; poll `GET /api/me`; brand-safe copy. Frontend section + D-13. |
</phase_requirements>

## Summary

ЮKassa exposes a clean, well-documented **v3 REST API at `https://api.yookassa.ru/v3/`** using **HTTP Basic auth** (`shopId` as username, secret key as password) and a mandatory **`Idempotence-Key` header on every POST**. The one-time-pack flow is: backend `POST /v3/payments` with `amount{value,currency:"RUB"}`, `capture:true`, and `confirmation:{type:"redirect", return_url}`; ЮKassa returns a `confirmation.confirmation_url`; the Mini App opens it; the user pays in their bank's flow and is redirected back to `return_url`. The **payment lifecycle is `pending → (waiting_for_capture) → succeeded | canceled`**; with `capture:true` the `waiting_for_capture` step is skipped. The merchant learns the final state via a **webhook AND/OR by polling `GET /v3/payments/{id}`**. Recurring works via a **saved payment method**: the first payment carries `save_payment_method:true`, the success response returns `payment_method.id`, and each renewal is a **merchant-initiated** `POST /v3/payments` with `payment_method_id` and **no confirmation block** — ЮKassa explicitly does **not** auto-charge on a schedule; the merchant must trigger each charge. Refunds are `POST /v3/refunds` with `payment_id` + `amount` (partial allowed, min 1₽; the practical window for cards is generous — 3 years per ЮKassa, ~15 months acquirer-practical).

The single most important security fact: **ЮKassa webhooks are NOT cryptographically signed.** The mandated defense (confirmed in current ЮKassa docs) is to **re-fetch the object by id from the API** and trust only the API-confirmed status, plus **restrict the webhook endpoint to ЮKassa's published IP ranges**. This maps cleanly onto the project's existing "server-authoritative everything" posture and the already-present DB idempotency columns (`payments.payload` UNIQUE, a charge-id index, `raw_update` JSONB audit). Access must be granted **only on the re-fetched `succeeded` status**, never on payment creation, and exactly once on redelivery.

For Python integration, the **official `yookassa` SDK (3.11.0, published 2026-06-26, slopcheck [OK])** is synchronous (built on `requests`). In this async FastAPI app the correct pattern is to **run the sync SDK calls in a threadpool via `anyio.to_thread.run_sync`** (anyio is already a transitive FastAPI/Starlette dependency) — this is simpler and safer than a thin hand-rolled `httpx` client and avoids depending on unofficial async forks. For the recurring-charge scheduler under the Celery/RQ/Arq ban and a single timeweb container, the recommendation is **lazy "charge-on-access at expiry" as the correctness backbone** (the DB window is already the source of truth and the consume-gate already runs on every reading) **augmented by a lightweight in-process APScheduler `AsyncIOScheduler` daily sweep** for proactive renewal/dunning — with explicit caveats about multi-instance deploys.

**Primary recommendation:** Add a `services/payments.py` (ЮKassa client wrapped via `anyio.to_thread`, grant/idempotency/recurring/refund logic) + a thin `api/payments.py` router (products, create, webhook, refund, cancel). Extend `services/reading.py`'s existing `Bucket` seam (already stubbed for `SUBSCRIPTION`/`PAID`) — do **not** fork the atomic gate. Add additive migration 0004 (`provider_payment_id`, `payment_method_id`, `confirmation_url`, `idempotence_key`, RUB defaults). Grant **only** on the re-fetched webhook `succeeded`, IP-allowlist the webhook, recompute price server-side, and store the official SDK as a main dependency.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Products/tariffs catalog (PAY-01) | API / Backend | DB (seed `products`) | Server owns the price list; client only renders it. Price is recomputed server-side at create (T-07-AMOUNT). |
| Create payment + idempotence key (PAY-02/03) | API / Backend | ЮKassa (external) | Only the backend holds the secret key; the Idempotence-Key is generated server-side per attempt. |
| Hosting the bank payment form | ЮKassa (external) | Browser (redirect target) | PCI scope stays with ЮKassa; the app never touches card data. |
| Opening the payment URL + return | Browser / Client (Telegram WebView) | — | `openLink(confirmation_url)` opens the external browser; the Mini App stays open and regains focus via the `activated` event. |
| Confirm + grant entitlement (PAY-04/05) | API / Backend (webhook) | DB (source of truth) | Grant happens only after a server-side re-GET confirms `succeeded`; DB UNIQUE constraints enforce exactly-once. |
| Recurring renewal charge (PAY-06) | API / Backend (scheduler/lazy) | ЮKassa (external) | ЮKassa does not auto-charge; the merchant triggers each charge. DB window is authoritative. |
| Refunds (PAY-07) | API / Backend (admin) | ЮKassa + webhook | Admin-triggered `POST /v3/refunds`; webhook `refund.succeeded` reconciles idempotently. |
| Entitlement enforcement (consume) | API / Backend (`reading.py` gate) | DB (`user_limits`) | The existing atomic consume-gate already has the `SUBSCRIPTION`/`PAID` seam; Phase 7 fills it. |
| Shop UI / balance display (PAY-08) | Frontend (React) | API (`GET /api/me`, `GET /api/products`) | Renders prices, opens payment, polls for granted access. No client-side trust. |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **yookassa** (official SDK) | `3.11.0` | ЮKassa v3 API client (`Configuration`, `Payment.create`, `Payment.find_one`, `Refund.create`, `Webhook`) | `[VERIFIED: PyPI]` Official YooMoney SDK, published 2026-06-26, supports Py 3.12, slopcheck [OK]. Handles auth, Idempotence-Key, retries, object parsing. Repo: github.com/yoomoney/yookassa-sdk-python. |
| **anyio** | `4.x` (already transitive) | `anyio.to_thread.run_sync(...)` to run the **synchronous** SDK off the event loop | `[VERIFIED: PyPI]` Already a FastAPI/Starlette dependency — no new top-level dep. The idiomatic way to call a sync client from async FastAPI without blocking. |

> **Why the official SDK over a thin httpx wrapper (Claude's Discretion D-01):** The SDK is sync (built on `requests`), but wrapping its 4 calls in `anyio.to_thread.run_sync` is ~5 lines and gives you maintained Idempotence-Key handling, error mapping, IP-range constants, and object models for free. A hand-rolled `httpx` client means re-implementing auth, idempotency, the notification-object parse, and the IP allowlist yourself (more surface for bugs in a payments path). Unofficial async forks (`async_yookassa`, `aioyookassa`) exist but are **community-maintained, low-download** — `[ASSUMED]`/`[SUS]` risk in a money path; do NOT use them. **Recommendation: official `yookassa` SDK + `anyio.to_thread`.**

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **tenacity** | `>=9,<10` (already a dep) | Bounded retry + timeout around a **recurring** charge (transient ЮKassa 5xx) | Already used for the LLM call. Reuse for merchant-initiated renewals; do NOT retry create-payment blindly (idempotency key handles that). |
| **APScheduler** | `3.11.2` | In-process `AsyncIOScheduler` daily sweep for proactive renewal + expiry (D-08) | `[VERIFIED: PyPI]` slopcheck [OK]. Lightweight, no broker (respects the Celery/RQ/Arq ban). See Pattern 4 + caveats. |
| **httpx** | `>=0.28` (currently **dev-only**) | Only if you reject the SDK and hand-roll; or for test-time ЮKassa stubbing via ASGITransport | `[VERIFIED: PyPI]` 0.28.1. If the SDK route is taken, httpx stays dev-only (it already is). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Official `yookassa` SDK in threadpool | Thin `httpx.AsyncClient` wrapper | Native async, one fewer abstraction — but you re-implement auth/idempotency/IP-list/parse in a payments path. Only worth it if you want zero sync calls. |
| Official SDK | `async_yookassa` / `aioyookassa` (unofficial async) | Native async — but community-maintained, low downloads, money path. **Avoid.** `[SUS]` |
| Lazy charge-on-access + APScheduler sweep | timeweb cron / scheduled job hitting an internal `POST /api/internal/charge-due` (token-guarded) | Cron survives restarts/multi-instance cleanly and is broker-free; but adds an external moving part + an internal auth surface. Viable fallback if you ever run >1 backend instance. See Pattern 4. |
| Lazy + APScheduler | Pure lazy charge-on-access only | Simplest, zero scheduler — but renewals only happen when the user opens the app at/after expiry, so a lapsed subscriber isn't proactively re-charged (acceptable for MVP; the window is DB-authoritative anyway). |

**Installation:**
```bash
# Backend (add to pyproject.toml [project.dependencies]):
#   "yookassa==3.11.*",
#   "APScheduler>=3.11,<4",   # only if adopting the proactive sweep (Pattern 4)
# anyio + tenacity + httpx already present (tenacity main; httpx dev). Then:
uv sync   # or: uv pip install -e ".[dev]"
```

**Version verification (run before locking):**
```bash
pip index versions yookassa        # → 3.11.0 (latest, 2026-06-26) ✓ verified this session
pip index versions APScheduler     # → 3.11.2 ✓ verified
pip index versions anyio           # → 4.14.1 (transitive via FastAPI) ✓ verified
pip index versions httpx           # → 0.28.1 ✓ verified
```

## Package Legitimacy Audit

> Run via `slopcheck install <pkg>` (slopcheck 0.6.1) + `pip index versions` on PyPI (correct ecosystem). All packages verified this session.

| Package | Registry | Age / Latest | Source Repo | slopcheck | Disposition |
|---------|----------|--------------|-------------|-----------|-------------|
| `yookassa` | PyPI | 3.11.0 (2026-06-26); line since 2.0.0 (2019) | github.com/yoomoney/yookassa-sdk-python | **[OK]** | **Approved** (official YooMoney SDK) |
| `APScheduler` | PyPI | 3.11.2 (mature, 3.x since 2015) | github.com/agronholm/apscheduler | **[OK]** | **Approved** (only if Pattern 4 sweep adopted) |
| `anyio` | PyPI | 4.14.1 | github.com/agronholm/anyio | (transitive — FastAPI dep) | **Approved** (already present) |
| `tenacity` | PyPI | 9.x (already locked) | github.com/jd/tenacity | (already approved Phase 4) | **Approved** (reuse) |
| `httpx` | PyPI | 0.28.1 (already dev-dep) | github.com/encode/httpx | (already approved) | **Approved** (dev-only stays, unless hand-rolling) |
| `async_yookassa` / `aioyookassa` | PyPI | unofficial, low downloads | community | **[SUS]** (not run; flagged on policy) | **REJECTED** — do not use unofficial async clients in a money path |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `async_yookassa`, `aioyookassa` — explicitly rejected (policy: no unofficial low-download libs in the payments path). The official sync SDK in a threadpool covers the async need.

*All approved packages are `[VERIFIED: PyPI]` (registry-confirmed via correct ecosystem + slopcheck [OK]). Package names came from the official ЮKassa docs / PyPI, not from a guess. The planner should still gate the **first install** of `yookassa` (and `APScheduler` if used) behind a `checkpoint:human-verify`, matching the established Phase-1/4 lock-once pattern in pyproject.toml.*

## Architecture Patterns

### System Architecture Diagram

```
ONE-TIME PACK PURCHASE (PAY-01..05, PAY-08)
────────────────────────────────────────────────────────────────────────
[Mini App] --GET /api/products--> [FastAPI] --select--> [Postgres products]
    │  renders tariffs in PaywallSheet + Profile «Магазин»
    │
    │  tap «Купить 3 расклада»
    ▼
[Mini App] --POST /api/payments/create {product_slug}--> [FastAPI api/payments]
                                                              │ recompute price from products row (T-07-AMOUNT)
                                                              │ INSERT payments(status=CREATED, payload UNIQUE)
                                                              │ Idempotence-Key = uuid4 (per attempt)
                                                              ▼
                                              anyio.to_thread → yookassa.Payment.create(
                                                  amount{value,RUB}, capture=true,
                                                  confirmation{type:redirect, return_url},
                                                  metadata{payment_uuid})
                                                              │
                                          ЮKassa returns {id, status:pending,
                                                          confirmation.confirmation_url}
                                                              │ store provider_payment_id + confirmation_url
    ┌─────────────────────────────────────────────────────────┘
    ▼ {confirmation_url}
[Mini App] Telegram.WebApp.openLink(confirmation_url)  ──► [External browser: bank 3DS / SBP]
    │  Mini App stays open (NOT closed)                              │ user pays
    │                                                                ▼
    │                                              ЮKassa ──redirect──► return_url
    │
    │  on `activated` event (focus regained) → start polling
    ▼
[Mini App] --GET /api/me (poll ~2s, ~Nx)--> [FastAPI]   (reads granted balance/sub)
                                                  ▲
                                                  │ (granted out-of-band by the webhook below)
ASYNC, AUTHORITATIVE GRANT (the source of truth)
────────────────────────────────────────────────────────────────────────
[ЮKassa] --POST notification {event:payment.succeeded, object}--> [POST /api/payments/yookassa/webhook]
                                                                       │ 1. IP in ЮKassa allowlist? else 403/ignore
                                                                       │ 2. parse object.id (IGNORE body status — unsigned!)
                                                                       │ 3. anyio.to_thread → Payment.find_one(id)  ← RE-FETCH
                                                                       │ 4. trust ONLY re-fetched status==succeeded
                                                                       │ 5. tx: if payments.status==CREATED → PAID,
                                                                       │       grant paid_spreads_balance / subscription,
                                                                       │       set paid_at, raw_update=object  (exactly once)
                                                                       │ 6. return 200 (always 200 on a handled/dup event)
                                                                       ▼
                                                                  [Postgres user_limits / subscriptions]

RECURRING RENEWAL (PAY-06) — merchant-initiated (ЮKassa does NOT auto-charge)
────────────────────────────────────────────────────────────────────────
First sub payment: ...create(save_payment_method=true) → success webhook stores
    subscriptions.payment_method_id + current_period_end = now+30d
            │
   (lazy)  every reading → consume-gate: if sub window expired → no SUBSCRIPTION bucket
   (sweep) APScheduler daily → find subs with current_period_end <= now+grace, status=active
            ▼
   anyio.to_thread → Payment.create(amount, capture=true, payment_method_id=...,  ← NO confirmation
                                    Idempotence-Key=f"renew:{sub_id}:{period_n}")
            │ success webhook → extend current_period_end += 30d
            │ failure → status=payment_failed, keep access til period_end, optional retry (tenacity)

REFUND (PAY-07) — admin-triggered
────────────────────────────────────────────────────────────────────────
[admin] --POST /api/payments/{id}/refund--> [FastAPI require_admin]
            │ anyio.to_thread → Refund.create(payment_id, amount{value,RUB},
            │                                  Idempotence-Key=f"refund:{payment_id}")
            ▼ webhook refund.succeeded → re-GET refund → payments.status=refunded,
              refunded_at, adjust access (decrement balance / end subscription)  (idempotent)
```

File-to-implementation mapping is in **Component Responsibilities** below, not the diagram.

### Component Responsibilities
| Component | File | Responsibility |
|-----------|------|----------------|
| Products list | `backend/app/api/payments.py` (new) | `GET /api/products` (active products) |
| Create payment | `backend/app/api/payments.py` | `POST /api/payments/create` — recompute price, create CREATED row, call SDK, return `confirmation_url` |
| Webhook | `backend/app/api/payments.py` | `POST /api/payments/yookassa/webhook` — IP gate + re-fetch + grant |
| Refund (admin) | `backend/app/api/payments.py` | `POST /api/payments/{id}/refund` (require_admin) |
| Cancel sub | `backend/app/api/payments.py` | `POST /api/subscriptions/{id}/cancel` (self-serve, D-10) |
| ЮKassa client + logic | `backend/app/services/payments.py` (new) | SDK wrapper (`anyio.to_thread`), grant/idempotency, recurring charge, refund, IP allowlist |
| Recurring sweep | `backend/app/services/payments.py` + `app/main.py` lifespan | APScheduler `AsyncIOScheduler` daily job (Pattern 4) |
| Consume buckets | `backend/app/services/reading.py` (extend `Bucket`/`_consume_free_gate`) | Fill `SUBSCRIPTION`/`PAID` arms — do NOT fork |
| Balance surface | `backend/app/schemas/auth.py` (`LimitsOut`) + `api/users.py` | Already exposes paid/sub fields; add subscription window/status |
| Schemas | `backend/app/schemas/payment.py` (new) | `ProductOut`, `CreatePaymentIn/Out`, webhook envelope, `RefundIn` |
| Seed products | `backend/app/seed/data/products.json` + `loader.py` | Upsert-by-slug (existing pattern); RUB prices D-15 |
| Shop UI | `frontend/src/components/PaywallSheet.tsx`, `profile/ProfileScreen.tsx`, new `shop/*` | Buy buttons, balance/sub, `openLink`, poll |
| Config | `backend/app/core/config.py` | `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` (+ optional IP override) fail-fast |

### Pattern 1: SDK configured once at import; every call wrapped in a threadpool
**What:** Configure the SDK module-level (like `redis_client`/`settings`), then call its sync methods via `anyio.to_thread.run_sync` from async handlers.
**When to use:** All four ЮKassa operations (create, find_one, refund, refund.find).
**Example:**
```python
# Source: pypi.org/project/yookassa (Configuration.configure) + FastAPI/anyio threadpool idiom
# backend/app/services/payments.py
from functools import partial
import anyio
from yookassa import Configuration, Payment, Refund
from app.core.config import settings

Configuration.configure(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)

async def create_payment(*, value_rub: str, return_url: str, idempotence_key: str,
                         metadata: dict, save_payment_method: bool = False):
    body = {
        "amount": {"value": value_rub, "currency": "RUB"},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": "Зеркало Судьбы",
        "metadata": metadata,
    }
    if save_payment_method:
        body["save_payment_method"] = True
    # Payment.create(params, idempotency_key) is SYNC → run off the loop.
    return await anyio.to_thread.run_sync(partial(Payment.create, body, idempotence_key))
```

### Pattern 2: One-time create — never grant here
**What:** Create a `CREATED` `payments` row first (UNIQUE `payload`), call ЮKassa, persist `provider_payment_id` + `confirmation_url`, return only the URL. **No balance change.**
**When to use:** `POST /api/payments/create`.
**Why:** Grant-on-create is the classic fraud hole. Access is granted only by the webhook after a re-fetch (Pattern 3/5).

### Pattern 3: Confirm via webhook, but trust only the re-fetched status
**What:** The webhook handler ignores the (unsigned) body status, re-GETs the object, and grants only if the **re-fetched** status is `succeeded`.
**When to use:** `payment.succeeded` and `refund.succeeded` events.
**Example:**
```python
# Source: yookassa.ru/developers/using-api/webhooks ("check the current status of the object")
async def handle_payment_succeeded(session, object_id: str):
    fresh = await anyio.to_thread.run_sync(partial(Payment.find_one, object_id))  # RE-FETCH
    if fresh.status != "succeeded":
        return  # body lied or not final yet — do nothing, ЮKassa will redeliver
    await grant_for_payment(session, provider_payment_id=fresh.id, raw=fresh.json())
```

### Pattern 4: Recurring renewal without a broker (D-08, Claude's Discretion)
**What:** Two complementary mechanisms, both broker-free (Celery/RQ/Arq stay banned):
1. **Lazy correctness backbone** — the DB `subscriptions.current_period_end` is the *only* source of truth for entitlement. The consume-gate already checks it each reading; an expired window simply yields no `SUBSCRIPTION` bucket. **No charge is ever required for correctness** — a lapsed sub just loses access until renewed. This alone satisfies "DB is source of truth, not ЮKassa."
2. **Proactive renewal sweep** — an in-process **APScheduler `AsyncIOScheduler`** job (started in the FastAPI `lifespan`, like Redis/engine) runs daily, finds `status=active` subscriptions with `current_period_end <= now + grace`, and issues a merchant-initiated charge (`Payment.create` with `payment_method_id`, **no `confirmation`**, a deterministic `Idempotence-Key=f"renew:{sub_id}:{period_index}"`). Success → the webhook extends the window; failure → `status=payment_failed` (keep access until `current_period_end`, optionally retry next sweep with `tenacity`).

**When to use:** Single-container timeweb deploy (current topology — DEPLOY.md describes exactly one backend app).
**Tradeoffs / caveats:**
- **Multi-instance footgun:** if the backend ever scales to >1 instance, every instance runs the scheduler → a sub could be charged N times. **Mitigation:** the deterministic per-period `Idempotence-Key` makes a same-period double-charge a no-op at ЮKassa (24h idempotency window) — but the *cleanest* multi-instance answer is to move the sweep to a **timeweb cron / scheduled job** hitting a token-guarded `POST /api/internal/charge-due` (the documented fallback). For MVP single-container, APScheduler is fine.
- **Restart timing:** APScheduler in-process loses its in-memory schedule on restart, but a *daily idempotent sweep* recomputes "who's due" from the DB every run, so a missed tick self-heals next run. Do NOT persist APScheduler jobstores in PG for this (unnecessary).
- **`misfire_grace_time`** should be generous (hours) so a deploy during the tick window still runs.

**Recommendation:** Ship **lazy backbone + APScheduler daily sweep** now; document the timeweb-cron fallback as the scale-out path. Keep the charge logic in `services/payments.py` so swapping the trigger (APScheduler ↔ cron endpoint) touches one call site.

### Pattern 5: Idempotent grant via status-transition guard + UNIQUE
**What:** Grant inside a transaction that flips `payments.status CREATED → PAID` and only grants if the flip actually happened (row was still `CREATED`). The UNIQUE `provider_payment_id` + UNIQUE `payload` are the DB backstop; the conditional UPDATE is the race guard.
**Example:**
```python
# Mirror reading.py's conditional UPDATE...RETURNING idempotency style.
res = await session.execute(
    update(Payment)
    .where(Payment.provider_payment_id == pid, Payment.status == PaymentStatus.CREATED)
    .values(status=PaymentStatus.PAID, paid_at=func.now(), raw_update=raw)
    .returning(Payment.id, Payment.product_id, Payment.user_id)
)
row = res.first()
if row is None:
    return  # already granted (redelivery) OR unknown id — no double grant
# ... grant balance / subscription for row, then commit
```

### Pattern 6: Refund reconciliation (D-14)
**What:** Admin `POST /v3/refunds` → set a `REFUNDED` intent; the `refund.succeeded` webhook (re-fetched) flips `payments.status=refunded`, sets `refunded_at`, and adjusts access (decrement `paid_spreads_balance`, or end the subscription window). Idempotent on redelivery (status guard + a UNIQUE refund id if stored).
**When to use:** `POST /api/payments/{id}/refund` (require_admin) + webhook `refund.succeeded`.

### Anti-Patterns to Avoid
- **Granting on payment creation or on the webhook body status.** Always re-fetch; grant only on the API-confirmed `succeeded`.
- **Trusting the client's price/amount.** Recompute from the `products` row every time (T-07-AMOUNT).
- **Forking the consume-gate.** The `Bucket` enum + `_consume_free_gate` already have `SUBSCRIPTION`/`PAID` seams — fill them with analogous atomic `UPDATE ... RETURNING` statements; reuse `_refund_*` for honest-fail.
- **Calling the sync SDK directly in an async handler** (blocks the event loop). Always `anyio.to_thread.run_sync`.
- **Wiring aiogram for the webhook.** ЮKassa is plain HTTP; the webhook is a normal FastAPI route. aiogram stays unwired (deferred).
- **Returning non-200 to ЮKassa on a duplicate/handled event.** Return 200 so ЮKassa stops redelivering; only return 4xx/5xx when you genuinely could not process (so it retries).
- **Putting the secret key or a parsed amount anywhere client-visible** (T-07-SECRET).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ЮKassa HTTP client (auth, idempotency, retries, object parse) | Custom `httpx` wrapper | Official `yookassa` SDK | Money path — maintained auth/idempotency/IP-list/models; fewer bugs. |
| Async-ifying a sync SDK | Custom thread/executor plumbing | `anyio.to_thread.run_sync` | Already a FastAPI dep; correct, cancellation-aware. |
| Idempotency / exactly-once grant | Ad-hoc "have I seen this?" flags | DB UNIQUE (`payload`, `provider_payment_id`) + conditional `UPDATE...RETURNING` | The codebase already uses this exact pattern (auth upsert, consume-gate). |
| Webhook authenticity | Custom HMAC/signature check | IP allowlist (ЮKassa ranges) + **re-fetch by id** | ЮKassa does NOT sign webhooks; re-fetch is the documented defense. |
| Recurring scheduler | Celery/RQ/Arq (BANNED) | Lazy DB window + APScheduler sweep (or timeweb cron) | No broker needed; DB is source of truth. |
| Retry/backoff on renewal | Hand-rolled sleep loops | `tenacity` (already a dep) | Bounded, tested. |
| Entitlement bucket logic | New gate | Extend `reading.py` `Bucket` seam | Forking the atomic gate breaks the safety-before-gate + refund invariants. |

**Key insight:** Almost everything Phase 7 needs already has a home in this codebase — idempotency via UNIQUE + conditional UPDATE, fail-fast config, the `Bucket` seam, `tenacity`, `anyio`. The genuinely new thing is the **ЮKassa client (use the official SDK)** and the **webhook re-fetch discipline**. Resist re-implementing money-path primitives.

## Runtime State Inventory

> Phase 7 is mostly additive backend + UI, but the provider pivot touches stored defaults and external service config. Inventory below.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| **Stored data** | `payments` rows from any prior testing carry `provider='telegram_stars'`, `currency='XTR'` server-defaults; `products` table likely empty or Stars-priced. No production payment data exists yet (PAY-* all Pending). | Migration 0004 flips the **server_defaults** to `yookassa`/`RUB` for *new* rows (existing test rows, if any, are harmless / can be ignored or truncated in a dev DB). Seed `products` with RUB prices (D-15). **Data migration of old rows: none needed** (no real payments). |
| **Live service config** | ЮKassa **webhook URL** is configured in the **ЮKassa merchant dashboard** (or via the `Webhook` API), NOT in git. The shop_id/secret_key live only in the merchant account + env. | Owner registers the webhook URL (`https://<backend>/api/payments/yookassa/webhook`) in the ЮKassa dashboard pointing at the deployed backend (url A). Document in DEPLOY.md. |
| **OS-registered state** | None — no Task Scheduler / pm2 / launchd entries. The recurring sweep is in-process (APScheduler in the FastAPI lifespan), not OS-registered. *(If the timeweb-cron fallback is chosen instead, THAT becomes timeweb-registered scheduled-job state — flag at that point.)* | None for the APScheduler approach. |
| **Secrets/env vars** | New: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY` (required, fail-fast). Existing `WEBHOOK_SECRET` placeholder in config/.env.example was reserved "for Phase 7 (bot wiring)" — **now unused** for ЮKassa (ЮKassa doesn't use a Telegram-style secret header). Optional `YOOKASSA_WEBHOOK_IPS` override. | Add the two ЮKassa secrets to config (fail-fast), `.env.example`, and DEPLOY.md. Repurpose or leave `WEBHOOK_SECRET` (harmless; note it's not used by ЮKassa). |
| **Build artifacts / installed packages** | `aiogram==3.28.*` is in `pyproject.toml` but **unwired** — Phase 7 was the assumed wire-in point; with the pivot it stays unwired. New deps: `yookassa` (+ optional `APScheduler`). | Add `yookassa` (and `APScheduler` if Pattern 4 sweep) to deps; `uv sync`/reinstall. Do NOT remove aiogram (lock-once policy; it's a no-op import). |

**Canonical question — after every file is updated, what runtime systems still hold old state?** Only the **ЮKassa dashboard webhook registration** and the **merchant credentials**, both owner-provisioned and external. No databases, OS schedulers, or build artifacts carry a stale Stars identity that would break at runtime.

## Common Pitfalls

### Pitfall 1: Granting access on payment creation or on the unsigned webhook body
**What goes wrong:** A forged `payment.succeeded` POST (the endpoint is public; ЮKassa doesn't sign) grants free balance; or grant-on-create gives access before money moves.
**Why it happens:** Treating the webhook body as trusted, or conflating "payment created" with "payment paid."
**How to avoid:** IP-allowlist the endpoint AND **re-fetch the object by id**, grant only on the re-fetched `succeeded` (Pattern 3/5). Never touch balances in the create handler.
**Warning signs:** Any code path that increments `paid_spreads_balance` reading a status from the request body; a webhook handler with no `Payment.find_one`.

### Pitfall 2: Double-grant on webhook redelivery
**What goes wrong:** ЮKassa redelivers `payment.succeeded` (it retries until 200) → balance granted twice.
**Why it happens:** No exactly-once guard; grant keyed on event arrival, not on a state transition.
**How to avoid:** Conditional `UPDATE ... WHERE status=CREATED ... RETURNING` — grant only if the row actually transitioned (Pattern 5). UNIQUE `provider_payment_id` is the backstop. Always return 200 once handled (even on a duplicate) so redelivery stops.
**Warning signs:** Grant logic that runs unconditionally after parsing the event; missing UNIQUE on the provider id.

### Pitfall 3: Blocking the event loop with the sync SDK
**What goes wrong:** `Payment.create(...)` called directly in an `async def` handler blocks the single event loop → all requests stall during the ЮKassa round-trip.
**Why it happens:** The SDK looks async-friendly but is sync (`requests`).
**How to avoid:** `await anyio.to_thread.run_sync(partial(Payment.create, body, key))` for **every** SDK call (Pattern 1).
**Warning signs:** `Payment.`/`Refund.` called without `to_thread`; latency spikes under concurrency in tests.

### Pitfall 4: Amount/price tampering from the client
**What goes wrong:** Client posts a `price` or `amount` and the backend trusts it → user pays 1₽ for the 10-pack.
**Why it happens:** Convenience — echoing a client-sent amount into `Payment.create`.
**How to avoid:** The create endpoint accepts only a `product_slug` (or id); **recompute `amount` from the `products` row** server-side (PAY-03 / T-07-AMOUNT). Mirror `reading.py`'s server-authoritative posture.
**Warning signs:** `amount` or `price` as a field on the create request schema.

### Pitfall 5: Recurring Idempotence-Key reuse vs. uniqueness confusion
**What goes wrong:** Either every renewal reuses one key (ЮKassa returns the *first* charge, no new money) — or a transient-retry uses a *new* key and double-charges.
**Why it happens:** Misunderstanding ЮKassa's 24h idempotency: same key+same body → returns original; different key → new charge.
**How to avoid:** Use a **deterministic per-period** key `f"renew:{sub_id}:{period_index}"` — a retry within the period reuses it (safe no-op if the first succeeded), the next period gets a new key. For one-time creates use a fresh `uuid4` per user attempt (a retry of the *same* attempt should reuse it).
**Warning signs:** A global constant key; or `uuid4()` regenerated inside a retry loop.

### Pitfall 6: RUB amount formatting (string, 2 decimals)
**What goes wrong:** Sending `amount.value` as a number or `"299"` instead of `"299.00"` → validation error or wrong amount; integer-kopecks confusion.
**Why it happens:** ЮKassa expects `value` as a **string with 2 decimal places** in major units (rubles), e.g. `"299.00"`, not kopecks, not a float.
**How to avoid:** Store the product price as an integer (rubles or kopecks — pick one and document) and format to `"{:.2f}"`; keep the `currency:"RUB"`. Note: the existing `products.stars_price` (Integer) becomes the RUB price — decide rubles-as-integer (e.g. 299 → `"299.00"`) and centralize the formatter.
**Warning signs:** `"value": amount` where amount is an int/float; kopecks math sprinkled around.

### Pitfall 7: Telegram WebView can't return a callback from an external payment page
**What goes wrong:** Developer expects `openInvoice`'s `invoiceClosed` callback to fire for the ЮKassa page — it never does (that callback is ONLY for Telegram-native invoices).
**Why it happens:** Conflating `openInvoice` (Telegram Stars/native) with `openLink` (arbitrary URL).
**How to avoid:** Use `openLink(confirmation_url)` (no status callback); detect return via the `activated` event (Bot API 8.0+) or visibilitychange, then **poll `GET /api/me`** until the webhook-granted state appears (D-07). Treat the webhook as truth; the return is UX only.
**Warning signs:** `openInvoice` used with a ЮKassa URL; UI that waits for a non-existent callback.

## Code Examples

Verified shapes from the live ЮKassa docs.

### Create a one-time payment (redirect)
```bash
# Source: yookassa.ru/developers/using-api/interaction-format + payment-process (verified 2026-06-27)
curl https://api.yookassa.ru/v3/payments \
  -X POST \
  -u <SHOP_ID>:<SECRET_KEY> \
  -H 'Idempotence-Key: <uuid4>' \
  -H 'Content-Type: application/json' \
  -d '{
    "amount": { "value": "169.00", "currency": "RUB" },
    "capture": true,
    "confirmation": { "type": "redirect", "return_url": "https://t.me/<bot>/<app>" },
    "description": "3 расклада",
    "metadata": { "payment_uuid": "<our payments.id>" }
  }'
# → 200 { "id":"<pid>", "status":"pending", "amount":{...},
#         "confirmation": { "type":"redirect", "confirmation_url":"https://..." }, ... }
```

### First subscription payment with saved method
```json
// Source: yookassa.ru/.../widget/additional-settings/save-payments (verified)
// POST /v3/payments  (Idempotence-Key header)
{
  "amount": { "value": "299.00", "currency": "RUB" },
  "capture": true,
  "save_payment_method": true,
  "confirmation": { "type": "redirect", "return_url": "https://t.me/<bot>/<app>" },
  "description": "Лунный доступ — 30 дней",
  "metadata": { "payment_uuid": "<our payments.id>" }
}
// success response includes:  "payment_method": { "type":"bank_card", "id":"<payment_method_id>", "saved": true }
//   → store <payment_method_id> on subscriptions for renewals
```

### Merchant-initiated renewal charge (no confirmation block)
```json
// Source: yookassa.ru/developers/payment-acceptance/scenario-extensions/recurring-payments/pay-with-saved (verified)
// POST /v3/payments  (Idempotence-Key: renew:<sub_id>:<period_index>)
{
  "amount": { "value": "299.00", "currency": "RUB" },
  "capture": true,
  "payment_method_id": "<saved payment_method_id>",
  "description": "Лунный доступ — продление"
}
// NOTE: no "confirmation" → charged without user interaction. ЮKassa does NOT do this on a
// schedule; the merchant sends this request when a period is due (Pattern 4).
```

### Refund (partial or full)
```json
// Source: yookassa.ru/developers/payment-acceptance/after-the-payment/refunds (verified)
// POST /v3/refunds  (Idempotence-Key: refund:<payment_id>)
{
  "amount": { "value": "169.00", "currency": "RUB" },
  "payment_id": "<succeeded payment id>"
}
// → { "id":"<refund_id>", "status":"succeeded", "amount":{...}, "payment_id":"...", ... }
// Partial allowed (min 1 RUB; remaining must be >=1 RUB or exactly 0). Payment must be 'succeeded'.
```

### Webhook notification envelope (what ЮKassa POSTs — UNSIGNED, re-fetch before trusting)
```json
// Source: yookassa.ru/developers/using-api/webhooks (verified)
{
  "type": "notification",
  "event": "payment.succeeded",
  "object": { "id": "<pid>", "status": "succeeded", "amount": {...}, "metadata": {...}, ... }
}
// Handler: take object.id, IGNORE object.status, GET /v3/payments/<id>, grant only if that == succeeded.
```

### SDK wrapper + webhook handler (FastAPI)
```python
# Source: pypi.org/project/yookassa + webhooks doc. Mirrors the codebase's service/router split.
# backend/app/services/payments.py
from functools import partial
import anyio
from yookassa import Configuration, Payment, Refund
from app.core.config import settings

Configuration.configure(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY)

async def find_payment(pid: str):
    return await anyio.to_thread.run_sync(partial(Payment.find_one, pid))

# backend/app/api/payments.py (webhook excerpt)
from ipaddress import ip_address, ip_network
YOOKASSA_NETS = [ip_network(n) for n in (
    "185.71.76.0/27","185.71.77.0/27","77.75.153.0/25","77.75.156.11/32",
    "77.75.156.35/32","77.75.154.128/25","2a02:5180::/32",
)]
def from_yookassa(ip: str) -> bool:
    addr = ip_address(ip)
    return any(addr in net for net in YOOKASSA_NETS)
```

## State of the Art

| Old Approach (CLAUDE.md / ТЗ) | Current Approach (this phase) | When Changed | Impact |
|-------------------------------|-------------------------------|--------------|--------|
| Telegram Stars (XTR), aiogram `create_invoice_link` / `successful_payment` | ЮKassa v3 REST (RUB), direct HTTP webhook | This phase (owner pivot, D-01) | No aiogram wiring; RUB payouts; the webhook is a plain FastAPI route. |
| `pre_checkout_query` (<10s) validation | Create-time server-side validation (recompute price, check active/unused) | Pivot | ЮKassa has no pre-checkout; validate when creating the payment. |
| `provider_token` / Telegram Payments | `shopId` + secret key, HTTP Basic | Pivot | New `YOOKASSA_*` env; PCI scope stays with ЮKassa. |
| Native recurring Stars (`subscription_period=2592000`, auto-renew) | Merchant-initiated saved-card charges (no auto-charge) | Pivot | A scheduler/lazy mechanism is REQUIRED (Pattern 4); DB window authoritative. |
| `openInvoice` (Telegram-native) | `openLink(confirmation_url)` + poll `GET /api/me` | Pivot | No invoice callback; return detected via `activated`/visibility + polling. |
| `refundStarPayment` (21-day window) | `POST /v3/refunds` (window: cards ~3yr / ~15mo acquirer-practical, partial OK) | Pivot | Much wider window; partial refunds supported. |

**Deprecated/outdated for this phase:**
- `CLAUDE.md` §"Telegram Stars Payments — EXACT Flow", §Payments constraint, "External acquirers → use Stars" — **superseded by D-01** (keep the rest of CLAUDE.md).
- The `WEBHOOK_SECRET` env's "Phase 7 bot wiring" note — ЮKassa uses no such header.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `products.stars_price` (Integer) is repurposed as the **RUB price as an integer rubles** (e.g. 299), formatted to `"299.00"` for ЮKassa. Could instead be kopecks. | Schema Delta / Pitfall 6 | Wrong charge amount. **Planner/owner must pick rubles-int vs kopecks and document.** Low risk (additive rename column instead if clarity wanted). |
| A2 | Single backend container on timeweb (per DEPLOY.md) → in-process APScheduler is safe. | Pattern 4 | If scaled to >1 instance, duplicate charge attempts (mitigated by deterministic Idempotence-Key, but cron fallback is cleaner). |
| A3 | The merchant account is configured such that a **simple payment without a `receipt`/54-ФЗ fiscalization block** is accepted (no online cash-register obligation, or ЮKassa handles fiscalization server-side). | Open Questions | If 54-ФЗ applies (ИП/ООО on ОСН/УСН selling to individuals), payments may require a `receipt` object → extra fields + customer email/phone. **Owner must confirm tax/fiscal status.** |
| A4 | `return_url` can be a `https://t.me/<bot>/<app>` deep link that reopens the Mini App; otherwise any https page that instructs "return to Telegram". | Frontend / Diagram | If the deep link doesn't reopen the app cleanly, UX degrades to "switch back manually" — still works (webhook grants regardless). |
| A5 | ЮKassa's webhook IP ranges (185.71.76.0/27, 185.71.77.0/27, 77.75.153.0/25, 77.75.156.11, 77.75.156.35, 77.75.154.128/25, 2a02:5180::/32) are current as of 2026-06. | Security / Code Examples | If ЮKassa changes ranges, valid webhooks get 403. **Make the list env-overridable (`YOOKASSA_WEBHOOK_IPS`) and re-fetch (Pattern 3) is the real guard anyway.** |
| A6 | The SDK method signatures are `Payment.create(params, idempotency_key)`, `Payment.find_one(id)`, `Refund.create(params, idempotency_key)`. | Code Examples | Verify against the installed 3.11.0 SDK at implementation time (the SDK is [VERIFIED] present; exact kwarg names confirmed via the SDK's README examples — re-check in code). |

**If this table is empty:** it is not — A1 (price units), A3 (54-ФЗ), and A2 (scaling) are the decisions the planner/owner should confirm before locking.

## Open Questions

1. **54-ФЗ / receipts (fiscalization)?**
   - What we know: ЮKassa supports a `receipt` object; whether it's *required* depends on the merchant's legal form and tax regime. The CONTEXT does not mention it; deferred-list does not exclude it explicitly.
   - What's unclear: Is the owner's merchant entity obligated to send fiscal receipts (online cash register) for digital-service sales to individuals?
   - Recommendation: **Ask the owner.** If yes, add a `receipt` block (customer email/phone + item) to `Payment.create` — treat as a small follow-up, not a blocker for the happy path. Flag in the plan as a conditional task.

2. **Price unit convention (A1).**
   - What we know: `products.stars_price` is `Integer`; ЮKassa wants `"value":"299.00"` (string, major units).
   - Recommendation: Store integer **rubles** (299) and format `"{:.2f}"`. Centralize in one `format_rub(price:int)->str` helper. Optionally rename the column `price_rub` in migration 0004 for clarity (additive: add new, backfill, keep old nullable or drop in dev).

3. **`return_url` target + reopen UX (A4).**
   - Recommendation: Use the Mini App deep link; verify on-device that returning reopens the app. The webhook grants access regardless, so this is UX polish, not correctness.

4. **Scheduler trigger for scale-out (A2).**
   - Recommendation: Ship APScheduler now; document the timeweb-cron→internal-endpoint fallback. Keep charge logic trigger-agnostic in `services/payments.py`.

## Environment Availability

> Phase 7 adds an external dependency (ЮKassa) and optionally a scheduler. Probe results below.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `yookassa` SDK (PyPI) | All ЮKassa calls (PAY-02/04/06/07) | ✓ installable | 3.11.0 | Thin `httpx` client (more work) |
| `anyio` | Threadpool wrapper | ✓ (transitive FastAPI dep) | 4.14.1 | `loop.run_in_executor` |
| `tenacity` | Renewal retry | ✓ (already a dep) | 9.x | manual bounded loop |
| `APScheduler` | Proactive renewal sweep (Pattern 4) | ✓ installable | 3.11.2 | Lazy charge-on-access only; or timeweb cron |
| Postgres 16 | All persistence | ✓ (managed, DEPLOY.md) | 16 | — |
| Redis 7 | (optional) fast idempotency guard | ✓ (managed) | 7 | DB UNIQUE is the real guard |
| **ЮKassa merchant account** | shop_id + secret_key + dashboard webhook | ✗ (owner-provisioned, external) | — | **No fallback — owner must create the account** (ИП/самозанятость/юрлицо for payout) |
| **Public HTTPS backend URL** | ЮKassa → webhook delivery | ✓ (timeweb app, url A) | — | ngrok/cloudflared for local test |

**Missing dependencies with no fallback:**
- **ЮKassa merchant account + dashboard webhook registration** — owner-side prerequisite. The plan can be fully built/tested in **test mode** (test shop_id/secret + sandbox cards) without the live account; live payout needs the verified merchant entity.

**Missing dependencies with fallback:**
- APScheduler — fall back to lazy charge-on-access (still correct) or a timeweb scheduled job.

## Validation Architecture

> nyquist_validation is enabled (config has no `workflow.nyquist_validation:false`). Section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (`asyncio_mode=auto`) `[VERIFIED: pyproject.toml]` |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`) |
| Quick run command | `cd backend && uv run pytest tests/test_payments_*.py -x` |
| Full suite command | `cd backend && uv run pytest` (frontend: vitest via `node_modules` — pnpm not in PATH, per MEMORY) |

**No-real-charge mandate:** every payment test runs against a **fake ЮKassa** (inject a fake client via the same `app.dependency_overrides` / constructor-seam pattern `reading.py` uses for `FakeLLM`/`FakeSafety`). NO test ever calls `api.yookassa.ru`. Use a `FakeYooKassa` exposing `create_payment` / `find_payment` / `create_refund` returning canned objects.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PAY-01 | `GET /api/products` returns active products only | integration | `uv run pytest tests/test_payments_api.py::test_products_list -x` | ❌ Wave 0 |
| PAY-02 | create returns `confirmation_url`, writes CREATED row, no grant | integration | `...::test_create_payment_no_grant -x` | ❌ Wave 0 |
| PAY-03 | amount recomputed server-side; inactive product → 4xx; client price ignored | unit+integration | `...::test_create_recomputes_price -x` | ❌ Wave 0 |
| PAY-04 | webhook `payment.succeeded` (re-fetched) grants balance/subscription | integration | `...::test_webhook_grants_on_refetched_succeeded -x` | ❌ Wave 0 |
| PAY-05 | redelivered event grants exactly once; body status ignored; non-ЮKassa IP rejected | integration | `...::test_webhook_idempotent_and_ip_gated -x` | ❌ Wave 0 |
| PAY-06 | renewal uses `payment_method_id`+deterministic key; cancel stops next charge, keeps window | unit+integration | `...::test_recurring_renewal_and_cancel -x` | ❌ Wave 0 |
| PAY-07 | refund flips status=refunded, adjusts access; refund webhook idempotent | integration | `...::test_refund_adjusts_access -x` | ❌ Wave 0 |
| PAY-08 | (FE) buy opens `openLink`, polls `/api/me`; honest failure copy | vitest + manual | `pnpm -C frontend vitest run src/shop` (+ live UAT) | ❌ Wave 0 |
| (gate) | consume-gate spends free→subscription→paid; honest-fail refunds the right bucket | unit | `uv run pytest tests/test_reading_buckets.py -x` (extend existing) | ⚠️ extend |

**Idempotency test (critical):** simulate the exact same `payment.succeeded` notification twice → assert balance incremented once and the second call is a 200 no-op (Pattern 5).

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_payments_*.py -x` (+ the bucket test if `reading.py` touched).
- **Per wave merge:** `uv run pytest` (full backend) + `pnpm -C frontend vitest run`.
- **Phase gate:** full backend + frontend suites green before `/gsd-verify-work`; plus the live test-mode UAT smokes (sandbox card → webhook → granted balance; renewal; refund) listed for HUMAN-UAT.

### Wave 0 Gaps
- [ ] `backend/tests/test_payments_api.py` — products/create/webhook/refund (PAY-01..07) with `FakeYooKassa`
- [ ] `backend/tests/test_payments_service.py` — grant idempotency, recurring key logic, refund reconciliation
- [ ] `backend/tests/conftest.py` — add `FakeYooKassa` fixture + `dependency_overrides` wiring (mirror FakeLLM)
- [ ] `backend/tests/test_reading_buckets.py` — extend to assert subscription/paid consume + correct-bucket refund
- [ ] `frontend/src/shop/*.test.tsx` — buy button → `openLink` called, poll-until-granted, honest-fail copy
- [ ] (No framework install needed — pytest/vitest already present.)

## Security Domain

> `security_enforcement` is enabled (absent = enabled). Section included. This is a money path — treat every item as load-bearing.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | All buy/refund/cancel routes behind `get_current_user` (Bearer JWT); refund behind `require_admin` (existing deps). |
| V3 Session Management | yes (reuse) | Existing JWT seam; no new session surface. |
| V4 Access Control | yes | Refund = admin-only; a user can only create payments/cancel subs for **their own** JWT identity (never a body user_id — T-07-IDOR, mirror reading.py). |
| V5 Input Validation | yes | Pydantic on all bodies; create accepts only `product_slug` (no client amount); webhook envelope validated; `{payment_id}` path typed. |
| V6 Cryptography | yes | NEVER hand-roll; ЮKassa owns TLS/PCI. Secret key only in env (fail-fast). Idempotence-Key = `uuid4`. |
| V9 Communications | yes | HTTPS only (timeweb). Webhook IP-allowlist + re-fetch over TLS. |
| V13 API / Webhooks | yes | Unsigned webhook → IP allowlist + re-fetch by id; always 200 on handled/dup; 4xx/5xx only to trigger redelivery. |

### Known Threat Patterns for {ЮKassa + FastAPI + Telegram Mini App}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| **T-07-WEBHOOK-FORGE** — attacker POSTs fake `payment.succeeded` to the public webhook | Spoofing | IP-allowlist ЮKassa ranges **AND** re-fetch `GET /v3/payments/{id}`; grant only on re-fetched `succeeded` (never the body). |
| **T-07-REPLAY** — same valid event redelivered to double-grant | Tampering / Elevation | Conditional `UPDATE ... WHERE status=CREATED ... RETURNING` + UNIQUE `provider_payment_id`; exactly-once grant. |
| **T-07-AMOUNT** — client sends a low `price`/`amount` | Tampering | Recompute amount from the `products` row server-side; no amount field on the create schema. |
| **T-07-GRANT-ON-CREATE** — access before payment | Elevation | Grant only in the webhook after re-fetch; create handler never mutates balances. |
| **T-07-IDOR** — buy/cancel/refund for another user's resource | Elevation | Scope to JWT `sub`; refund = `require_admin`; `{id}` ownership-checked → 404 (no existence leak), mirroring reading.py. |
| **T-07-SECRET-LEAK** — shop secret / amount logic exposed | Info Disclosure | Secret only in env (fail-fast like JWT_SECRET); never in responses/logs; `raw_update` JSONB is server-side audit, never returned to clients. |
| **T-07-DOUBLE-CHARGE** — renewal charged twice (retry or multi-instance) | Tampering | Deterministic per-period Idempotence-Key (24h ЮKassa idempotency); cron fallback for true multi-instance. |
| **T-07-CARD-DATA** — app touches PAN | Info Disclosure | Redirect/widget hosted by ЮKassa; the app never sees card data (PCI scope stays with ЮKassa). |
| **T-07-WEBHOOK-DOS** — flood the public webhook | DoS | IP-allowlist drops non-ЮKassa early; cheap pre-checks before any DB/SDK work; reuse Redis throttle pattern if needed. |
| **T-07-OPEN-REDIRECT** — attacker-controlled `return_url` | Tampering | `return_url` is server-constructed (the app's own deep link), never client-supplied. |

## Project Constraints (from CLAUDE.md)

The planner must honor these (CLAUDE.md is authoritative except its Stars §, superseded by D-01):
- **No Celery/RQ/Arq** — the recurring scheduler must be broker-free (Pattern 4 complies: APScheduler in-process / lazy / timeweb cron).
- **Backend stack:** FastAPI + SQLAlchemy 2.0 async + asyncpg + Alembic + Pydantic v2 + Redis. New code uses `select()`/`AsyncSession`/`Mapped[]` (no legacy Query), Pydantic v2 (`from_attributes`, `model_dump`).
- **Server-authoritative everything** — payments must be server-verified (recompute price, re-fetch status). No client trust.
- **Secrets via env, validated at startup** — `YOOKASSA_*` join the fail-fast `Settings` (no defaults).
- **Brand voice (SAFE-06)** — shop/success/failure copy uses ритуальные formulations; no "AI/нейросеть". Honest failure copy «деньги не списаны / доступ не выдан» (D-13).
- **Frontend stack:** React 19 + Vite + Tailwind v4 + `motion` (`import * as m from "motion/react-m"`, `AnimatePresence` from `motion/react`) + Zustand (UI) + TanStack Query (server state — `useMe`, products). Do NOT duplicate server state into Zustand.
- **mobile-first, Telegram SDK insets** (not CSS env()), safe-area, sticky CTA.
- **Worktrees=false on Windows** (sequential execute), deps in `uv` venv (`uv run pytest`), pnpm not in PATH (vitest via node_modules) — per MEMORY.
- **Migrations hand-written** (no live DB for autogenerate) and reversible — migration 0004 follows the 0002/0003 style.
- **Testing:** 80% coverage target; TDD; AAA; no real external calls (FakeYooKassa, mirror FakeLLM/FakeSafety seam).

## Schema Delta (migration 0004)

Latest migration is **0003** (`down_revision` for the new one = `"0003_reading_answer_style"`). Hand-written, reversible (style: `0003_reading_answer_style.py`). All changes are **additive** (no data migration needed — no real payments exist; PAY-* all Pending).

**`payments`** — add:
- `provider_payment_id` `String` UNIQUE nullable index — the ЮKassa payment id (D-06). *(Recommendation: ADD this rather than rename `telegram_payment_charge_id`, to avoid touching the existing indexed column; leave the old column nullable/unused or drop it in the same migration since no data exists. Planner decides — additive is lowest-risk.)*
- `confirmation_url` `String` nullable — returned by create, surfaced to the FE.
- `idempotence_key` `String` nullable — the per-attempt key (audit/retry-safe).
- flip `provider` server_default `'telegram_stars'`→`'yookassa'`, `currency` `'XTR'`→`'RUB'` (for new rows).
- `payment_method_id` `String` nullable — if a one-time pack also saves a method (else only on subscriptions).

**`subscriptions`** — add:
- `payment_method_id` `String` nullable — the saved ЮKassa method for renewals (D-08). *(The existing `telegram_payment_charge_id` `String` NOT NULL must become nullable or be repurposed — currently NOT NULL, which would break a ЮKassa insert. ADD `provider_payment_id` nullable + make `telegram_payment_charge_id` nullable.)*
- (optional) `last_charge_at` `TIMESTAMP` nullable + `period_index` `Integer` default 0 — to build the deterministic renewal Idempotence-Key (Pitfall 5).

**`products`** — D-15 seed + A1 decision:
- Option A (lowest churn): keep `stars_price` column, treat as **integer rubles**, format `"{:.2f}"`. Document in the model docstring.
- Option B (clarity): add `price_rub` `Integer`, backfill, deprecate `stars_price`. Additive.
- Seed `products.json`: `pack_1` (69), `pack_3` (169), `pack_10` (449), `sub_moon` (299, `product_type=subscription`, `subscription_days=30`); packs set `spreads_amount`, sub sets `subscription_days`.

**Enums:** `PaymentStatus` already has `CREATED/PAID/FAILED/REFUNDED/CANCELED` — sufficient. `PRE_CHECKOUT_APPROVED` is now unused (Stars-only) but harmless; leave it. `SubscriptionStatus` (`ACTIVE/CANCELED/EXPIRED/PAYMENT_FAILED`) — sufficient for D-10 + renewal-fail.

**`LimitsOut` / `GET /api/me`:** already exposes `paid_spreads_balance`, `subscription_spreads_limit/used`. Add subscription **window/status** (e.g. `subscription_active: bool`, `subscription_period_end: datetime|None`) so the shop shows «активна до DD.MM» (extend `project_limits`).

## Sources

### Primary (HIGH confidence)
- **yookassa.ru/developers/using-api/interaction-format** — base URL `https://api.yookassa.ru/v3/`, HTTP Basic (shopId+secret), `Idempotence-Key` (POST/DELETE, ≤64 chars, uuid4 rec., 24h same-key→original; HTTP 500 = verify status). [VERIFIED via WebFetch 2026-06-27]
- **yookassa.ru/developers/payment-acceptance/getting-started/payment-process** — lifecycle `pending→(waiting_for_capture)→succeeded|canceled`; capture true/false; `confirmation_url`/`return_url`; status via webhook or GET. [VERIFIED]
- **yookassa.ru/developers/using-api/webhooks** — events (`payment.succeeded/.waiting_for_capture/.canceled`, `refund.succeeded`); envelope `{type,event,object}`; dashboard vs API registration; **IP ranges** (185.71.76.0/27, 185.71.77.0/27, 77.75.153.0/25, 77.75.156.11, 77.75.156.35, 77.75.154.128/25, 2a02:5180::/32); **no signing → re-fetch/“check current status”.** [VERIFIED]
- **yookassa.ru/.../recurring-payments/pay-with-saved** — renewal `POST /v3/payments` with `payment_method_id`, no confirmation; **merchant configures frequency (no auto-charge).** [VERIFIED]
- **yookassa.ru/.../widget/additional-settings/save-payments** — first payment `save_payment_method:true`; save `payment_method.id`. [VERIFIED]
- **yookassa.ru/developers/payment-acceptance/after-the-payment/refunds** — `POST /v3/refunds {amount,payment_id}`; partial (min 1₽) vs full; payment must be `succeeded`; window cards ~3yr (~15mo acquirer). [VERIFIED]
- **core.telegram.org/bots/webapps** — `openLink(url[,options])` (external browser, app not closed; `try_instant_view`); `openInvoice` (Telegram-native only, `invoiceClosed`); `activated`/`deactivated` (Bot API 8.0+). [VERIFIED]
- **pypi.org/project/yookassa** — official SDK 3.11.0 (2026-06-26), sync (`requests`), Py 3.7–3.12, `Configuration.configure(account_id, secret_key)`. [VERIFIED + slopcheck [OK] + pip index]
- **pypi.org/project/httpx** — 0.28.1, async + Basic auth. [VERIFIED]
- **Codebase** — `billing.py`, `enums.py`, `reading.py` (Bucket seam, conditional UPDATE...RETURNING idempotency, FakeLLM/FakeSafety seam), `config.py` (fail-fast), `deps.py` (`require_admin`), `redis.py` (Lua throttle), `loader.py` (upsert-by-slug), `users.py`/`auth.py` (`LimitsOut`/`project_limits`), `main.py` (lifespan), `0003_*.py` (migration style), `pyproject.toml` (deps), `PaywallSheet.tsx`/`ProfileScreen.tsx`/`telegram.ts`/`client.ts`, `DEPLOY.md`/`.env.example`. [VERIFIED by direct read]

### Secondary (MEDIUM confidence)
- WebSearch (yookassa.ru results) — create/refund JSON examples, metadata key-value, idempotency-on-retry semantics, recurring best practice. Cross-checked against the primary docs above.
- WebSearch (Telegram ToS) — telegram.org/tos/mini-apps + core.telegram.org/bots/payments-stars: **digital goods must use Stars; external link for digital goods can get the bot banned** (the D-03 risk). MEDIUM (policy wording paraphrased; owner already accepted).
- WebSearch — APScheduler `AsyncIOScheduler` in FastAPI lifespan; unofficial async ЮKassa clients exist (rejected).

### Tertiary (LOW confidence — flagged for validation)
- Exact SDK kwarg names (`idempotency_key` arg position) — re-verify against installed 3.11.0 at implementation (A6).
- ЮKassa IP ranges currency over time (A5) — make env-overridable; re-fetch is the real guard.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `yookassa` SDK + versions registry-verified (slopcheck [OK], pip index); httpx/anyio/APScheduler/tenacity verified.
- API shapes (create/recurring/refund/webhook/lifecycle): HIGH — verified against live yookassa.ru/developers pages this session.
- Architecture / idempotency / gate integration: HIGH — maps directly onto verified existing codebase patterns (conditional UPDATE...RETURNING, Bucket seam, FakeLLM seam).
- Recurring scheduler choice: MEDIUM — sound, broker-free, with documented multi-instance caveat (A2); the lazy backbone is HIGH-correctness, the proactive sweep is a discretion call.
- Telegram WebView payment-return UX: HIGH for the API facts (`openLink` vs `openInvoice`, `activated`); MEDIUM for the exact on-device reopen behavior (A4) — webhook makes it non-load-bearing.
- 54-ФЗ/receipts: LOW — depends on owner's legal/tax status (Open Q1).

**Research date:** 2026-06-27
**Valid until:** ~2026-07-27 (30 days; ЮKassa API v3 is stable, but re-verify IP ranges + SDK version at implementation, and confirm the 54-ФЗ + price-unit decisions with the owner before locking the plan).
