# Stack Research

**Domain:** Telegram Mini App — AI-раскладов таро (generative LLM interpretation, Telegram Stars monetization)
**Researched:** 2026-06-09
**Confidence:** HIGH (versions verified against official docs / npm / PyPI / Telegram Bot API as of June 2026; LLM API verified against platform.claude.com)

> This document **pins concrete versions and idioms** for the stack locked in `PROJECT.md` (TZ §12.1 + my edits #1, #2, #5). It is prescriptive: WHY each choice, what NOT to use, and the exact crypto / payments algorithms that must be correct.
>
> **Two corrections to the original spec surfaced by research:**
> 1. **"Framer Motion" no longer exists under that name** — the library was renamed to **`motion`** (import from `motion/react`). Install `motion`, not `framer-motion`. (See [What NOT to Use].)
> 2. **Telegram Stars *native recurring* subscriptions exist** (`subscription_period`) — my edit #7 assumed "manual renewal if API unavailable." The API **is** available. Recommendation below: use native recurring with a 30-day `subscription_period`, but still keep the entitlement-window model server-side as source of truth.

---

## Recommended Stack

### Core Technologies — Frontend (`/frontend`, `/admin`)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **React** | `19.2.x` | UI runtime | Current stable. Concurrent rendering, Actions, `use()`. Mini App is a small SPA — React 19 is the boring, correct default. |
| **TypeScript** | `5.7+` | Type safety | Mandatory per coding rules; strict mode. Telegram WebApp types + API contracts benefit hugely. |
| **Vite** | `7.1.x` (recommend) — `8.0.x` exists | Build / dev server | **Recommend Vite 7**, not 8. Vite 8 (Dec 2025) replaces esbuild with **Rolldown** by default — newer, occasional plugin-compat rough edges. Vite 7 is mature, every Tailwind/React plugin works. Upgrade to 8 post-MVP. |
| **Tailwind CSS** | `4.0.x` | Styling | v4 = CSS-first config (`@theme` in CSS, no `tailwind.config.js` required), OKLCH colors, native cascade layers. Per-deck theming via CSS custom properties (`--color-accent`, etc.) maps perfectly to the 6-deck palette requirement (TZ §10.1). Aligns with web/coding-style rules (design tokens as CSS vars). |
| **motion** (ex-`framer-motion`) | `12.x` | Animation | **Package renamed `framer-motion` → `motion`.** Import `{ motion }` from `motion/react`. Drives flip animations, shuffle ritual, particle/glow micro-animations (TZ §10.2). Use compositor-friendly props only (transform/opacity) per web/performance rules. |
| **Zustand** | `5.0.x` | Client state | Edit #5: lighter than Redux for a Mini App. Tiny (~1KB), no boilerplate, no provider hell. Holds ephemeral UI/ritual state (selected deck/topic/spread, reveal step, settings toggles). |
| **TanStack Query** (`@tanstack/react-query`) | `5.101.x` | Server state | Caches `/api/decks`, `/api/spreads`, `/api/me`, history. Handles the `POST /api/readings` mutation with loading/error states for the "колода замолчала" retry UX. **Do not** duplicate server data into Zustand (web/patterns rule). |

### Core Technologies — Backend (`/backend`)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | `3.12.x` (or 3.13) | Runtime | TZ §12.1 floor is 3.12. 3.12 is the safe, fully-supported target for all libs below. |
| **FastAPI** | `0.136.x` | HTTP API | Async-native, Pydantic v2 integration, auto OpenAPI 3.1. The whole reading flow (validate initData → check limits → pick cards → one LLM call → persist) is async I/O — FastAPI is ideal. |
| **Uvicorn** | `0.34+` (`uvicorn[standard]`) | ASGI server | Standard FastAPI server. Behind it in prod, run via Gunicorn worker or container `CMD uvicorn` with `--workers`. |
| **SQLAlchemy** | `2.0.x` (async) | ORM | 2.0 async engine + `async_sessionmaker`. Maps the 16-table schema (TZ §13). Use `AsyncSession`, `Mapped[...]` typed models, `select()` 2.0 style — **not** legacy `Query`. |
| **asyncpg** | `0.30.x` | Postgres driver | Fastest async Postgres driver. DSN: `postgresql+asyncpg://...`. |
| **Alembic** | `1.14.x` | Migrations | Schema migrations for all 16 tables. Configure with async engine template (`alembic init -t async`). |
| **Pydantic** | `2.10.x` | Validation / schemas | v2 (Rust core). Request/response models, LLM JSON output validation. Use `model_config = ConfigDict(from_attributes=True)` for ORM→schema. |
| **pydantic-settings** | `2.7.x` | Config | Settings via `BaseSettings` from env vars (BOT_TOKEN, DATABASE_URL, REDIS_URL, ANTHROPIC_API_KEY, ADMIN_TELEGRAM_IDS, JWT_SECRET). **Never hardcode secrets** (security rule). Validate presence at startup. |
| **PostgreSQL** | `16.x` (or 17) | Database | Primary store. JSONB columns (`visual_style`, `raw_update`, `event_properties`), `TEXT[]` arrays (`recommended_topics`, `keywords_*`), UUID PKs — all native PG. |
| **Redis** | `7.x` | Rate-limit / cache / throttle | **Edit #2: Redis only — NO Celery/RQ/Arq.** Weekly free-limit counters, throttle, cached base card meanings + deck/spread catalog. |
| **redis-py** | `5.2.x` (`redis[hiredis]`) | Redis client | Async client (`redis.asyncio`). `hiredis` extra for faster parsing. |
| **PyJWT** | `2.10.x` | Session tokens | Issue JWT after initData validation (TZ §14.1 returns `access_token`). Short-lived, HS256, secret from env. |

### Core Technologies — Bot (`/bot`)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **aiogram** | `3.27.x` | Telegram Bot framework | Modern async, full Bot API coverage incl. **Telegram Stars** (`create_invoice_link`, `refund_star_payment`, `edit_user_star_subscription`, `get_star_transactions`). Router-based handlers for `pre_checkout_query` / `successful_payment`. **Webhook mode** (TZ §12.1). |

### LLM Layer (`InterpretationService` / `LLMService`)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **anthropic** (Python SDK) | `0.69.x+` | Claude API client | Default provider behind swappable `LLMService` abstraction (TZ §12.1, edit #1). Supports **Structured Outputs** (`client.messages.parse(...)` + Pydantic schema). |
| **Claude Haiku 4.5** | `claude-haiku-4-5` | **Default generation model** | **$1.00 / $5.00 per MTok.** Fast + cheap. One reading = ~1.5–3K input tokens (prompts + card data) + ~1–2K output. At Haiku pricing a reading costs ≈ $0.01. Quality is more than enough for atmospheric tarot copy. **This is the MVP default.** |
| **Claude Sonnet 4.6** | `claude-sonnet-4-6` | Premium / quality fallback | **$3.00 / $15.00 per MTok.** Use for "deep" decks (Тени/Лесной) or a paid "premium tone" tier post-MVP, or as automatic retry if Haiku output fails validation. 3× the cost — not the default. |

**Model IDs verified June 2026** (current lineup is ahead of older training data — Opus is at 4.8, Sonnet 4.6, Haiku 4.5). Use the **aliases without dates** (`claude-haiku-4-5`) so minor model bumps don't require code changes; pin a dated snapshot only if you need reproducibility for `prompt_version` logging.

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **httpx** | `0.28.x` | Async HTTP | If `LLMService` needs a non-Anthropic provider (OpenAI-compatible) without its SDK. Also general outbound calls. |
| **structlog** *or* stdlib `logging` | `24.x` | Structured logs | `generation_logs` context (model, latency_ms, tokens), payment audit trail. JSON logs for timeweb. |
| **tenacity** | `9.x` | Retries | Wrap the single LLM call with bounded retry (1–2 attempts) + timeout. Replaces a queue for transient failures (edit #2). |
| **@telegram-apps/sdk-react** | `3.x` | Telegram WebApp wrapper (frontend) | **Optional.** Typed wrapper over `window.Telegram.WebApp`: `initDataRaw`, theme params, MainButton/BackButton, HapticFeedback, viewport. See decision note below — raw `window.Telegram.WebApp` is also fully viable. |
| **slowapi** | `0.1.9` | HTTP rate-limit decorator | Optional convenience for per-IP/endpoint limits on top of Redis. The *business* weekly limit (3/week) is custom logic in `user_limits`, not slowapi. |
| **pytest** + **pytest-asyncio** + **httpx ASGITransport** | latest | Testing | 80% coverage rule. Unit (initData validation, card-pick, limit logic), integration (API + test DB), payment-flow tests. |
| **ruff** | `0.9.x` | Lint + format | Single fast tool for lint+format. Replaces black+isort+flake8. |
| **Vitest** + **Playwright** | latest | Frontend tests | Vitest for hooks/utils; Playwright for visual regression at 360/390/430px + flip/reveal flow (web/testing rules). |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Docker + Docker Compose** | Local dev + deploy | Compose: `postgres:16`, `redis:7`, `backend`, `bot`, `frontend` (nginx static). Mirrors timeweb App Platform. |
| **uv** *or* **Poetry** | Python deps/venv | `uv` is dramatically faster; either is fine. Pin versions in lockfile. |
| **pnpm** | JS package manager | Faster, disk-efficient; matches web rules (hooks reference pnpm). |
| **ngrok / cloudflared** | Local Telegram testing | Telegram needs HTTPS for Mini App + bot webhook; tunnel during dev. |

---

## Installation

### Frontend (`/frontend`, `/admin` shares the app)

```bash
pnpm create vite@7 frontend -- --template react-ts

# Core runtime
pnpm add react@19 react-dom@19
pnpm add @tanstack/react-query@5 zustand@5 motion

# Telegram (optional typed wrapper — or use window.Telegram.WebApp directly)
pnpm add @telegram-apps/sdk-react@3

# Styling (Tailwind v4 — CSS-first, via Vite plugin)
pnpm add -D tailwindcss@4 @tailwindcss/vite

# Dev / test
pnpm add -D typescript vitest @playwright/test eslint prettier
```

> **Tailwind v4 note:** no `tailwind.config.js` needed. Add `@import "tailwindcss";` in CSS and `@tailwindcss/vite` to `vite.config.ts`. Define per-deck tokens in `@theme { --color-accent: ...; }`.

### Backend (`/backend`)

```bash
# Core
uv pip install "fastapi==0.136.*" "uvicorn[standard]" \
  "sqlalchemy[asyncio]==2.0.*" "asyncpg==0.30.*" "alembic==1.14.*" \
  "pydantic==2.10.*" "pydantic-settings==2.7.*" \
  "redis[hiredis]==5.2.*" "pyjwt==2.10.*"

# LLM + resilience
uv pip install "anthropic>=0.69" "tenacity==9.*" "httpx==0.28.*"

# Dev / test
uv pip install pytest pytest-asyncio "ruff==0.9.*"
```

### Bot (`/bot`)

```bash
uv pip install "aiogram==3.27.*"
```

---

## Telegram initData Validation — EXACT Algorithm (must be correct)

> **Confidence: HIGH** — verified against `core.telegram.org/bots/webapps` (June 2026).
> **DO NOT roll your own crypto carelessly, but DO implement this 5-line HMAC yourself** — it is trivial and well-specified. A heavy third-party lib is *not* required (see decision note). If you want a vetted helper, `init-data-py` (PyPI) exists, but the hand-rolled version below is the standard and auditable.

**Algorithm (bot-token / first-party method):**

1. Parse `init_data` as a query string into key→value pairs.
2. Extract and remove the `hash` field. **Also remove `signature`** if present (that belongs to the Ed25519 third-party method, not this one).
3. Build `data_check_string`: remaining pairs **sorted alphabetically by key**, each as `key=value`, joined by `\n` (newline `0x0A`).
4. `secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)` — **note the order: the constant string `"WebAppData"` is the HMAC *key*, the bot token is the *message*.**
5. `computed_hash = hex( HMAC_SHA256(key=secret_key, msg=data_check_string) )`
6. Constant-time compare `computed_hash` with the received `hash` (`hmac.compare_digest`).
7. **Freshness:** reject if `now - auth_date > MAX_AGE`. Recommend **`MAX_AGE = 86400` (24h)**, or tighter (e.g. 1h) for the auth endpoint. Always check it — replay protection.

**Reference implementation (hand-rolled, stdlib only):**

```python
import hmac, hashlib, time
from urllib.parse import parse_qsl

def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    pairs = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = pairs.pop("hash", None)
    pairs.pop("signature", None)  # not part of bot-token method
    if not received_hash:
        raise ValueError("missing hash")

    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        raise ValueError("bad hash")
    if time.time() - int(pairs.get("auth_date", "0")) > max_age:
        raise ValueError("expired")
    return pairs  # contains 'user' (JSON string), 'auth_date', etc.
```

> The `user` field is a **URL-decoded JSON string** — `json.loads(pairs["user"])` to get `telegram_id`, `username`, `first_name`, `photo_url`, `language_code` for upserting `users` (TZ §13.1).

---

## Telegram Stars Payments — EXACT Flow (must be correct)

> **Confidence: HIGH** — verified against aiogram 3.27 docs + `core.telegram.org/api/subscriptions` + Bot API (June 2026).

**Currency = `XTR`. Provider token = empty string `""`. `prices` = exactly ONE `LabeledPrice` for Stars.**

### One-time purchase (packs: 1 / 3 / 10 readings)

1. **Create invoice** (`POST /api/payments/create-invoice` → aiogram `create_invoice_link`):
   ```python
   link = await bot.create_invoice_link(
       title="3 расклада",
       description="...",
       payload=payload,                 # JSON: {user_id, product_id, purchase_type, idempotency_key}
       currency="XTR",
       prices=[LabeledPrice(label="XTR", amount=stars_price)],  # exactly one item
       provider_token="",               # empty for Stars
   )
   ```
   Persist `payments` row `status='created'` with the **UNIQUE `payload`** (idempotency anchor, TZ §13.13).
2. **`pre_checkout_query`** handler → validate (product exists, active, payload unused, limits) → `await query.answer(ok=True)` **within 10s** (Telegram hard limit). On fail: `ok=False, error_message="..."`.
3. **`successful_payment`** (Message update) → idempotent on `payload`/`telegram_payment_charge_id`: save `telegram_payment_charge_id`, set `status='paid'`, increment `user_limits.paid_spreads_balance` (TZ §11.5). **Access granted ONLY here** (constraint in PROJECT.md).
4. **Refund:** `await bot.refund_star_payment(user_id, telegram_payment_charge_id)` → set `status='refunded'`, decrement balance if appropriate.
5. **Reconciliation:** `get_star_transactions` for audit / admin.

### Subscription ("Лунный доступ", 30-day) — NATIVE RECURRING IS AVAILABLE

> This **supersedes the uncertainty in edit #7**. Telegram Stars supports native recurring subscriptions.

- Add **`subscription_period=2592000`** (exactly 30 days — Telegram currently **only** allows this value) to `create_invoice_link`. Currency must be `XTR`.
- Telegram **auto-renews** every period, deducting Stars and firing a new `successful_payment` with **`is_recurring=True`** (and `is_first_recurring=True` on the first one). `subscription_expiration_date` is included.
- **Cancel / re-enable** from the bot: `bot.edit_user_star_subscription(user_id, telegram_payment_charge_id, is_canceled=True|False)`.
- **Source of truth = your DB, not Telegram's subscription state.** On each `successful_payment` (recurring or not) extend `subscriptions.current_period_end` / `user_entitlements` by 30 days. This keeps edit #7's "entitlement window" model while using native billing.

**`successful_payment` fields that matter:** `telegram_payment_charge_id`, `invoice_payload`, `total_amount`, `is_recurring`, `is_first_recurring`, `subscription_expiration_date`. Branch one-time vs subscription on `is_recurring`.

---

## LLM: Single Structured Call for the Whole Reading (edit #1)

> **Confidence: HIGH** — Structured Outputs verified GA on Claude Haiku 4.5 / Sonnet 4.6 (platform.claude.com, June 2026).

**One call returns every card interpretation + the summary as ONE validated JSON object** (×4–5 cheaper/faster than per-card calls; less desync — edit #1). Per-card templates (TZ §17) remain a **fallback only**.

**Enforce strict JSON via native Structured Outputs** (preferred) — compiles the schema into a grammar, constrains decoding, guarantees valid JSON (no regex-scraping, no retry-on-malformed):

```python
from pydantic import BaseModel
import anthropic

class CardInterp(BaseModel):
    position_index: int
    short_meaning: str        # ≤140 chars (TZ §17)
    interpretation: str       # 2–4 short paragraphs
    mystical_accent: str
    soft_advice: str

class ReadingResult(BaseModel):
    cards: list[CardInterp]
    summary_short: str
    connection: str
    main_factor: str
    attention_point: str
    advice: str
    closing_phrase: str

client = anthropic.Anthropic()
resp = client.messages.parse(            # SDK helper for Structured Outputs
    model="claude-haiku-4-5",
    max_tokens=2048,
    system=system_prompt,                # TZ §16 + deck modifier §19 + safety §20
    messages=[{"role": "user", "content": reading_context}],  # all cards/positions §18
    output_format=ReadingResult,         # schema → grammar-constrained
)
result = resp.parsed_output              # already a validated ReadingResult
```

**API notes (current):** Structured Outputs is **GA** — the old beta header `anthropic-beta: structured-outputs-2025-11-13` is no longer required (still tolerated). The raw param moved from `output_format` → **`output_config.format`**; the **SDK `messages.parse(..., output_format=Model)` helper hides this** and is what you should use.

**Fallback for forced-JSON without Structured Outputs** (e.g. swapping to a provider/model that lacks it): use **strict tool use** — define one tool with `strict: True` + `input_schema`, force `tool_choice={"type":"tool","name":...}`, read `tool_use.input`. Both are documented; prefer `messages.parse`.

**Safety classifier (edit #3):** runs as part of the SAME call — add a `safety_level: Literal["normal","sensitive","crisis"]` field to the schema, plus a cheap regex pre-filter before the call for hard crisis keywords. On `crisis`, swap to the supportive `refusal`/`safety` template (TZ §13.10 types, §20) instead of a mystical reading. No second model call needed.

---

## Redis Usage (edit #2 — no queue)

| Use | Pattern | Notes |
|-----|---------|-------|
| Weekly free limit (3/week) | Source of truth in Postgres `user_limits` (`free_used_this_week`, `week_start`); Redis as fast counter/cache | Reset weekly (compare `week_start`). Keep PG authoritative for correctness/audit. |
| Throttle / abuse | `INCR` + `EXPIRE` per-user short-window key | Prevent rapid-fire reading creation. |
| Cache base card meanings | `GET/SET` JSON, TTL or invalidate-on-admin-edit | Cards/deck_cards rarely change; avoids re-reading 78×6 rows per reading. |
| Cache deck/spread catalog | Cache `/api/decks`, `/api/spreads` responses | Admin toggle busts cache. |
| Idempotency keys (optional) | `SETNX payment:{payload}` as a fast guard | DB UNIQUE on `payload` remains the real guarantee. |

**No Celery/RQ/Arq.** Generation = one synchronous LLM call inside the request with a timeout + `tenacity` retry. Add a queue only if a future feature needs true background work.

---

## Deploy: timeweb.cloud (App Platform, Docker)

| Service | Container | Notes |
|---------|-----------|-------|
| **backend** | `python:3.12-slim` → `uvicorn app.main:app` | FastAPI API. HTTPS required (TZ §12.1). Reads env (DATABASE_URL, REDIS_URL, BOT_TOKEN, ANTHROPIC_API_KEY, JWT_SECRET, ADMIN_TELEGRAM_IDS). |
| **bot** | `python:3.12-slim` → aiogram **webhook** | Separate process/container. Telegram → `/api/payments/webhook` (or bot's own webhook path) over HTTPS. Handles `pre_checkout_query` + `successful_payment`. |
| **frontend** | build then `nginx:alpine` static | `pnpm build` → serve `dist/`. Admin = protected `/admin` routes in same SPA (edit #6, allowlist `ADMIN_TELEGRAM_IDS` + server check). |
| **postgres** | managed PG (timeweb) or `postgres:16` container | Prefer managed for backups. |
| **redis** | managed Redis or `redis:7` container | Either works for MVP. |

**Constraint (PROJECT.md):** timeweb MCP only does App Platform deploy-from-Git; managed PG/Redis/S3 and VPS are provisioned manually in panel. **Docker Compose is the local-dev source of truth**; App Platform consumes per-service Dockerfiles. Keep one `Dockerfile` per service + a root `docker-compose.yml` (postgres + redis + backend + bot + frontend) for parity.

```yaml
# docker-compose.yml (local dev shape)
services:
  postgres: { image: postgres:16, environment: [POSTGRES_*], ports: ["5432:5432"] }
  redis:    { image: redis:7, ports: ["6379:6379"] }
  backend:  { build: ./backend, env_file: .env, depends_on: [postgres, redis], ports: ["8000:8000"] }
  bot:      { build: ./bot, env_file: .env, depends_on: [backend] }
  frontend: { build: ./frontend, ports: ["5173:5173"] }
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Zustand 5 | Redux Toolkit | Never for this app (edit #5). RTK only if a large team needs strict middleware/devtools conventions — overkill for a Mini App. |
| `motion` (ex-framer-motion) | CSS-only animations / GSAP | CSS for trivial transitions (cheaper). GSAP only if you need a complex scroll/timeline engine — not needed for flip + particles. |
| Native Structured Outputs (`messages.parse`) | Strict tool use; or prompt-"return JSON" + parse | Strict tool use when target model lacks Structured Outputs. **Never** rely on plain prompt-and-parse — that's the failure mode SO was built to remove. |
| Claude Haiku 4.5 (default) | Claude Sonnet 4.6 | Premium tone tier / deep decks post-MVP, or auto-escalation on validation failure. 3× cost. |
| Hand-rolled initData HMAC | `init-data-py` (PyPI) | Use the lib if you want maintained parsing + the Ed25519 third-party path. The hand-rolled 5-liner is standard and auditable for first-party. |
| aiogram 3.x | python-telegram-bot / grammY(JS) / raw Bot API | aiogram is the idiomatic async Python choice and matches TZ. PTB is fine but TZ specifies aiogram. |
| Native recurring Stars subscription | Manual 30-day entitlement renewal | Manual only as a fallback if you deliberately avoid auto-billing UX. Native recurring is available and simpler for users. |
| Vite 7 | Vite 8 (Rolldown) | Adopt Vite 8 post-MVP once your plugin set is confirmed compatible with Rolldown. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`framer-motion` package name** | **Renamed to `motion`.** Installing `framer-motion` pulls a legacy/redirect package; imports/docs diverge. | `pnpm add motion`; `import { motion } from "motion/react"` |
| **Redux / Redux Toolkit** | Heavy boilerplate, larger bundle — wasteful for a Mini App (edit #5). | Zustand 5 |
| **Celery / RQ / Arq (MVP)** | Generation is ONE fast LLM call. A broker/worker adds infra, deploy surface, and failure modes for zero benefit (edit #2). | Synchronous call + `tenacity` retry + timeout; Redis for limits/cache |
| **Prompt-"please return JSON" then `json.loads`** | Brittle: markdown fences, trailing prose, schema drift → parse errors and retries. | Native **Structured Outputs** (`messages.parse`) or strict tool use |
| **Dated model ID hardcoded everywhere** (e.g. `claude-haiku-4-5-YYYYMMDD`) | Couples code to a snapshot; misses free quality bumps. | Alias `claude-haiku-4-5`; log resolved version into `prompt_version`/`generation_logs` |
| **Picking cards / checking limits on the frontend** | Forgeable; breaks fair-random + unified history (TZ §12.4, §29.2; PROJECT constraint). | Backend-only `secrets`-based shuffle + server limit checks |
| **Python `random` for card selection** | Not cryptographically secure (TZ §12.5 requires CSPRNG). | `secrets.SystemRandom().shuffle(...)` / `random.SystemRandom` |
| **External card-payment acquirers (Stripe/etc.) for digital goods** | Telegram requires **Stars** for digital services in Mini Apps (TZ §2.2). | Telegram Stars (`XTR`) only |
| **SQLAlchemy 1.4 legacy `Query` API** | Project targets 2.0; mixing styles causes async footguns. | 2.0 `select()` + `AsyncSession` + `Mapped[]` |
| **Pydantic v1 idioms** (`orm_mode`, `.dict()`) | v2 changed the API; v1 is EOL. | v2: `from_attributes=True`, `.model_dump()` |
| **Vite 8 for MVP** | Rolldown default is new; possible plugin-compat surprises mid-build. | Vite 7 now; revisit 8 post-MVP |
| **The word "AI"/"нейросеть"/"модель" in UI copy** | Brand-voice constraint (PROJECT.md / TZ §0). Not a tech rule but gates copy in components. | "колода", "оракул", ритуальные формулировки |

---

## Stack Patterns by Variant

**If a future "premium tone"/deep-deck tier is added:**
- Route those readings to `claude-sonnet-4-6` inside `LLMService` (per-deck model map), keep Haiku default.
- Because: 3× cost is justified only for paid/depth content; abstraction already swaps models.

**If reading generation ever becomes genuinely long (multi-step, >~30s):**
- Only then introduce Arq (lightest async queue) + a job-status poll endpoint.
- Because: edit #2 explicitly defers this; do not pre-build it.

**If you need third-party initData verification (no bot token in that service):**
- Use the Ed25519 `signature` method (Telegram public key, `bot_id:WebAppData\n...` prefix) instead of the HMAC method.
- Because: only relevant if a separate service validates without the token — not the MVP backend.

**If admin needs richer tooling than protected SPA routes:**
- Keep edit #6 (allowlisted `/admin` routes) for MVP; consider SQLAdmin/FastAPI-Admin only if CRUD volume explodes.
- Because: minimal surface for MVP; the SPA already renders the catalog.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| React 19.2 | motion 12, TanStack Query 5, Zustand 5 | All support React 19. |
| Vite 7 | Tailwind v4 (`@tailwindcss/vite`), React plugin | Tailwind v4 ships a first-party Vite plugin; avoid the old PostCSS path. |
| FastAPI 0.136 | Pydantic 2.10, SQLAlchemy 2.0 async, Uvicorn 0.34 | Pydantic v2 is required by modern FastAPI. |
| SQLAlchemy 2.0 async | asyncpg 0.30, Alembic 1.14 | DSN `postgresql+asyncpg://`; Alembic async template. |
| aiogram 3.27 | Python 3.12, Bot API w/ Stars + subscriptions | `create_invoice_link`, `refund_star_payment`, `edit_user_star_subscription`, `get_star_transactions` all present. |
| anthropic SDK ≥0.69 | claude-haiku-4-5 / sonnet-4-6, Structured Outputs GA | `messages.parse` + Pydantic schema; no beta header needed. |
| redis-py 5.2 | Redis 7, async (`redis.asyncio`) | `redis[hiredis]` for speed. |

---

## Sources

- platform.claude.com/docs/en/build-with-claude/structured-outputs — Structured Outputs GA, `output_config.format`, `messages.parse`, model support incl. Haiku 4.5 (HIGH)
- platform.claude.com/docs/en/about-claude/pricing — Haiku 4.5 $1/$5, Sonnet 4.6 $3/$15 per MTok (HIGH)
- core.telegram.org/bots/webapps — initData HMAC algorithm, `secret = HMAC_SHA256("WebAppData", bot_token)`, auth_date freshness, Ed25519 third-party method (HIGH)
- core.telegram.org/api/subscriptions + Bot API — Stars `subscription_period=2592000`, recurring `successful_payment` (`is_recurring`/`is_first_recurring`/`subscription_expiration_date`) (HIGH)
- docs.aiogram.dev (3.27) — `create_invoice_link` (XTR, empty provider_token, single price), `pre_checkout_query`, `refund_star_payment`, `edit_user_star_subscription`, `SuccessfulPayment` fields (HIGH)
- npm registry (June 2026) — react 19.2.7, @tanstack/react-query 5.101.0, zustand 5.0.14, vite 8.0.16 (7.x recommended), motion (ex-framer-motion), tailwindcss v4 (HIGH)
- PyPI / official docs (June 2026) — FastAPI 0.136.x, SQLAlchemy 2.0, asyncpg 0.30, Pydantic 2.10.x, pydantic-settings (HIGH)
- motion.dev/docs/react-installation — package rename framer-motion → `motion`, `import { motion } from "motion/react"` (HIGH)

---
*Stack research for: Telegram Mini App — AI tarot readings (LLM interpretation + Telegram Stars)*
*Researched: 2026-06-09*
