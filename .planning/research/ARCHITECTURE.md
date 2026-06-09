# Architecture Research

**Domain:** Telegram Mini App — AI-powered tarot readings (FastAPI + aiogram + React MiniApp + PostgreSQL + Redis + LLM)
**Researched:** 2026-06-09
**Confidence:** HIGH (component boundaries, data flows, build order grounded in TZ §12/§13/§14/§23/§29 + verified Telegram/aiogram patterns)

> Source of truth for requirements is `.planning/REFERENCE-TZ.md`. This file translates that spec into explicit component boundaries, data-flow direction, and a dependency-ordered, **Vertical-MVP** build sequence (each phase ships an end-to-end user-visible capability, not a horizontal layer). It reflects the project's locked decisions: single structured LLM call per reading, **no background queue** (Celery/RQ/Arq excluded), Redis for rate-limit/cache only, backend-only card draw + limit checks, admin as guarded routes + allowlist.

---

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                         TELEGRAM CLIENT (in-app)                       │
│   ┌──────────────────────────┐        ┌──────────────────────────┐    │
│   │   React Mini App (WebView)│        │   Telegram Chat / Bot UI │    │
│   │  Zustand · React Query    │        │  invoice button, /start  │    │
│   │  Framer Motion · TG SDK   │        │  payment confirmation    │    │
│   │  /admin guarded routes    │        │                          │    │
│   └────────────┬─────────────┘        └────────────┬─────────────┘    │
│        initData │ HTTPS (Bearer JWT)   Bot API updates│ (webhook)       │
└─────────────────┼─────────────────────────────────────┼────────────────┘
                  │                                       │
                  ▼                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    BACKEND PROCESS (FastAPI, ASGI)                      │
