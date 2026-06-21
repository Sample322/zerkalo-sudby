<!-- GSD:project-start source:PROJECT.md -->
## Project

**Зеркало Судьбы — Telegram Mini App для AI-раскладов таро**

Telegram Mini App для атмосферных раскладов таро с генеративной интерпретацией. Пользователь задаёт вопрос, выбирает тему, колоду и расклад — и получает красивый интерактивный ритуал с глубокой, но бережной интерпретацией каждой карты и общим итогом. Внутри интерпретации работает LLM, но в UI продукт воспринимается как «цифровая гадалка / оракул», а не как AI-сервис: слова «AI», «нейросеть», «модель», «сгенерировано ИИ» в интерфейсе не используются.

Аудитория: 18–35 лет, интерес к таро, саморефлексии, отношениям, мистическому контенту и эстетичным mini apps; пользователи Telegram, которым нужен быстрый красивый расклад без установки отдельного приложения.

**Core Value:** **Один и тот же вопрос ощущается по-разному в разных колодах.** Если ритуал, атмосфера и персональность ответа работают — продукт живёт; всё остальное вторично. Это ядро MVP (ТЗ §30): 6 колод с разными prompt-модификаторами, тоном и визуалом дают разный опыт на один вопрос.

### Constraints

- **Tech stack (frontend)**: React 19 + TypeScript + Vite + Tailwind v4 + **`motion`** (бывш. Framer Motion — переименован; импорт `motion/react`) + **Zustand** (не Redux — легче для mini app) + React Query (TanStack Query) + Telegram WebApp SDK — ТЗ §12.1 + коррекция research (правка #5)
- **Tech stack (backend)**: FastAPI + Python 3.12+ + SQLAlchemy 2.x async + asyncpg + Alembic + Pydantic v2 + PostgreSQL + Redis (rate-limit/кэш) — ТЗ §12.1; **без Celery/RQ/Arq** (моя правка #2)
- **Tech stack (bot)**: aiogram 3.x — **как модуль внутри FastAPI-процесса** (`feed_webhook_update`), не отдельный сервис; общий DB-сеанс/идемпотентность с API (коррекция research)
- **LLM**: абстракция `LLMService` (swappable provider); **один структурированный вызов на весь расклад** через Anthropic Structured Outputs (`messages.parse(output_format=PydanticModel)` → один валидный JSON: все карты + итог); дефолт `Codex-haiku-4-5` (~$0.01/расклад), эскалация на Sonnet для premium/при ошибке валидации; low temp + одна корректирующая ретрай-попытка + таймаут + DB-fallback; лимит НЕ списывается при ошибке генерации (моя правка #1 + коррекция research)
- **Payments**: только Telegram Stars (валюта XTR) — требование Telegram для цифровых услуг; доступ засчитывается только после `successful_payment`, идемпотентность по `payload`
- **Safety**: классификатор обязателен (поднят из «желательно» ТЗ §20.4 — моя правка #3); запрет категоричных предсказаний/мед.-юр.-фин. советов; кризис → безопасный поддерживающий ответ
- **Legal/IP**: только авторские визуалы; юридическая проверка ассетов перед публичным запуском
- **Deploy**: timeweb.cloud, HTTPS обязателен. MCP-доступ ограничен (только App Platform deploy из Git; managed PostgreSQL/Redis/S3 и VPS — вручную в панели или контейнерами) — деталь развёртывания решается на этапе деплоя
- **Brand voice**: в UI/текстах/кнопках/результатах не использовать «AI», «нейросеть», «модель», «сгенерировано ИИ» (кроме юридически необходимых мест)
- **Mobile-first**: основной дизайн под смартфон 360–430px; нижняя sticky-CTA; крупные карты
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
| **anthropic** (Python SDK) | `0.69.x+` | Codex API client | Default provider behind swappable `LLMService` abstraction (TZ §12.1, edit #1). Supports **Structured Outputs** (`client.messages.parse(...)` + Pydantic schema). |
| **Codex Haiku 4.5** | `Codex-haiku-4-5` | **Default generation model** | **$1.00 / $5.00 per MTok.** Fast + cheap. One reading = ~1.5–3K input tokens (prompts + card data) + ~1–2K output. At Haiku pricing a reading costs ≈ $0.01. Quality is more than enough for atmospheric tarot copy. **This is the MVP default.** |
| **Codex Sonnet 4.6** | `Codex-sonnet-4-6` | Premium / quality fallback | **$3.00 / $15.00 per MTok.** Use for "deep" decks (Тени/Лесной) or a paid "premium tone" tier post-MVP, or as automatic retry if Haiku output fails validation. 3× the cost — not the default. |
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
## Installation
### Frontend (`/frontend`, `/admin` shares the app)
# Core runtime
# Telegram (optional typed wrapper — or use window.Telegram.WebApp directly)
# Styling (Tailwind v4 — CSS-first, via Vite plugin)
# Dev / test
### Backend (`/backend`)
# Core
# LLM + resilience
# Dev / test
### Bot (`/bot`)
## Telegram initData Validation — EXACT Algorithm (must be correct)
## Telegram Stars Payments — EXACT Flow (must be correct)
### One-time purchase (packs: 1 / 3 / 10 readings)
### Subscription ("Лунный доступ", 30-day) — NATIVE RECURRING IS AVAILABLE
- Add **`subscription_period=2592000`** (exactly 30 days — Telegram currently **only** allows this value) to `create_invoice_link`. Currency must be `XTR`.
- Telegram **auto-renews** every period, deducting Stars and firing a new `successful_payment` with **`is_recurring=True`** (and `is_first_recurring=True` on the first one). `subscription_expiration_date` is included.
- **Cancel / re-enable** from the bot: `bot.edit_user_star_subscription(user_id, telegram_payment_charge_id, is_canceled=True|False)`.
- **Source of truth = your DB, not Telegram's subscription state.** On each `successful_payment` (recurring or not) extend `subscriptions.current_period_end` / `user_entitlements` by 30 days. This keeps edit #7's "entitlement window" model while using native billing.
## LLM: Single Structured Call for the Whole Reading (edit #1)
## Redis Usage (edit #2 — no queue)
| Use | Pattern | Notes |
|-----|---------|-------|
| Weekly free limit (3/week) | Source of truth in Postgres `user_limits` (`free_used_this_week`, `week_start`); Redis as fast counter/cache | Reset weekly (compare `week_start`). Keep PG authoritative for correctness/audit. |
| Throttle / abuse | `INCR` + `EXPIRE` per-user short-window key | Prevent rapid-fire reading creation. |
| Cache base card meanings | `GET/SET` JSON, TTL or invalidate-on-admin-edit | Cards/deck_cards rarely change; avoids re-reading 78×6 rows per reading. |
| Cache deck/spread catalog | Cache `/api/decks`, `/api/spreads` responses | Admin toggle busts cache. |
| Idempotency keys (optional) | `SETNX payment:{payload}` as a fast guard | DB UNIQUE on `payload` remains the real guarantee. |
## Deploy: timeweb.cloud (App Platform, Docker)
| Service | Container | Notes |
|---------|-----------|-------|
| **backend** | `python:3.12-slim` → `uvicorn app.main:app` | FastAPI API. HTTPS required (TZ §12.1). Reads env (DATABASE_URL, REDIS_URL, BOT_TOKEN, ANTHROPIC_API_KEY, JWT_SECRET, ADMIN_TELEGRAM_IDS). |
| **bot** | `python:3.12-slim` → aiogram **webhook** | Separate process/container. Telegram → `/api/payments/webhook` (or bot's own webhook path) over HTTPS. Handles `pre_checkout_query` + `successful_payment`. |
| **frontend** | build then `nginx:alpine` static | `pnpm build` → serve `dist/`. Admin = protected `/admin` routes in same SPA (edit #6, allowlist `ADMIN_TELEGRAM_IDS` + server check). |
| **postgres** | managed PG (timeweb) or `postgres:16` container | Prefer managed for backups. |
| **redis** | managed Redis or `redis:7` container | Either works for MVP. |
# docker-compose.yml (local dev shape)
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Zustand 5 | Redux Toolkit | Never for this app (edit #5). RTK only if a large team needs strict middleware/devtools conventions — overkill for a Mini App. |
| `motion` (ex-framer-motion) | CSS-only animations / GSAP | CSS for trivial transitions (cheaper). GSAP only if you need a complex scroll/timeline engine — not needed for flip + particles. |
| Native Structured Outputs (`messages.parse`) | Strict tool use; or prompt-"return JSON" + parse | Strict tool use when target model lacks Structured Outputs. **Never** rely on plain prompt-and-parse — that's the failure mode SO was built to remove. |
| Codex Haiku 4.5 (default) | Codex Sonnet 4.6 | Premium tone tier / deep decks post-MVP, or auto-escalation on validation failure. 3× cost. |
| Hand-rolled initData HMAC | `init-data-py` (PyPI) | Use the lib if you want maintained parsing + the Ed25519 third-party path. The hand-rolled 5-liner is standard and auditable for first-party. |
| aiogram 3.x | python-telegram-bot / grammY(JS) / raw Bot API | aiogram is the idiomatic async Python choice and matches TZ. PTB is fine but TZ specifies aiogram. |
| Native recurring Stars subscription | Manual 30-day entitlement renewal | Manual only as a fallback if you deliberately avoid auto-billing UX. Native recurring is available and simpler for users. |
| Vite 7 | Vite 8 (Rolldown) | Adopt Vite 8 post-MVP once your plugin set is confirmed compatible with Rolldown. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`framer-motion` package name** | **Renamed to `motion`.** Installing `framer-motion` pulls a legacy/redirect package; imports/docs diverge. | `pnpm add motion`; `import { motion } from "motion/react"` |
| **Redux / Redux Toolkit** | Heavy boilerplate, larger bundle — wasteful for a Mini App (edit #5). | Zustand 5 |
| **Celery / RQ / Arq (MVP)** | Generation is ONE fast LLM call. A broker/worker adds infra, deploy surface, and failure modes for zero benefit (edit #2). | Synchronous call + `tenacity` retry + timeout; Redis for limits/cache |
| **Prompt-"please return JSON" then `json.loads`** | Brittle: markdown fences, trailing prose, schema drift → parse errors and retries. | Native **Structured Outputs** (`messages.parse`) or strict tool use |
| **Dated model ID hardcoded everywhere** (e.g. `Codex-haiku-4-5-YYYYMMDD`) | Couples code to a snapshot; misses free quality bumps. | Alias `Codex-haiku-4-5`; log resolved version into `prompt_version`/`generation_logs` |
| **Picking cards / checking limits on the frontend** | Forgeable; breaks fair-random + unified history (TZ §12.4, §29.2; PROJECT constraint). | Backend-only `secrets`-based shuffle + server limit checks |
| **Python `random` for card selection** | Not cryptographically secure (TZ §12.5 requires CSPRNG). | `secrets.SystemRandom().shuffle(...)` / `random.SystemRandom` |
| **External card-payment acquirers (Stripe/etc.) for digital goods** | Telegram requires **Stars** for digital services in Mini Apps (TZ §2.2). | Telegram Stars (`XTR`) only |
| **SQLAlchemy 1.4 legacy `Query` API** | Project targets 2.0; mixing styles causes async footguns. | 2.0 `select()` + `AsyncSession` + `Mapped[]` |
| **Pydantic v1 idioms** (`orm_mode`, `.dict()`) | v2 changed the API; v1 is EOL. | v2: `from_attributes=True`, `.model_dump()` |
| **Vite 8 for MVP** | Rolldown default is new; possible plugin-compat surprises mid-build. | Vite 7 now; revisit 8 post-MVP |
| **The word "AI"/"нейросеть"/"модель" in UI copy** | Brand-voice constraint (PROJECT.md / TZ §0). Not a tech rule but gates copy in components. | "колода", "оракул", ритуальные формулировки |
## Stack Patterns by Variant
- Route those readings to `Codex-sonnet-4-6` inside `LLMService` (per-deck model map), keep Haiku default.
- Because: 3× cost is justified only for paid/depth content; abstraction already swaps models.
- Only then introduce Arq (lightest async queue) + a job-status poll endpoint.
- Because: edit #2 explicitly defers this; do not pre-build it.
- Use the Ed25519 `signature` method (Telegram public key, `bot_id:WebAppData\n...` prefix) instead of the HMAC method.
- Because: only relevant if a separate service validates without the token — not the MVP backend.
- Keep edit #6 (allowlisted `/admin` routes) for MVP; consider SQLAdmin/FastAPI-Admin only if CRUD volume explodes.
- Because: minimal surface for MVP; the SPA already renders the catalog.
## Version Compatibility
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| React 19.2 | motion 12, TanStack Query 5, Zustand 5 | All support React 19. |
| Vite 7 | Tailwind v4 (`@tailwindcss/vite`), React plugin | Tailwind v4 ships a first-party Vite plugin; avoid the old PostCSS path. |
| FastAPI 0.136 | Pydantic 2.10, SQLAlchemy 2.0 async, Uvicorn 0.34 | Pydantic v2 is required by modern FastAPI. |
| SQLAlchemy 2.0 async | asyncpg 0.30, Alembic 1.14 | DSN `postgresql+asyncpg://`; Alembic async template. |
| aiogram 3.27 | Python 3.12, Bot API w/ Stars + subscriptions | `create_invoice_link`, `refund_star_payment`, `edit_user_star_subscription`, `get_star_transactions` all present. |
| anthropic SDK ≥0.69 | Codex-haiku-4-5 / sonnet-4-6, Structured Outputs GA | `messages.parse` + Pydantic schema; no beta header needed. |
| redis-py 5.2 | Redis 7, async (`redis.asyncio`) | `redis[hiredis]` for speed. |
## Sources
- platform.Codex.com/docs/en/build-with-Codex/structured-outputs — Structured Outputs GA, `output_config.format`, `messages.parse`, model support incl. Haiku 4.5 (HIGH)
- platform.Codex.com/docs/en/about-Codex/pricing — Haiku 4.5 $1/$5, Sonnet 4.6 $3/$15 per MTok (HIGH)
- core.telegram.org/bots/webapps — initData HMAC algorithm, `secret = HMAC_SHA256("WebAppData", bot_token)`, auth_date freshness, Ed25519 third-party method (HIGH)
- core.telegram.org/api/subscriptions + Bot API — Stars `subscription_period=2592000`, recurring `successful_payment` (`is_recurring`/`is_first_recurring`/`subscription_expiration_date`) (HIGH)
- docs.aiogram.dev (3.27) — `create_invoice_link` (XTR, empty provider_token, single price), `pre_checkout_query`, `refund_star_payment`, `edit_user_star_subscription`, `SuccessfulPayment` fields (HIGH)
- npm registry (June 2026) — react 19.2.7, @tanstack/react-query 5.101.0, zustand 5.0.14, vite 8.0.16 (7.x recommended), motion (ex-framer-motion), tailwindcss v4 (HIGH)
- PyPI / official docs (June 2026) — FastAPI 0.136.x, SQLAlchemy 2.0, asyncpg 0.30, Pydantic 2.10.x, pydantic-settings (HIGH)
- motion.dev/docs/react-installation — package rename framer-motion → `motion`, `import { motion } from "motion/react"` (HIGH)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.Codex/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-Codex-profile` -- do not edit manually.
<!-- GSD:profile-end -->