│  ┌──────────────────┐  ┌───────────────────┐  ┌────────────────────┐   │
│  │  REST API routers │  │ aiogram dispatcher │  │  Admin API (guard) │   │
│  │ /api/auth /me     │  │  (in-process):     │  │ /api/admin/* +     │   │
│  │ /decks /spreads   │  │  pre_checkout_query│  │ allowlist check    │   │
│  │ /readings /products│ │  successful_payment│  │                    │   │
│  │ /payments/*       │  │  refund            │  │                    │   │
│  └───────┬──────────┘  └─────────┬─────────┘  └──────────┬─────────┘   │
│          └───────────────┬───────┴────────────────────────┘            │
│                          ▼  SERVICE LAYER (no business logic in routers)│
│  TelegramAuth · Deck · Spread · CardDraw · Reading · PromptEngine ·     │
│  Safety(classifier) · LLMService(swappable) · Limit · Payment ·         │
│  Subscription · Analytics · Admin                                       │
│          │                    │                      │                  │
│          ▼                    ▼                      ▼                  │
│  ┌──────────────┐    ┌──────────────┐      ┌──────────────────┐        │
│  │  PostgreSQL  │    │    Redis     │      │  LLM Provider     │        │
│  │ (SQLAlchemy  │    │ rate-limit · │      │ (Claude default,  │        │
│  │  2.x async,  │    │ card-meaning │      │  HTTP, sync call  │        │
│  │  Alembic)    │    │ cache · lock │      │  in request)      │        │
│  └──────────────┘    └──────────────┘      └──────────────────┘        │
└──────────────────────────────────────────────────────────────────────┘
```

### The Bot/Backend Boundary (key decision)

The monorepo names `/bot` as a separate folder, but **the aiogram bot is not a separate HTTP server**. aiogram 3.x can ingest updates from any web framework via `dispatcher.feed_webhook_update(bot, update)` — Telegram POSTs to one `/api/payments/webhook` (or `/tg/webhook`) route served by FastAPI, which constructs an `Update` and feeds the dispatcher (verified: aiogram docs, "you can pass incoming request to aiogram's webhook controller from any web framework").

**Recommendation: one deployable backend process** hosting both the REST API and the aiogram dispatcher. The `/bot` folder is a logical module (handlers, FSM, payment update logic) imported by the FastAPI app, not a standalone service. Rationale:

- Payment grant logic (`successful_payment` → increment `user_limits.paid_spreads_balance`) needs the same DB session, services, and idempotency guard as the REST API. A separate process means duplicating the service layer or adding inter-service RPC — overkill for MVP.
- No background queue exists (generation is one sync LLM call), so there is no worker process to co-locate the bot with.
- A single Telegram **webhook secret token** header (`X-Telegram-Bot-Api-Secret-Token`) protects the route; the rest of the API uses JWT.

A separate `bot` worker becomes worth it only post-MVP (push "card of the day", scheduled jobs). Keep handlers in `/bot` so extraction later is a deployment change, not a rewrite.

### Component Responsibilities

| Component | Responsibility (owns) | Talks to | Typical Implementation |
|-----------|----------------------|----------|------------------------|
| **React Mini App** | All UI, ritual animation, progressive reveal over already-ready data, state | Backend REST (Bearer JWT) | Vite SPA, Zustand (client state), React Query (server state), Framer Motion |
| **Admin (frontend)** | CRUD UI for decks/cards/prompts/products, dashboards | Admin API | Same SPA, guarded `/admin` routes; server is the real gate |
| **REST API (FastAPI)** | HTTP contract, auth dependency, request validation, calls services | Service layer, Postgres, Redis | FastAPI routers + Pydantic; thin — no business logic |
| **aiogram dispatcher (in-process)** | Telegram payment updates (`pre_checkout_query`, `successful_payment`, refunds), bot `/start` deep-link | PaymentService, Postgres | aiogram 3.x, webhook mode, fed by FastAPI route |
| **TelegramAuthService** | Validate `initData` HMAC + `auth_date`, upsert user, issue JWT | Postgres | HMAC-SHA256 with `WebAppData` secret; PyJWT |
| **CardDrawService** | Crypto-secure shuffle, draw N, assign orientation (70/30), store debug hash | Postgres (deck_cards) | `secrets`/`random.SystemRandom` |
| **ReadingService** | Orchestrate reading: limit check → draw → pending → LLM → validate → persist → decrement | Limit, CardDraw, Prompt, Safety, LLM, Postgres | One DB transaction boundary per reading |
| **PromptEngine** | Assemble system + deck-modifier + position + card context from versioned `prompt_templates` | Postgres (prompt_templates) | Template fill; records `prompt_version` |
| **SafetyService** | Classify question (normal / *_sensitive / crisis) pre-generation; inject safety modifier or short-circuit crisis | (regex prefilter + classifier) | Cheap: regex prefilter, then classification folded into the main call |
| **LLMService** | Swappable provider abstraction; one structured JSON call returning all cards + summary | LLM provider (HTTP) | Claude default; JSON-schema-validated response |
| **LimitService** | Free weekly limit (3/wk + weekly reset), paid balance, subscription window check | Postgres (user_limits), Redis (throttle) | DB is source of truth; Redis for abuse throttle |
| **PaymentService** | Invoice creation, payload idempotency, grant entitlement on `successful_payment`, refunds | Postgres (payments/products/subscriptions) | Called by both REST (create invoice) and dispatcher (grant) |
| **AnalyticsService** | Append `app_events`; surface dashboard metrics | Postgres (app_events) | Fire-and-forget inserts; never block UX |
| **PostgreSQL** | All durable state (15 tables, TZ §13) | — | SQLAlchemy 2.x async, Alembic |
| **Redis** | Rate-limit counters, card-meaning cache, optional per-user reading lock | — | **Not** a queue; cache/throttle only |

---

## Recommended Project Structure

Monorepo (`/frontend`, `/backend`, `/bot`, `/admin` as routes, `/docs`) per PROJECT.md. `/bot` is a Python module imported by the backend, not a separate service.

```
zerkalo-sudby/
├── docker-compose.yml          # postgres + redis + backend (+ frontend dev)
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app, lifespan, set_webhook, mount routers
│   │   ├── api/                # ROUTERS ONLY (thin, no business logic)
│   │   │   ├── deps.py         #   get_current_user (JWT), require_admin (allowlist)
│   │   │   ├── auth.py         #   POST /api/auth/telegram
│   │   │   ├── users.py        #   GET /api/me, PATCH /api/me/settings
│   │   │   ├── decks.py spreads.py readings.py products.py payments.py
│   │   │   └── admin/          #   admin routers, all behind require_admin
│   │   ├── services/           # BUSINESS LOGIC lives here (TZ §29.1)
│   │   │   ├── telegram_auth.py card_draw.py reading.py
│   │   │   ├── prompt_engine.py safety.py llm/  # llm/base.py + llm/claude.py
│   │   │   ├── limit.py payment.py subscription.py analytics.py
│   │   ├── models/             # SQLAlchemy 2.x models (one file per aggregate)
│   │   ├── schemas/            # Pydantic request/response + LLM JSON schema
│   │   ├── core/               # config, security(JWT), redis, db session
│   │   └── seed/               # 6 decks, 7 spreads, 78 cards, prompt templates
│   ├── bot/                    # aiogram handlers (imported by app, not standalone)
│   │   ├── dispatcher.py       #   Dispatcher + router registration
│   │   ├── payments.py         #   pre_checkout_query, successful_payment, refund
│   │   └── start.py            #   /start deep-link → open mini app
│   └── alembic/
├── frontend/
│   └── src/
│       ├── pages/              # /, /onboarding, /reading/:id, /history, /tariffs, /profile, /settings
│       ├── features/           # reading-flow/, deck-picker/, paywall/, history/
│       ├── components/ui/      # DeckCard, TarotCardReveal, RitualLoadingScreen, PaywallSheet...
│       ├── admin/              # guarded /admin route tree
│       ├── stores/             # Zustand (reading draft, session)
│       ├── api/                # React Query hooks, axios client w/ JWT
│       └── theme/              # per-deck palette tokens (6 palettes, TZ §21.2)
└── docs/
```

### Structure Rationale

- **`api/` is thin, `services/` is thick:** TZ §29.2 mandates "never trust frontend"; card draw and limit checks must live server-side. Keeping routers free of logic makes the same services reusable by the bot dispatcher (payment grant) and admin.
- **`bot/` inside `backend/`:** single deployable, shared DB session + PaymentService; folder boundary preserved so it can be split into a worker post-MVP without rewriting handlers.
- **`services/llm/` as a package with `base.py`:** enforces the swappable-provider abstraction (locked decision). Reading logic depends on the interface, never on Claude specifics.
- **`seed/` first-class:** the core value ("same question, different deck") lives in seed data (6 deck `prompt_modifier`s + `prompt_templates`), so it is code-managed and migration-seeded, then refined via admin.
- **Frontend `features/` over type-folders:** the reading flow spans many components sharing the reading-draft store; co-locating reduces prop drilling and matches the vertical-slice build order.

---

## Architectural Patterns

### Pattern 1: Backend-Authoritative Reading Orchestration (single transaction, single LLM call)

**What:** `POST /api/readings` runs the entire high-value path synchronously in one request. No queue, no polling. The frontend's ritual animation plays *over data that is already complete*.

**When to use:** Generation is a single fast LLM call (locked decision). The "ritual" latency is a UX choice, not a technical wait — so the animation can mask the 2–6s LLM call and reveal pre-computed cards progressively.

**Trade-offs:** (+) No queue/worker infra, no status-polling endpoint, no card/summary desync. (−) Request held open for the LLM call → needs a sane timeout (e.g. 30–45s) and a graceful failure path; long-tail latency is user-visible if the animation finishes first (mitigate with a minimum ritual duration on the client).

**Order of operations (the load-bearing sequence):**
```
POST /api/readings (deck_slug, spread_slug, question, topic, reversals_enabled)
  └─ LimitService.check()         # Redis throttle + user_limits; reject early if 0
  └─ SafetyService.classify()     # cheap regex prefilter -> label
  │     ├─ crisis_sensitive  -> short-circuit: supportive refusal, NO draw, NO charge
  │     └─ *_sensitive       -> set safety_modifier for prompt
  └─ CardDrawService.draw()       # crypto-secure shuffle, N cards, 70/30 orientation
  └─ persist reading (status=pending) + reading_cards (no interpretation yet)
  └─ PromptEngine.assemble()      # system + deck_modifier + positions + card context + safety_modifier
  └─ LLMService.generate()        # ONE structured call -> JSON {cards:[...], summary:{...}}
  └─ validate against JSON schema # invalid -> status=failed, soft error, DO NOT decrement
  └─ persist interpretations + summary, status=completed, completed_at
  └─ LimitService.decrement()     # ONLY on success
  └─ AnalyticsService.log(reading_completed)
  └─ return full reading payload  # frontend animates reveal over ready data
```

**Example (service skeleton):**
```python
async def create_reading(user, req, session) -> Reading:
    await limit_service.ensure_can_read(user, session)        # raises -> 402 paywall
    label = safety.classify(req.question)
    if label == "crisis_sensitive":
        return safety.crisis_response()                       # no draw, no charge
    cards = card_draw.draw(deck, spread, req.reversals_enabled)
    reading = await repo.create_pending(user, req, cards, session)
    prompt = prompt_engine.assemble(req, deck, spread, cards, safety_modifier=label)
    raw = await llm.generate(prompt)                          # single structured call
    data = ReadingLLMResult.model_validate_json(raw)          # schema gate
    await repo.complete(reading, data, session)
    await limit_service.decrement(user, session)              # success-only
    return reading
```

### Pattern 2: Idempotent Stars Payment via In-Process Dispatcher

**What:** Telegram Stars flow split across REST (create) and the aiogram dispatcher (confirm/grant), with `payload` as the idempotency key (verified: `currency='XTR'`, empty `provider_token`, exactly one `LabeledPrice`; `refund_star_payment` since Bot API 7.4 / aiogram ≥3.7).

**When to use:** All paid entitlement grants. Telegram requires Stars for digital goods.

**Trade-offs:** (+) Entitlement granted only after Telegram-confirmed `successful_payment`; payload UNIQUE constraint makes retries safe. (−) Two entry points (REST + webhook) touching `payments`; both must go through PaymentService, never write directly.

**Flow & boundary:**
```
1. POST /api/payments/create-invoice {product_slug}
     PaymentService: build payload = {user_id, product_id, purchase_type, idempotency_key}
     persist payments(status=created, payload UNIQUE)
     return invoice_link (createInvoiceLink, XTR, provider_token="")
2. User pays in Telegram client.
3. Telegram -> POST /tg/webhook -> FastAPI -> dispatcher.feed_webhook_update()
     pre_checkout_query handler:
        PaymentService.validate(payload)  # product active? payload unused/created? limits?
        answer_pre_checkout_query(ok=True/False)   # MUST answer < 10s
4. successful_payment handler:
        PaymentService.grant(payload, telegram_payment_charge_id):
           - guard: skip if payload already 'paid' (idempotent)
           - store telegram_payment_charge_id, status=paid, paid_at
           - one_time_spreads -> user_limits.paid_spreads_balance += spreads_amount
           - subscription     -> upsert subscription (30-day window) + subscription_spreads_limit
        AnalyticsService.log(payment_success)
5. Refund: refund_star_payment(charge_id) -> status=refunded, adjust balance if appropriate
```

### Pattern 3: Versioned Prompt Assembly from DB (PromptEngine)

**What:** Prompt fragments live in `prompt_templates` (type ∈ system, single_card, final_summary, deck_modifier, safety, refusal), versioned by `version` + `is_active`. PromptEngine composes the final structured prompt at request time and stamps `prompt_version` onto the reading and `generation_logs`.

**When to use:** Every generation. Keeps the "different deck = different experience" core value editable via admin without code deploys, and makes regressions traceable.

**Trade-offs:** (+) Tunable in production, A/B-able, auditable per reading. (−) A bad active version breaks all generations → mitigate with admin "toggle active version" + generation-log error visibility (TZ §22.5).

**Assembly layering (for the single combined call):**
```
[system]  global mystical-fortuneteller rules + safety constraints (TZ §16)
  + [deck_modifier]  tone/imagery/forbidden words for chosen deck (TZ §19.x)
  + [safety modifier] only if classifier flagged *_sensitive
  + per-card context: position.prompt_instruction · card base meaning/keywords
                      · deck_card modifier · orientation
  + output contract: strict JSON schema (all cards' interpretations + summary)
```

---

## Data Flow

### Auth Flow (initData → JWT)

```
[Mini App boot]
   window.Telegram.WebApp.initData
      ↓ POST /api/auth/telegram {init_data}
[TelegramAuthService]
   1. parse query string, extract `hash`
   2. secret = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
   3. check = HMAC_SHA256(key=secret, msg=sorted "k=v\n" pairs sans hash)
   4. constant-time compare check == hash        # reject if mismatch
   5. assert now - auth_date <= 300s              # freshness, reject stale
   6. upsert users by telegram_id (profile fields)
   7. ensure user_limits row exists
      ↓
   issue JWT (sub=user.id, exp) -> { access_token, user, limits, settings }
[Mini App] stores JWT; React Query attaches `Authorization: Bearer` to every call
```
Telegram identity and JWT coexist: `initData` is the **identity proof** (per session boot), JWT is the **session bearer** for subsequent API calls. Admin = same JWT **plus** `users.telegram_id ∈ ADMIN_TELEGRAM_IDS` checked server-side in `require_admin` (frontend route guard is cosmetic).

### Reading Flow (request direction)

```
[Tap "Начать расклад"]
   POST /api/readings ──► LimitService ──► SafetyService ──► CardDrawService
        │                     │ (Redis+DB)    │ (classify)      │ (crypto draw)
        │                     ▼               ▼                 ▼
        │                  reject 402     crisis short-circuit  reading=pending
        │                                                       │
        └──────────────► PromptEngine ──► LLMService ──► JSON schema validate
                              │ (DB tpl)     │ (1 call)        │
                              ▼              ▼                 ▼
                         prompt_version  generation_logs   persist + decrement
   ◄────────────────────────────────────────────────── full reading payload
[Mini App] RitualLoadingScreen (min duration) → staggered TarotCardReveal over ready data
```

### Payment Flow (two directions converge on PaymentService)

```
REST  : create-invoice ─► PaymentService.create ─► payments(created) ─► invoice_link ─► client
WEBHOOK: Telegram ─► /tg/webhook ─► aiogram dispatcher
            ├─ pre_checkout_query ─► PaymentService.validate ─► answer(ok)   (<10s)
            └─ successful_payment ─► PaymentService.grant ─► user_limits/subscriptions (idempotent by payload)
```

### State Management (frontend)

```
Server state (readings, decks, spreads, me, products)  ── React Query (cache, SWR)
Client/draft state (question, topic, deck, spread, ritual step) ── Zustand store
URL state (active reading id, history filters)         ── route params
   Components subscribe; the reading-draft store is consumed by the whole reading flow.
```

### Key Data Flows (summary)

1. **Auth:** initData (proof) → HMAC validate + freshness → upsert user → JWT (bearer for all later calls).
2. **Reading:** one synchronous request does limit→safety→draw→pending→single-LLM→validate→persist→decrement; client animates over completed data.
3. **Payment:** REST creates invoice; webhook (in-process aiogram) confirms + grants, idempotent on `payload`, entitlement only after `successful_payment`.
4. **Analytics:** every meaningful step appends to `app_events` fire-and-forget; never on the critical path.

---

## Data Model Boundaries

The model deliberately splits **universal card meaning** from **deck-specific style** (TZ §5.3, §13) — this is what enables "same card, different deck experience" and keeps IP clean.

```
cards (universal)                deck_cards (style layer)         decks
  meaning_upright/reversed   ◄──── deck_specific_*_modifier ────►  prompt_modifier
  keywords, advice                 image_url, back_image_url        tone, atmosphere
  arcana_type, suit                visual_prompt                    visual_style(JSONB)
        ▲                               ▲                                ▲
        │ card_id              deck_card_id │                   deck_id  │
        └───────────── reading_cards ───────┴──── readings ──────────────┘
                       orientation,                user_id, question,
                       interpretation,             topic, status, summary_*,
                       mystical_accent             prompt_version, model_name

spread_types ──1:N── spread_positions (position_index, prompt_instruction)
     │
     └── deck_spread_compatibility (deck_id × spread_type_id, is_recommended)  → /spreads/recommend

prompt_templates (slug, type, template_text, version, is_active)   → PromptEngine
user_limits (free_weekly + week_start, paid_spreads_balance, subscription_*)  → LimitService
products → payments (payload UNIQUE, telegram_payment_charge_id) → subscriptions
app_events (analytics)        generation_logs (per-reading: tokens, latency, status, error)
```

**Boundary rules:**
- `cards` never holds imagery or deck tone; `deck_cards` never holds the base meaning. A reading references both (`card_id` for meaning, `deck_card_id` for image/style).
- `readings` is the durable result; `reading_cards` are immutable rows written once on completion. Re-opening history reads these, never re-generates.
- `generation_logs` ≠ `app_events`: the former is technical (tokens/latency/errors for the admin generation-logs view), the latter is product analytics.

---

## Build Order — Vertical-MVP Slices

PROJECT_MODE=mvp → each phase ships an **end-to-end, user-visible** capability (a vertical slice through frontend + API + service + DB), not a horizontal layer. This maps the TZ §23 stage plan onto vertical slices and respects dependencies. **No background-queue phase exists** — generation is synchronous from day one.

| # | Slice (user-visible capability) | Spans | Depends on | Notes / risk |
|---|--------------------------------|-------|-----------|--------------|
| 0 | **Walking skeleton** — repo boots: mini app opens, `/healthz` answers, DB+Redis up via Docker Compose, Alembic ready | infra, FE shell, BE health | — | Not user-facing value but the platform every slice rides on (TZ §23.1) |
| 1 | **"It knows who I am"** — open mini app → authenticated, profile via `/api/me` | FE TG SDK → `/api/auth/telegram` → JWT → `/api/me` | 0 | initData HMAC + freshness; JWT issuance. Establishes `require_admin` allowlist seam early |
| 2 | **"I can browse decks & spreads"** — see 6 decks, 7 spreads, get a recommendation | seed → `/decks` `/spreads` `/spreads/recommend` → FE carousels | 1 | Seed data is the core-value substrate; per-deck theming tokens land here |
| 3 | **"I can run the whole ritual (mock)"** — full flow to a mock result | onboarding, home, question/topic/deck/spread, ritual, reveal screens | 2 | Locks the UX + animation contract *before* wiring the LLM, so generation is "fill in real data" |
| 4 | **"I get a real, personal reading"** ⭐ core value — one structured LLM call, per-deck voice | CardDraw + Reading + PromptEngine + Safety + LLMService + JSON schema; real `POST /api/readings` | 3 | The high-value path. Single sync call, no queue. Safety classifier (incl. crisis short-circuit) ships *with* generation, not later |
| 5 | **"I can revisit past readings"** — history list + detail + soft delete | `/readings` (list/detail/delete) + history UI + personalization toggle | 4 | Reads immutable `reading_cards`; never regenerates |
| 6 | **"I'm limited to 3 free/week"** — limit enforcement + paywall surface | LimitService (weekly reset, Redis throttle) + paywall UI | 4 | Gate must exist before payments are meaningful |
| 7 | **"I can buy more / subscribe"** — Stars purchase grants access | products + PaymentService + create-invoice + in-process aiogram webhook (pre_checkout/success/refund) + tariffs UI | 6 | Idempotent by payload; entitlement only on `successful_payment`. First slice needing the bot module |
| 8 | **"Operators can run it without code"** — admin CRUD + dashboards | admin routers (behind allowlist) + admin UI for decks/cards/prompts/products + generation-logs + toggles | 4,7 | Prompt-version toggle + deck/spread disable are operational safety valves |
| 9 | **Polish & deploy** — error/empty/loading states, mobile pass, Sentry, metrics, timeweb.cloud | cross-cutting | all | Test Stars in test mode; verify Telegram theme |

**Ordering rationale & dependencies:**
- **Auth (1) gates everything** — no authenticated identity, no per-user reads/limits/payments.
- **Seed/read APIs (2) before UX (3)** — the home flow needs real decks/spreads to render; recommendation needs `deck_spread_compatibility`.
- **Mock UX (3) before real generation (4)** — this is the deliberate vertical-slice move: ship the *ritual* end-to-end first, then swap mock data for the LLM call. De-risks the highest-uncertainty UX (animation timing vs. latency) independently of prompt tuning.
- **Generation (4) is the keystone** — history (5), limits (6), payments (7), and admin (8) all assume a working `readings` write path. Safety is **inside** slice 4 (cheap, mandatory, crisis handling is liability-critical), not a trailing concern.
- **Limits (6) before payments (7)** — a paywall is meaningless until free access is bounded.
- **Admin (8) after payments (7)** — admin reads payments/generation-logs, so those tables must exist; admin's prompt/deck toggles are the production safety mechanism for the generation path.

**Phases likely to need deeper research later (flag for roadmap):**
- Slice 4 — prompt engineering + JSON schema design for a *single* combined call (all cards + summary in one response), plus the cheap safety classifier approach (regex prefilter vs. folding classification into the main call). Highest product+technical risk.
- Slice 7 — exact aiogram Stars API surface for the in-process webhook + refund semantics + subscription-window modeling (native recurring Stars vs. manual 30-day window).
- Slices 1 — Telegram-validated CSP / `connect-src` for the WebView and JWT-in-WebView storage.

---

## Scaling Considerations

| Scale | Architecture adjustments |
|-------|--------------------------|
| 0–1k users | Single FastAPI process (REST + dispatcher), managed Postgres + Redis. No changes needed. This is the MVP target. |
| 1k–100k users | Run **N stateless FastAPI replicas behind one HTTPS endpoint**; Telegram webhook still hits one URL (load-balanced). Add Postgres connection pooling (PgBouncer). Cache `cards`/`deck_cards`/`prompt_templates` in Redis (already a slot). Watch LLM provider rate limits. |
| 100k+ users | Split the aiogram dispatcher into its own deployment (it's already an isolated module); introduce a read replica for history/analytics; move `app_events` to an append-optimized store. Only now consider an async generation queue **if** richer multi-call generation is added post-MVP. |

### Scaling Priorities

1. **First bottleneck — the synchronous LLM call holds a request open.** At low scale it's fine (one fast call). Under load it ties up workers and exposes provider latency/limits. Fix order: per-deck response-length caps + token logging → provider concurrency tuning → only then revisit the "no queue" decision. The current architecture intentionally trades worker-occupancy for zero queue infra.
2. **Second bottleneck — `user_limits` / weekly-reset write contention + abuse.** Mitigate with the Redis throttle in front of `LimitService` (TZ §25.6) before it reaches Postgres; reset weekly limits lazily on read (`week_start` comparison) rather than via a scheduled job (no scheduler in MVP).
3. **Third — analytics inserts.** Keep `app_events` fire-and-forget and off the reading critical path; batch/replica it before it competes with reads.

---

## Anti-Patterns

### Anti-Pattern 1: Drawing cards or checking limits on the frontend
**What people do:** Shuffle/select cards client-side for snappy animation, or gate the paywall only in the UI.
**Why it's wrong:** Trivially spoofable — users forge "free" readings, desync history, break honest randomness (TZ §12.4, §29.2).
**Do this instead:** Backend-only `CardDrawService` (crypto-secure) and `LimitService`; the frontend animates over a server-returned result.

### Anti-Pattern 2: Adding a background queue "just in case" generation is slow
**What people do:** Reach for Celery/RQ/Arq + status polling because "AI generation = async job."
**Why it's wrong:** Explicitly excluded (locked decision). Generation is one fast LLM call; a queue adds a worker process, a status endpoint, polling, and card/summary desync risk — pure overhead for MVP.
**Do this instead:** Synchronous `POST /api/readings` with a timeout; the ritual animation (with a minimum duration) masks latency. Revisit only if post-MVP multi-call generation appears.

### Anti-Pattern 3: Per-card LLM calls (or summary as a separate call)
**What people do:** One LLM call per card position + one for the summary (5 calls for a 4-card spread).
**Why it's wrong:** ×4–5 cost/latency, and independent calls drift in tone and contradict each other across cards (locked decision #1).
**Do this instead:** One structured call returning all card interpretations + summary in a single schema-validated JSON. Keep per-card templates only as a fallback.

### Anti-Pattern 4: Granting entitlement on invoice creation / trusting the client's "paid" signal
**What people do:** Increment `paid_spreads_balance` when the invoice is created or when the WebView reports success.
**Why it's wrong:** Payment can fail/cancel after the invoice; the client can lie. Leads to free paid-readings and reconciliation pain.
**Do this instead:** Grant **only** in the `successful_payment` handler, idempotent on `payload` (UNIQUE), storing `telegram_payment_charge_id` (TZ §11.4, §29.2).

### Anti-Pattern 5: Business logic in routers / bot handlers
**What people do:** Put limit checks, card draw, or payment-grant logic directly in FastAPI route functions or aiogram handlers.
**Why it's wrong:** The same logic is needed from multiple entry points (REST + webhook + admin); duplicating it causes drift, especially for payment grants.
**Do this instead:** Thin routers/handlers that delegate to the `services/` layer; both the REST API and the in-process dispatcher call the same `PaymentService`/`LimitService`.

### Anti-Pattern 6: Treating the safety classifier as optional polish
**What people do:** Defer safety to "after generation works," or skip crisis handling.
**Why it's wrong:** Crisis topics (self-harm, violence) are real liability; surfacing a mystical "prediction" there is harmful (locked decision #3).
**Do this instead:** Ship Safety **inside** the generation slice — cheap regex prefilter + classification; `crisis_sensitive` short-circuits *before* draw/charge into a supportive response.

---

## Integration Points

### External Services

| Service | Integration pattern | Notes / gotchas |
|---------|---------------------|-----------------|
| Telegram WebApp (Mini App) | `window.Telegram.WebApp.initData` → backend HMAC validation | `auth_date` freshness (~5 min); validate server-side every session; WebView CSP must allow your API origin |
| Telegram Bot API (payments) | aiogram dispatcher fed by FastAPI webhook route | Stars: `currency='XTR'`, empty `provider_token`, exactly one `LabeledPrice`; `pre_checkout_query` MUST be answered <10s; protect route with `X-Telegram-Bot-Api-Secret-Token`; `refund_star_payment` requires Bot API ≥7.4 / aiogram ≥3.7 |
| LLM provider (Claude default) | `LLMService` interface, synchronous HTTP in-request | One structured JSON call; enforce response schema; set a request timeout + soft-fail; log tokens/latency to `generation_logs`; swappable so model can change without touching reading logic |
| timeweb.cloud | App Platform deploy from Git; managed Postgres/Redis/S3 + VPS via panel | HTTPS mandatory; single backend container hosts REST + dispatcher; decide deploy details at the deploy slice |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Mini App ↔ Backend | HTTPS REST, `Authorization: Bearer <JWT>` | React Query owns server state; never duplicate it into Zustand |
| Telegram ↔ Backend (payments) | Webhook POST → `dispatcher.feed_webhook_update()` | In-process; one route, secret-token guarded |
| Routers/handlers ↔ Services | Direct in-process calls | Routers thin; all logic in `services/`; same services shared by REST, webhook, admin |
| ReadingService ↔ LLMService | Interface (`llm/base.py`) | Provider-agnostic; Claude is one implementation |
| Services ↔ Postgres | SQLAlchemy 2.x async, per-request session | One transaction boundary per reading; reading_cards written once |
| Services ↔ Redis | Cache + throttle only | **Not** a queue/broker; rate-limit counters, card-meaning cache, optional per-user lock |
| Admin API ↔ everything | Same services, behind `require_admin` | Allowlist `telegram_id ∈ ADMIN_TELEGRAM_IDS` enforced server-side |

---

## Sources

- TZ (source of truth): `.planning/REFERENCE-TZ.md` §12 (architecture, flow), §13 (15-table schema), §14 (API endpoints), §15–§19 (prompt system), §20 (safety), §23 (stage plan), §29 (backend services) — HIGH
- PROJECT.md locked decisions (single LLM call, no queue, mandatory safety classifier, Zustand, admin allowlist) — HIGH
- Telegram Mini Apps — Init Data validation (HMAC-SHA256 `WebAppData`, `auth_date` freshness): https://docs.telegram-mini-apps.com/platform/init-data , https://docs.telegram-mini-apps.com/packages/tma-js-init-data-node/validating — HIGH
- aiogram 3.x Stars invoice example (`currency='XTR'`, empty `provider_token`, single `LabeledPrice`, `pre_checkout_query`): https://github.com/aiogram/aiogram/blob/dev-3.x/examples/stars_invoice.py — HIGH
- aiogram 3.x `create_invoice_link` / `send_invoice` (XTR notes) + `refund_star_payment` (Bot API 7.4 / aiogram 3.7): https://docs.aiogram.dev/en/latest/api/methods/create_invoice_link.html — HIGH
- aiogram 3.x webhook + external-framework integration (`feed_webhook_update`, single-process viability): https://docs.aiogram.dev/en/latest/dispatcher/webhook.html — HIGH

---
*Architecture research for: Telegram Mini App AI tarot (Зеркало Судьбы)*
*Researched: 2026-06-09*
