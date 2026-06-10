# Phase 1: Foundation & Telegram Auth — Research

**Researched:** 2026-06-10
**Domain:** Monorepo bootstrap (Docker Compose: Postgres 16 + Redis 7) · SQLAlchemy 2 async + Alembic full-schema migration + idempotent seed · Telegram `initData` two-stage HMAC validation → JWT · admin allowlist · Vite/React walking-skeleton
**Confidence:** HIGH (stack versions re-verified against PyPI/npm 2026-06-10; initData/JWT/Alembic/pydantic-settings patterns verified against official docs today; extends `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md` from 2026-06-09)

## Summary

This phase is a **Walking Skeleton + security spine**: `docker compose up` brings up Postgres 16 + Redis 7 + FastAPI; Alembic migrates all 16 tables; an idempotent seed loads 7 topics / 6 decks / 7 spreads (+ positions) / 78 cards / base prompt templates; opening the Mini App POSTs `initData`, the server validates the two-stage HMAC + `auth_date` freshness, upserts the user, returns a JWT; and an admin-allowlist dependency (`require_admin`) is wired even though no admin endpoints have bodies yet. The three prior research docs already pin the stack and give the exact HMAC algorithm; this document **verifies current versions** (several drifted upward since yesterday — `alembic 1.14→1.18`, `redis-py 5.2→8.0`, `pydantic-settings 2.7→2.14`), nails down **implementation-level patterns** the planner needs (async Alembic `env.py`, pydantic-settings fail-fast + the `list[int]` JSON-parsing footgun for `ADMIN_TELEGRAM_IDS`, PyJWT encode/decode, SQLAlchemy 2 typed models for JSONB/`TEXT[]`/enums/UUID), and surfaces **two design questions** that block clean planning (topics have no table; bot module is imported but not wired until Phase 7).

**Primary recommendation:** Build one deployable FastAPI process. Put business logic in `services/`, keep routers thin, centralize initData validation in `TelegramAuthService` (hand-rolled stdlib HMAC — auditable, no dependency), derive `telegram_id` ONLY from validated initData, and treat the full 16-table Alembic migration + idempotent JSON-seed-loader as the two largest tasks. Pin versions explicitly; do not float `redis-py` to 8.x or `anthropic` without a verify checkpoint.

<user_constraints>
## User Constraints (from PROJECT.md — no phase-level CONTEXT.md exists yet)

> No `01-CONTEXT.md` was found in the phase directory. The binding constraints below are lifted from `PROJECT.md` (Key Decisions + Constraints) and `CLAUDE.md`, which carry locked-decision authority for this project. The planner MUST honor these.

### Locked Decisions (relevant to Phase 1)
- **Monorepo:** `/frontend`, `/backend` (with aiogram bot as an **in-process module**, not a separate service), `/docs`. Local dev via Docker Compose (Postgres + Redis).
- **Backend stack:** FastAPI + Python 3.12+ + SQLAlchemy 2.x **async** + asyncpg + Alembic + Pydantic v2 + PostgreSQL + Redis. **No Celery/RQ/Arq.**
- **Bot:** aiogram 3.x as an in-process FastAPI module (`feed_webhook_update`); shares DB session + idempotency with the API. **First wired in Phase 7** — in Phase 1 the folder/module may exist but no webhook route is required.
- **Auth security spine:** `initData` two-stage HMAC (`secret = HMAC_SHA256(key="WebAppData", msg=bot_token)`) + `auth_date` freshness is the security spine; `telegram_id` derived **only** from validated initData, never from request body.
- **Admin:** allowlist by `ADMIN_TELEGRAM_IDS` + **server-side** `require_admin` check (edit #6). Admin = guarded routes in the same SPA.
- **Card draw + limit checks are backend-only (CSPRNG)** throughout (not exercised in Phase 1 but the schema/seed must support it).
- **Frontend stack:** React 19 + TS + Vite + Tailwind v4 + `motion` (NOT `framer-motion`) + Zustand + TanStack Query + Telegram WebApp SDK.
- **Brand voice:** no "AI / нейросеть / модель / сгенерировано ИИ" in any UI string (applies to the skeleton's authenticated-state screen too).

### Claude's Discretion (Phase 1)
- Hand-rolled stdlib initData HMAC **vs** `init-data-py` lib → research recommends hand-rolled (below).
- JWT expiry window, `auth_date` MAX_AGE window (recommend values below).
- Seed data file format (JSON vs YAML) and load mechanism (Alembic data migration vs standalone CLI) → recommend below.
- Whether `/bot` module skeleton is created now or deferred to Phase 7.
- `uv` vs Poetry for Python deps; `pnpm` vs `npm` for JS (pnpm not installed locally — see Environment Availability).

### Deferred Ideas (OUT OF SCOPE for Phase 1)
- Anything in Phases 2–8: real readings, LLM, payments, limits enforcement, history, admin CRUD bodies, analytics dashboards.
- Sentry/error-tracking *wiring* is **INFRA-05**, mapped to Phase 1 in REQUIREMENTS.md but the ROADMAP Phase-1 success criteria do not enumerate it — see Open Question #4. Soft-error-not-stacktrace behavior is in scope; full Sentry integration is borderline and should be confirmed.
- Background queue (excluded from the whole MVP).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-01 | Monorepo (`/frontend`, `/backend` w/ in-process aiogram, `/docs`) + Docker Compose (Postgres + Redis) | Project Structure, docker-compose shape, Dockerfile pattern (below) |
| INFRA-02 | Alembic migrations for full 16-table schema | Standard Stack (Alembic 1.18 async), Architecture Pattern 1 (async `env.py`), §13 schema map, Code Examples |
| INFRA-03 | Seed: 7 topics, 6 decks, 7 spreads+positions, 78 cards, base prompt templates | Seed Strategy pattern, idempotent upsert, exact slugs from §27/§19, Open Question #1 (topics) |
| INFRA-04 | Backend healthcheck + env config with fail-fast secret validation (bot token, DB, Redis, LLM key) | pydantic-settings fail-fast pattern, `GET /healthz` DB+Redis probe, secret inventory |
| INFRA-05 | Logs + error tracking (Sentry/analog); generation errors stored, user sees soft error not stacktrace | structlog/logging setup, soft-error handler; Sentry scope flagged (Open Question #4) |
| AUTH-01 | User auths via Telegram WebApp; frontend sends `initData` → `POST /api/auth/telegram` | Auth flow, frontend skeleton, POST contract |
| AUTH-02 | Backend validates `initData` (two-stage HMAC, sorted check-string sans `hash`) + `auth_date` freshness; rejects invalid/stale | initData EXACT algorithm (verified), Pitfall 1, Validation Architecture |
| AUTH-03 | First login creates profile; repeat updates `last_seen_at` | User upsert pattern (INSERT … ON CONFLICT), users table fields §13.1 |
| AUTH-04 | Backend issues JWT; frontend uses it for later requests | PyJWT encode/decode (verified), `get_current_user` Bearer dependency |
| AUTH-05 | Admin endpoints only for `ADMIN_TELEGRAM_IDS`, server-side | `require_admin` dependency, allowlist parsing footgun, 403 path |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `initData` HMAC validation | API / Backend | — | Requires `BOT_TOKEN` secret; never client-side (client value is forgeable). The entire identity model rests here. |
| JWT issue / verify | API / Backend | — | Signed with server `JWT_SECRET`; client only stores + echoes the bearer. |
| User upsert (profile from validated initData) | API / Backend | Database | Identity fields written server-side from the validated `user` blob only. |
| Admin allowlist enforcement | API / Backend | — | `telegram_id ∈ ADMIN_TELEGRAM_IDS` checked server-side; frontend route guard is cosmetic. |
| Schema migration (16 tables) | Database | API / Backend | Alembic owns DDL; models live in backend but the migration is the source of truth. |
| Seed data load | Database | API / Backend | Idempotent loader writes seed rows; data files are code-managed in backend. |
| Health check (DB+Redis reachability) | API / Backend | Database, Redis/Cache | Backend probes its dependencies; orchestrator (Compose/timeweb) consumes the result. |
| Config / secret loading + fail-fast | API / Backend | — | `pydantic-settings` validates presence at process start, before serving. |
| Read `window.Telegram.WebApp.initData`, POST it, store JWT | Browser / Client | Frontend Server (static host) | Only the browser has the Telegram WebView context; the static host just serves the SPA. |
| Authenticated-state UI | Browser / Client | — | Thinnest real interaction proving end-to-end; renders `/api/me`-style data. |

## Standard Stack

> **Re-verified against PyPI / npm on 2026-06-10.** Several versions drifted upward since STACK.md (2026-06-09). Where the registry "latest" is a fresh major bump with migration risk, the recommendation **pins the prior stable line** and tags the bleeding-edge version `[ASSUMED]` for a verify checkpoint. **Provenance note:** package *names* originate from STACK.md/CLAUDE.md (project docs) — per the package-name provenance rule these are tagged `[ASSUMED]` even though registry existence is confirmed, because none were discovered from Context7 (unavailable this session). Registry existence ≠ slopcheck-verified. The planner should gate first-install behind the Package Legitimacy checkpoint.

### Core — Backend (`/backend`)

| Library | Version (pin) | Registry latest (2026-06-10) | Purpose | Why Standard |
|---------|---------------|------------------------------|---------|--------------|
| FastAPI | `0.136.*` | 0.136.3 | HTTP API | Async-native, Pydantic v2, OpenAPI 3.1. `[VERIFIED: PyPI 0.136.3]` |
| Uvicorn | `>=0.49` (`uvicorn[standard]`) | 0.49.0 | ASGI server | Standard FastAPI server. `[VERIFIED: PyPI 0.49.0]` |
| SQLAlchemy | `2.0.*` (use 2.0.50+) | 2.0.50 | Async ORM | `Mapped[]` typed models, `select()`, `AsyncSession`. `[VERIFIED: PyPI 2.0.50]` |
| asyncpg | `0.31.*` | 0.31.0 | Postgres async driver | DSN `postgresql+asyncpg://`. STACK.md said 0.30; **0.31 is current**. `[VERIFIED: PyPI 0.31.0]` |
| Alembic | `1.18.*` | 1.18.4 | Migrations | Async template (`alembic init -t async`). STACK.md said 1.14 — **stale; use 1.18**. `[VERIFIED: PyPI 1.18.4]` |
| Pydantic | `2.13.*` | 2.13.4 | Schemas / validation | v2 Rust core. STACK.md said 2.10. `[VERIFIED: PyPI 2.13.4]` |
| pydantic-settings | `2.14.*` | 2.14.1 | Config from env/.env | Fail-fast `ValidationError` on missing required field. STACK.md said 2.7. `[VERIFIED: PyPI 2.14.1]` |
| PyJWT | `2.13.*` | 2.13.0 | Session tokens | HS256 encode/decode; auto-verifies `exp`. STACK.md said 2.10. `[VERIFIED: PyPI 2.13.0]` |
| redis-py | **pin `>=5.2,<6` (`redis[hiredis]`)** | **8.0.0** (2026-05-28) | Redis client | `redis.asyncio` for the healthcheck PING. **8.0.0 is ~2 weeks old (RESP3 default).** Recommend the proven 5.2 line for MVP; 8.0 `[ASSUMED]` → verify checkpoint. See Pitfall 4. |
| PostgreSQL | `16` (container `postgres:16`) | — | Database | JSONB, `TEXT[]`, UUID, enums all native. `[CITED: ROADMAP success criterion]` |
| Redis | `7` (container `redis:7`) | — | Cache/throttle (PING-only in P1) | Provisioned now; used by limits/payments later. `[CITED: ROADMAP]` |

### Core — Frontend (`/frontend`, walking-skeleton subset)

| Library | Version (pin) | Registry latest (2026-06-10) | Purpose | Why Standard |
|---------|---------------|------------------------------|---------|--------------|
| React + ReactDOM | `19.2.*` | 19.2.7 | UI runtime | `[VERIFIED: npm 19.2.7]` |
| Vite | **`7.3.*` (NOT 8)** | 8.0.16 (`latest`); **7.3.5** exists | Build/dev | Vite 8 default = Rolldown (new); stay on 7 for MVP. `pnpm create vite@7`. `[VERIFIED: npm — 7.3.5 on 7.x line, 8.0.16 is latest tag]` |
| TanStack Query | `5.101.*` (or newer 5.x) | 5.101.0 | Server state | `/api/me` fetch + auth mutation. `[VERIFIED: npm 5.101.0]` |
| Zustand | `5.0.*` | 5.0.14 | Client state | Holds session/JWT. `[VERIFIED: npm 5.0.14]` |
| Tailwind CSS + `@tailwindcss/vite` | `4.3.*` | 4.3.0 | Styling | CSS-first; first-party Vite plugin. `[VERIFIED: npm 4.3.0]` |
| motion | `12.*` | 12.40.0 | Animation | **NOT `framer-motion`.** Minimal use in skeleton. `[VERIFIED: npm 12.40.0]` |
| @telegram-apps/sdk-react | `3.*` (optional) | 3.3.9 | Typed Telegram WebApp wrapper | Optional — raw `window.Telegram.WebApp.initData` is fully viable for the skeleton. `[VERIFIED: npm 3.3.9]` |

### Supporting (Phase 1 scope)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog *or* stdlib `logging` | 24.x / stdlib | Structured logs | INFRA-05 soft-error logging; JSON logs for timeweb. |
| pytest + pytest-asyncio + httpx (`ASGITransport`) | latest | Tests | initData unit tests, `/healthz` + `/api/auth/telegram` integration tests. |
| ruff | `0.9.*`+ | Lint/format | Single fast tool. |
| sentry-sdk | latest (IF INFRA-05 in scope) | Error tracking | Only if Open Question #4 resolves "wire Sentry now". |
| (bot) aiogram | `3.28.*` (3.28.2) | Telegram bot | **Module skeleton only in P1**; not wired until Phase 7. `[VERIFIED: PyPI 3.28.2]` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled initData HMAC | `init-data-py` (PyPI) | Lib adds the Ed25519 third-party path + maintained parsing, but the first-party HMAC is a ~10-line stdlib function — auditable, zero supply-chain surface, recommended. |
| `pnpm` | `npm` (Node 22 present) / `corepack enable pnpm` | pnpm not installed locally; npm works. See Environment Availability. |
| `uv` | Poetry / pip | `uv` is much faster; either fine. Pin a lockfile. |
| Alembic data migration for seed | Standalone CLI seed command | Recommend **CLI command** (`python -m app.seed`) calling an idempotent loader, invoked separately from `alembic upgrade head` — keeps DDL and data concerns separate and re-runnable. See Seed Strategy. |
| redis-py 8.0 | redis-py 5.2 | 8.0 is fresh (RESP3 default); 5.2 is battle-tested and the async API is identical for PING. Pin 5.2 for MVP. |

**Installation:**
```bash
# Backend (uv)
uv pip install "fastapi==0.136.*" "uvicorn[standard]>=0.49" \
  "sqlalchemy[asyncio]==2.0.*" "asyncpg==0.31.*" "alembic==1.18.*" \
  "pydantic==2.13.*" "pydantic-settings==2.14.*" \
  "redis[hiredis]>=5.2,<6" "pyjwt==2.13.*"
uv pip install pytest pytest-asyncio httpx "ruff>=0.9"
# (bot module skeleton, optional in P1)
uv pip install "aiogram==3.28.*"

# Frontend (pnpm — or swap to npm)
pnpm create vite@7 frontend -- --template react-ts
pnpm add react@19 react-dom@19 @tanstack/react-query@5 zustand@5 motion
pnpm add @telegram-apps/sdk-react@3            # optional
pnpm add -D tailwindcss@4 @tailwindcss/vite
```

**Version verification performed:** all backend versions confirmed via `https://pypi.org/pypi/<pkg>/json`, all frontend via `https://registry.npmjs.org/<pkg>` on 2026-06-10.

## Package Legitimacy Audit

> slopcheck could not be installed this session (no network wheel; `command -v slopcheck` empty). Per the graceful-degradation rule, every package below is tagged `[ASSUMED]` and the planner MUST gate the first install of each behind a `checkpoint:human-verify` task. Registry existence + age + a known source repo were verified manually via the PyPI/npm JSON APIs as a partial substitute.

| Package | Registry | Age signal | Source repo (known) | slopcheck | Disposition |
|---------|----------|-----------|---------------------|-----------|-------------|
| fastapi | PyPI | mature (0.136.3) | github.com/fastapi/fastapi | N/A (unavailable) | Approved — `[ASSUMED]`, verify on install |
| sqlalchemy | PyPI | mature (2.0.50) | github.com/sqlalchemy/sqlalchemy | N/A | Approved — `[ASSUMED]` |
| asyncpg | PyPI | mature (0.31.0) | github.com/MagicStack/asyncpg | N/A | Approved — `[ASSUMED]` |
| alembic | PyPI | mature (1.18.4) | github.com/sqlalchemy/alembic | N/A | Approved — `[ASSUMED]` |
| pydantic / pydantic-settings | PyPI | mature (2.13.4 / 2.14.1) | github.com/pydantic/* | N/A | Approved — `[ASSUMED]` |
| pyjwt | PyPI | mature (2.13.0) | github.com/jpadilla/pyjwt | N/A | Approved — `[ASSUMED]` |
| redis (redis-py) | PyPI | **8.0.0 fresh (2026-05-28)**; 5.2.1 mature | github.com/redis/redis-py | N/A | Approved on **5.2 line**; 8.0 flagged — pin `<6` |
| uvicorn | PyPI | mature (0.49.0) | github.com/encode/uvicorn | N/A | Approved — `[ASSUMED]` |
| aiogram | PyPI | mature (3.28.2) | github.com/aiogram/aiogram | N/A | Approved — `[ASSUMED]` (module only in P1) |
| react / react-dom | npm | mature (19.2.7) | github.com/facebook/react | N/A | Approved — `[ASSUMED]` |
| vite | npm | mature (7.3.5 / 8.0.16) | github.com/vitejs/vite | N/A | Approved on **7.x**; avoid 8 for MVP |
| @tanstack/react-query | npm | mature (5.101.0) | github.com/TanStack/query | N/A | Approved — `[ASSUMED]` |
| zustand | npm | mature (5.0.14) | github.com/pmndrs/zustand | N/A | Approved — `[ASSUMED]` |
| motion | npm | mature (12.40.0) | github.com/motiondivision/motion | N/A | Approved — `[ASSUMED]` (NOT `framer-motion`) |
| @tailwindcss/vite, tailwindcss | npm | mature (4.3.0) | github.com/tailwindlabs/tailwindcss | N/A | Approved — `[ASSUMED]` |
| @telegram-apps/sdk-react | npm | mature (3.3.9) | github.com/Telegram-Mini-Apps/telegram-apps | N/A | Approved (optional) — `[ASSUMED]` |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck unavailable).
**Packages flagged suspicious [SUS]:** none by signal, but `redis 8.0.0` (2-week-old major) and any `framer-motion` mistype are the two to watch. The cross-ecosystem trap to avoid: `motion` is the npm package; do NOT `pip install` anything named `motion`.

## Architecture Patterns

### System Architecture Diagram (Phase-1 slice only)

```
┌────────────────────────── TELEGRAM CLIENT (WebView) ───────────────────────────┐
│   React Mini App (Vite SPA)                                                     │
│   reads window.Telegram.WebApp.initData ──┐                                     │
│   stores JWT (Zustand) ; TanStack Query   │ renders authenticated state         │
└───────────────────────────────────────────┼────────────────────────────────────┘
                                             │ 1) POST /api/auth/telegram {init_data}
                                             │ 4) Authorization: Bearer <JWT>  (GET /api/me-style)
                                             ▼
┌──────────────────────────── FastAPI process (single deployable) ────────────────┐
│  api/ (THIN routers)                 services/ (THICK, all logic)                │
│   auth.py  ── POST /api/auth/telegram ─►  TelegramAuthService                    │
│   deps.py  ── get_current_user ───────►     2) parse → 2-stage HMAC → compare    │
│            ── require_admin ──────────►        3) auth_date freshness check      │
│   health.py ─ GET /healthz                     ↓ valid → upsert user, issue JWT  │
│                                          (PyJWT HS256, JWT_SECRET)               │
│  core/config.py  ── pydantic-settings BaseSettings (fail-fast on missing secret)│
│  core/db.py      ── async engine + async_sessionmaker (asyncpg)                 │
│  core/redis.py   ── redis.asyncio client                                        │
│         │ GET /healthz probes ▼                ▼ upsert / read                   │
│   ┌───────────────┐                     ┌───────────────────┐                    │
│   │   Redis 7     │  PING               │   PostgreSQL 16   │  SELECT 1 / users  │
│   │  (compose)    │◄───────────────────►│  (compose)        │◄──────────────────►│
│   └───────────────┘                     │  Alembic: 16 tbl  │                    │
│  bot/ (module skeleton, NOT wired in P1)│  seed: 6/7/7/78    │                    │
└──────────────────────────────────────────────────────────────────────────────────┘

Trace the primary use case: initData enters at (1) → HMAC+freshness (2,3) → upsert+JWT →
client stores JWT → echoes it as Bearer (4) on the next call. /healthz independently
proves DB+Redis reachability for `docker compose up`.
```

### Recommended Project Structure

```
zerkalo-sudby/
├── docker-compose.yml          # postgres:16 + redis:7 + backend (+ frontend dev)
├── .env.example                # every required secret, no values
├── backend/
│   ├── Dockerfile              # python:3.12-slim → uvicorn app.main:app
│   ├── pyproject.toml          # deps + ruff config (uv or poetry)
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              # ASYNC template (async_engine_from_config + run_sync)
│   │   └── versions/0001_*.py  # ONE migration: all 16 tables + indexes/uniques
│   └── app/
│       ├── main.py             # FastAPI app, lifespan (engine/redis), mount routers
│       ├── api/
│       │   ├── deps.py         # get_current_user (JWT), require_admin (allowlist)
│       │   ├── auth.py         # POST /api/auth/telegram
│       │   ├── health.py       # GET /healthz (DB+Redis)
│       │   └── users.py        # GET /api/me  (proves Bearer path end-to-end)
│       ├── services/
│       │   └── telegram_auth.py# validate_init_data + upsert + issue_jwt
│       ├── models/             # SQLAlchemy 2 typed models (one file per aggregate)
│       │   └── base.py         # DeclarativeBase, UUID/timestamp mixins, PG enums
│       ├── schemas/            # Pydantic request/response (AuthResponse, MeResponse)
│       ├── core/
│       │   ├── config.py       # Settings(BaseSettings) — fail-fast
│       │   ├── db.py           # async engine + async_sessionmaker
│       │   ├── redis.py        # redis.asyncio client
│       │   └── security.py     # encode_jwt / decode_jwt (PyJWT)
│       ├── seed/
│       │   ├── __main__.py     # `python -m app.seed` → idempotent loader
│       │   └── data/           # topics.json decks.json spreads.json cards.json prompts.json
│       └── bot/                # aiogram handlers — skeleton only, imported later (Phase 7)
├── frontend/
│   └── src/
│       ├── main.tsx App.tsx
│       ├── api/                # axios/fetch client w/ JWT, TanStack Query hooks
│       ├── stores/session.ts   # Zustand: jwt, user
│       └── lib/telegram.ts      # read window.Telegram.WebApp.initData
└── docs/
```

### Pattern 1: Async Alembic `env.py` (VERIFIED — official cookbook)

**What:** Alembic's migration runner is synchronous; for an async engine you wrap it with `connection.run_sync` inside an `asyncio.run`.
**When to use:** Always, for this project (SQLAlchemy 2 async + asyncpg).
**Key:** inject the DB URL from app settings (don't hardcode in `alembic.ini`), and use `NullPool`.

```python
# alembic/env.py (online section) — Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html
import asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.core.config import settings
from app.models.base import Base   # target_metadata = Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)  # inject from env, not ini
target_metadata = Base.metadata

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())
```
> `alembic init -t async` scaffolds exactly this; you then point `target_metadata` at your `Base` and inject the URL. The DSN MUST be `postgresql+asyncpg://...`.

### Pattern 2: pydantic-settings fail-fast config + the `list[int]` env footgun (VERIFIED)

**What:** A `BaseSettings` with **no defaults** on required secrets → instantiation raises `ValidationError` at process start if any are missing (satisfies INFRA-04 "fail fast if a required secret is missing").
**Critical footgun:** pydantic-settings parses complex types (`list`, `dict`) from env vars as **JSON by default**. `ADMIN_TELEGRAM_IDS=111,222` will raise a JSON-decode error unless you opt out of JSON decoding. Use a `field_validator(mode="before")` (with `NoDecode`) to split a comma string.

```python
# core/config.py — Source: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/
from typing import Annotated
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, NoDecode

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Required — missing any of these => ValidationError at startup (fail-fast):
    BOT_TOKEN: str
    DATABASE_URL: str          # postgresql+asyncpg://user:pass@postgres:5432/db
    REDIS_URL: str             # redis://redis:6379/0
    JWT_SECRET: str
    ANTHROPIC_API_KEY: str     # LLM key — required by INFRA-04 even though unused until Phase 4

    # Admin allowlist — MUST bypass JSON decoding:
    ADMIN_TELEGRAM_IDS: Annotated[list[int], NoDecode] = []

    # Optional / tunable:
    JWT_EXPIRE_SECONDS: int = 60 * 60 * 24 * 7     # 7-day session token
    INITDATA_MAX_AGE_SECONDS: int = 86400          # 24h freshness window
    WEBHOOK_SECRET: str | None = None              # X-Telegram-Bot-Api-Secret-Token (Phase 7)

    @field_validator("ADMIN_TELEGRAM_IDS", mode="before")
    @classmethod
    def _parse_ids(cls, v):
        if isinstance(v, str):
            return [int(x) for x in v.split(",") if x.strip()]
        return v

settings = Settings()   # called at import → fail-fast
```
> Decision needed (Claude's discretion): `ANTHROPIC_API_KEY` and `WEBHOOK_SECRET` aren't *used* in Phase 1. INFRA-04 explicitly lists "LLM key" as a required-at-startup secret, so keep `ANTHROPIC_API_KEY` required. Keep `WEBHOOK_SECRET` optional until Phase 7.

### Pattern 3: Telegram `initData` two-stage HMAC (VERIFIED — extends STACK.md §initData)

This is the **security spine** (AUTH-02). The algorithm is unchanged from STACK.md and re-confirmed against `core.telegram.org/bots/webapps`. Reproduced here because the planner builds tasks directly against it. **Note the HMAC key/message order** and **constant-time compare**.

```python
# services/telegram_auth.py — hand-rolled, stdlib only (recommended over a dependency)
import hmac, hashlib, time, json
from urllib.parse import parse_qsl

def validate_init_data(init_data: str, bot_token: str, max_age: int = 86400) -> dict:
    pairs = dict(parse_qsl(init_data, strict_parsing=True))   # do NOT url-decode further
    received_hash = pairs.pop("hash", None)
    pairs.pop("signature", None)                              # belongs to Ed25519 method, not this
    if not received_hash:
        raise ValueError("missing hash")
    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed   = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):     # constant-time
        raise ValueError("bad hash")
    if time.time() - int(pairs.get("auth_date", "0")) > max_age:
        raise ValueError("expired")
    return pairs        # pairs["user"] is a JSON string → json.loads for telegram_id, etc.
```

**`POST /api/auth/telegram` contract (AUTH-01/03/04):**
- Request: `{ "init_data": "<raw window.Telegram.WebApp.initData string>" }`
- Server: `validate_init_data` → `user = json.loads(pairs["user"])` → derive `telegram_id` **only** from `user["id"]` → upsert → issue JWT.
- Response (per TZ §14.1): `{ "access_token": "<jwt>", "user": {...}, "limits": {...}, "settings": {...} }`
- Failure: `401` (bad hash / stale / missing) with a generic message; never leak which check failed in detail.

### Pattern 4: User upsert (AUTH-03) — INSERT … ON CONFLICT

**What:** First login inserts; repeat updates `last_seen_at` (+ refreshable profile fields). Use Postgres upsert so it's one atomic statement.

```python
# Source: SQLAlchemy 2 docs — sqlalchemy.dialects.postgresql.insert
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timezone

stmt = insert(User).values(
    telegram_id=tg["id"], username=tg.get("username"),
    first_name=tg.get("first_name"), last_name=tg.get("last_name"),
    language_code=tg.get("language_code"), photo_url=tg.get("photo_url"),
    last_seen_at=datetime.now(timezone.utc),
).on_conflict_do_update(
    index_elements=[User.telegram_id],                       # telegram_id UNIQUE
    set_={"last_seen_at": datetime.now(timezone.utc),
          "username": tg.get("username"), "updated_at": datetime.now(timezone.utc)},
).returning(User)
user = (await session.execute(stmt)).scalar_one()
# Also ensure a user_limits row exists (insert-if-absent) so later phases have it.
```

### Pattern 5: `get_current_user` + `require_admin` FastAPI dependencies (AUTH-04/05)

```python
# api/deps.py — Source: PyJWT usage + FastAPI security
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

bearer = HTTPBearer(auto_error=True)

async def get_current_user(cred: HTTPAuthorizationCredentials = Depends(bearer), session=Depends(get_session)):
    try:
        payload = jwt.decode(cred.credentials, settings.JWT_SECRET, algorithms=["HS256"])  # verifies exp
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
    user = await session.get(User, payload["sub"])     # sub = user UUID (str)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown user")
    return user

async def require_admin(user: User = Depends(get_current_user)):
    if user.telegram_id not in settings.ADMIN_TELEGRAM_IDS:   # server-side allowlist
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    return user
```
> JWT claims: `sub` = user UUID (str), `telegram_id` (int, convenience), `iat`, `exp`. PyJWT verifies `exp` automatically in `decode`.

### Pattern 6: Seed Strategy — idempotent, re-runnable, data-file driven (INFRA-03)

**What:** Ship seed content as JSON files under `backend/app/seed/data/` and load via a standalone CLI (`python -m app.seed`) that uses **upsert by `slug`** for every entity, so it is safe to run repeatedly.
**Why CLI, not Alembic data-migration:** keeps DDL (`alembic upgrade head`) separate from content; content can be re-seeded/refined (later via admin) without a new migration; easier to test row counts. Run order matters (FKs): topics → decks → cards → deck_cards → spread_types → spread_positions → deck_spread_compatibility → prompt_templates.

```python
# app/seed/__main__.py (shape)
async def upsert_by_slug(session, Model, rows):
    for r in rows:
        stmt = pg_insert(Model).values(**r).on_conflict_do_update(
            index_elements=["slug"], set_={k: r[k] for k in r if k != "slug"})
        await session.execute(stmt)
# load decks.json (6), spreads.json (7) + positions, cards.json (78), prompts.json (system/
# single_card/final_summary/deck_modifier×6/safety/refusal), topics (see Open Question #1).
```

### Anti-Patterns to Avoid (Phase-1 relevant)
- **Reading `telegram_id` from the request body / `initDataUnsafe`** → full auth bypass. Derive only from validated initData. (PITFALLS Pitfall 1.)
- **Business logic in routers** → put it in `services/`; routers stay thin so the bot/admin can reuse services later. (PITFALLS Anti-Pattern 5.)
- **`framer-motion` in package.json** → renamed to `motion`; installs a legacy/redirect package. (STACK.md What-NOT.)
- **Floating `redis-py` to 8.x or `anthropic` latest unpinned** → fresh majors; pin and gate.
- **Hardcoding DB URL in `alembic.ini`** → inject from settings so Compose/timeweb env wins.
- **`ADMIN_TELEGRAM_IDS` as a plain `list[int]` without `NoDecode`** → JSON-decode crash at startup on `111,222`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async migrations | Custom DDL runner / raw SQL files | Alembic 1.18 async template | Autogenerate, downgrade, version table, async `run_sync` wrapper all solved. |
| Env/secret loading + validation | `os.environ[...]` scattered + manual checks | pydantic-settings `BaseSettings` | One fail-fast `ValidationError` at startup; typed; `.env` support. |
| JWT sign/verify | HMAC-by-hand token format | PyJWT (`encode`/`decode`) | Auto `exp` verification, standard claims, well-audited. |
| Postgres upsert | SELECT-then-INSERT race | `insert(...).on_conflict_do_update` | Atomic; no TOCTOU on `telegram_id`/`slug`. |
| Async Postgres pool/session | Manual connection mgmt | SQLAlchemy `async_sessionmaker` + lifespan | Per-request session, pooling, transaction scoping. |
| Health probe semantics | Ad-hoc try/except | Explicit DB `SELECT 1` + Redis `PING` in `/healthz` | Real reachability, not "process is up". |
| initData crypto | Inventing a check-string format | The exact documented two-stage HMAC (stdlib `hmac`/`hashlib`) | One wrong step = silent auth bypass; the algorithm is fixed by Telegram. **Implement it, but exactly to spec — this is the one place "hand-rolled" means "to the published algorithm".** |

**Key insight:** In this phase "don't hand-roll" applies to *infrastructure* (migrations, config, JWT, pooling). The initData HMAC is the deliberate exception — it's ~10 lines of stdlib against a fixed published spec, more auditable than a dependency, but it must match the spec byte-for-byte.

## Runtime State Inventory

> Greenfield phase — no prior runtime state exists. The categories are answered for completeness because this phase *creates* the durable substrate later phases depend on.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no DB exists yet. This phase **creates** Postgres schema + seed rows (slugs become permanent keys: deck/spread/topic slugs from §27, card slugs, prompt-template slugs). | Lock slug naming now; later phases + admin reference these slugs. |
| Live service config | None — no external services configured. Bot webhook NOT registered in P1 (Phase 7). | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | New `.env` keys introduced as exact names code reads: `BOT_TOKEN`, `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `ANTHROPIC_API_KEY`, `ADMIN_TELEGRAM_IDS`, (`WEBHOOK_SECRET` reserved). These names become a contract for timeweb deploy. | Document all in `.env.example`; do not rename later without code change. |
| Build artifacts | None yet. First `docker compose build` produces backend image; first `alembic upgrade head` writes `alembic_version` table. | None — fresh. |

**The canonical question** ("after every file is updated, what runtime systems still hold old state?") is moot for a greenfield phase: **None — verified, nothing pre-exists.**

## Common Pitfalls

### Pitfall 1: initData validation done wrong → spoofed `telegram_id` / auth bypass (CRITICAL)
**What goes wrong:** trusting `initDataUnsafe`/body `telegram_id`; using raw bot token as HMAC key instead of the two-stage derivation; unsorted/wrong-delimiter check-string; not excluding `hash`; URL-decoding values before hashing; skipping `auth_date`. Any one = anyone forges any user (drains balances, reads history, impersonates admin).
**Why:** `initDataUnsafe` "works" in dev; the two-stage HMAC is subtly easy to get wrong and a wrong impl still returns a valid-looking user on the happy path.
**How to avoid:** the exact algorithm in Pattern 3; constant-time `hmac.compare_digest`; derive `telegram_id` only from validated `user`; centralize in `TelegramAuthService`; unit-test with a captured real initData plus tampered-hash, stale-`auth_date`, missing-`hash` variants.
**Warning signs:** no `"WebAppData"` constant in the code; `telegram_id` read from body/query; no test feeds a forged hash. *(Extends PITFALLS Pitfall 1.)*

### Pitfall 2: `ADMIN_TELEGRAM_IDS` JSON-decode crash at startup
**What goes wrong:** declaring `ADMIN_TELEGRAM_IDS: list[int]` and setting `ADMIN_TELEGRAM_IDS=111,222` → pydantic-settings tries `json.loads("111,222")` → `SettingsError`/`ValidationError` and the app won't boot (looks like a "missing secret" failure but isn't).
**Why:** pydantic-settings JSON-decodes complex types from env by default.
**How to avoid:** `Annotated[list[int], NoDecode]` + `field_validator(mode="before")` splitting on comma (Pattern 2). Document the `.env.example` value format as `111,222` (comma, no brackets).
**Warning signs:** boot fails only when the allowlist has >1 id, or only when set via env (not via code default).

### Pitfall 3: Healthcheck that lies ("process up" ≠ "deps reachable")
**What goes wrong:** `/healthz` returns 200 from a bare handler while Postgres/Redis are unreachable → `docker compose up` looks healthy but the first real request 500s; success criterion #1 ("`GET /healthz` healthy") is falsely green.
**How to avoid:** `/healthz` runs `await session.execute(text("SELECT 1"))` and `await redis.ping()`; return 503 with which dependency failed (server-side detail only). Use Compose `depends_on` + healthchecks so backend waits for DB/Redis.
**Warning signs:** `/healthz` has no DB/Redis call; backend starts before Postgres accepts connections.

### Pitfall 4: redis-py / asyncpg / Vite version drift vs. STACK.md
**What goes wrong:** STACK.md (1 day old) already lists stale pins (`alembic 1.14`, `redis 5.2`, `pydantic-settings 2.7`). Blindly `pip install redis` now pulls **8.0.0** (2-week-old major, RESP3 default); blindly `npm create vite` pulls **Vite 8** (Rolldown default). Either can introduce subtle breakage mid-phase.
**Why:** "latest" tags move; fresh majors land between research and execution.
**How to avoid:** pin exactly as the Standard Stack table says (`redis[hiredis]>=5.2,<6`, `vite@7`, `asyncpg==0.31.*`, `alembic==1.18.*`); put a Package Legitimacy checkpoint before first install; if 8.x/Vite-8 is desired, do it as a deliberate, tested upgrade, not by default.
**Warning signs:** lockfile shows `redis 8.x` or `vite 8.x` unintentionally; CI passes locally on host Python 3.14 but the container is 3.12 (test in the container).

### Pitfall 5: Topics seeded with nowhere to live (schema/seed mismatch)
**What goes wrong:** INFRA-03 says "seed 7 topics," but TZ §13 has **no `topics` table** — topics are string slugs used in `decks.recommended_topics TEXT[]`, `spread_types.recommended_topics TEXT[]`, and `readings.topic TEXT`. A planner may invent a table that contradicts the schema, or skip topics entirely.
**How to avoid:** decide explicitly (Open Question #1). Recommended: treat the 7 topics as a **canonical constant** (a `topics.json` + a Python `Enum`/frozenset used for validation) and *optionally* add a tiny `topics(slug, title)` lookup table if the catalog/UI needs titles from the DB. Keep it consistent with the `TEXT`/`TEXT[]` columns either way.
**Warning signs:** a migration creates a `topics` table with FKs the rest of the schema doesn't reference; or `/api/spreads/recommend` (Phase 2) has no source of topic titles.

### Pitfall 6: Host Python 3.14 vs container 3.12 confusion
**What goes wrong:** local `python` is 3.14; running the backend on the host may hit library wheels/behaviour not validated for 3.14, while production runs `python:3.12-slim`. Tests "pass on my machine" diverge from the deployed image.
**How to avoid:** run/test the backend **inside the Compose container** (3.12) as the source of truth; if running on host, create a 3.12 venv via `uv python install 3.12`. Pin `requires-python = ">=3.12,<3.13"` in `pyproject.toml` to make intent explicit.

## Code Examples

### `GET /healthz` (INFRA-04 success criterion #1)
```python
# api/health.py
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
router = APIRouter()

@router.get("/healthz")
async def healthz(session=Depends(get_session), redis=Depends(get_redis)):
    checks = {}
    try:
        await session.execute(text("SELECT 1")); checks["db"] = "ok"
    except Exception:
        checks["db"] = "down"
    try:
        await redis.ping(); checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "down"
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(checks, status_code=200 if healthy else 503)
```

### Async engine + session lifespan (SQLAlchemy 2)
```python
# core/db.py — Source: SQLAlchemy 2 async docs
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session():
    async with SessionLocal() as session:
        yield session
```

### Typed model with UUID PK / JSONB / TEXT[] / PG enum (SQLAlchemy 2)
```python
# models/base.py + models/deck.py — Source: SQLAlchemy 2 ORM + sqlalchemy.dialects.postgresql
import uuid
from sqlalchemy import String, Integer, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase): ...

class Deck(Base):
    __tablename__ = "decks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    title: Mapped[str]
    visual_style: Mapped[dict] = mapped_column(JSONB, default=dict)
    recommended_topics: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    access_type: Mapped[str] = mapped_column(String, default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
```
> For status/orientation enums use either Postgres native `ENUM` (`SAEnum(..., name="reading_status")`) or a `String` + `CHECK`/app-level validation. Native ENUM gives DB-level integrity but every value change is a migration; `String` is simpler for MVP. Recommend **native ENUM** for the small fixed sets (`reading.status`, `reading_cards.orientation`, `payments.status`, `products.product_type`, `subscriptions.status`, `prompt_templates.type`, `cards.arcana_type`) since they're stable.

### Frontend walking-skeleton (reads initData → auth → store JWT → render)
```ts
// src/lib/telegram.ts
export const initData = (): string => window.Telegram?.WebApp?.initData ?? "";
// src/api/auth.ts
export async function authenticate() {
  const res = await fetch(`${API}/api/auth/telegram`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ init_data: initData() }),
  });
  if (!res.ok) throw new Error("auth failed");
  return res.json();          // { access_token, user, limits, settings }
}
// On boot: call authenticate() → store access_token in Zustand → fetch GET /api/me with Bearer
// → render "Колода знает тебя, {first_name}" (NO "AI"/"нейросеть" — brand voice).
```
> Telegram Mini App needs HTTPS even in dev → tunnel with `cloudflared`/`ngrok`. The WebView's CSP `connect-src` must allow the API origin (flag for the planner: confirm `connect-src` includes the tunnel/API URL).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Sync SQLAlchemy `Query` + sync Alembic | SQLAlchemy 2.0 async (`Mapped[]`, `select()`, `AsyncSession`) + Alembic async `env.py` | SQLAlchemy 2.0 (2023) | All models/queries async; `env.py` uses `run_sync`. |
| Pydantic v1 (`orm_mode`, `.dict()`) | Pydantic v2 (`from_attributes=True`, `.model_dump()`) | v2 (2023) | v1 idioms are EOL; use v2 everywhere. |
| `framer-motion` | `motion` (`import { motion } from "motion/react"`) | package rename (2024) | Installing the old name pulls a redirect/legacy pkg. |
| Vite 7 (esbuild) | Vite 8 (Rolldown default) — Dec 2025 | **Stay on 7 for MVP** | Rolldown plugin-compat still settling. |
| redis-py 5.x (RESP2) | redis-py 8.0 (RESP3 default) — May 2026 | **Stay on 5.2 for MVP** | RESP3 wire change; legacy response shapes preserved but pin to be safe. |

**Deprecated/outdated to avoid:** SQLAlchemy 1.4 `Query`; Pydantic v1; `framer-motion`; `Math.random()`/`random.random()` for any future draw (CSPRNG only — not exercised in P1 but the schema enables it).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All package **names** are legitimate (slopcheck unavailable; only registry existence + known repos verified) | Standard Stack / Legitimacy Audit | LOW per-package (all are well-known), but the gate is process-required → planner adds a verify checkpoint before first install. |
| A2 | Pin `redis[hiredis]>=5.2,<6` (avoid 8.0) is correct for MVP | Standard Stack, Pitfall 4 | LOW — 8.0 likely works (PING is trivial) but pinning avoids RESP3 surprises; revisit post-MVP. |
| A3 | Stay on Vite 7, not 8 | Standard Stack | LOW — matches STACK.md rationale; Rolldown compat is the only risk. |
| A4 | `ANTHROPIC_API_KEY` should be a **required** startup secret in Phase 1 (per INFRA-04 "LLM key") even though unused until Phase 4 | Pattern 2, Secrets inventory | MEDIUM — if treated optional, fail-fast won't catch a missing LLM key until Phase 4. Confirm with user. |
| A5 | Topics are a string-slug set, not a table (no `topics` table in §13) | Pitfall 5, Open Question #1 | MEDIUM — wrong choice creates schema/seed inconsistency that ripples into Phase 2 recommend logic. |
| A6 | JWT 7-day expiry + 24h `auth_date` window are acceptable defaults | Pattern 2 | LOW — tunable; security-conscious users may want shorter (e.g. 1h auth window, 1–24h JWT). |
| A7 | Seed via standalone CLI (`python -m app.seed`), not an Alembic data migration | Seed Strategy | LOW — both work; CLI keeps DDL/data separate and is re-runnable. |
| A8 | aiogram/bot is a **module skeleton only** in Phase 1 (no webhook route) | Project Structure, constraints | LOW — matches "bot first wired in Phase 7"; confirm the folder is created now vs. deferred. |
| A9 | Native Postgres ENUM for the small fixed status/type sets | Code Examples | LOW — `String`+CHECK is the alternative; ENUM changes need migrations. |

## Open Questions

1. **Topics: table or constant?** TZ §13 defines **no `topics` table**; topics are slugs in `TEXT`/`TEXT[]` columns. INFRA-03 says "seed 7 topics." 
   - What we know: 7 canonical slugs (`love, work, money, choice, day, self_reflection, general`) from §27.1; used by decks/spreads/readings as strings.
   - What's unclear: whether to add a lookup `topics(slug,title)` table (for titles/admin) or keep them as a code constant.
   - **Recommendation:** ship `topics.json` + a Python `Enum`/frozenset for validation **and** a minimal `topics(slug,title)` table so Phase 2's `/spreads/recommend` and the UI have a DB source of titles — but only if the planner confirms it won't be treated as a FK target (the `TEXT[]` columns stay strings). Flag for discuss-phase.

2. **"16 tables" exact set.** §13 enumerates §13.1–§13.16 = exactly 16: `users, decks, cards, deck_cards, spread_types, spread_positions, deck_spread_compatibility, readings, reading_cards, prompt_templates, user_limits, products, payments, subscriptions, app_events, generation_logs`. (No `topics`, no `user_entitlements` — TZ mentions "user_entitlements" prose-only in §11.4; the actual store is `user_limits`/`subscriptions`.) 
   - **Recommendation:** migrate exactly these 16. Treat "user_entitlements" as a synonym for the `user_limits`+`subscriptions` pair, not a 17th table.

3. **Indexes/uniques to assert in the migration.** Required: `users.telegram_id UNIQUE`; `decks.slug`, `cards.slug`, `spread_types.slug`, `prompt_templates.slug`, `products.slug` all UNIQUE; `payments.payload UNIQUE` + index `payments.telegram_payment_charge_id`; FK indexes on hot paths (`reading_cards.reading_id`, `readings.user_id`, `app_events.user_id`, `generation_logs.reading_id`). Most aren't exercised until later phases but should land in the initial migration so later phases don't need DDL.

4. **INFRA-05 (Sentry/error tracking) scope in Phase 1.** REQUIREMENTS.md maps INFRA-05 to Phase 1, but the ROADMAP Phase-1 success criteria do **not** list Sentry; TZ §23 puts Sentry in Этап 10 (polish). 
   - **Recommendation:** in Phase 1 implement the *soft-error-not-stacktrace* exception handler + structured logging (cheap, satisfies the spirit of INFRA-05 and is needed for `/api/auth/telegram` failures), and **defer full Sentry wiring** to the deploy/polish phase unless the user wants it now. Confirm with user.

5. **WebView CSP `connect-src`.** The Mini App must reach the API origin; the dev tunnel (cloudflared/ngrok) URL changes. Decide how `connect-src` is configured (env-driven) so the skeleton's `fetch` isn't CSP-blocked. Low effort, easy to miss.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Docker | INFRA-01 Compose | ✓ | 28.3.2 | — |
| Docker Compose | INFRA-01 | ✓ | v2.38.2 | — |
| Node.js | Frontend build | ✓ | 22.14.0 | — |
| pnpm | Frontend (STACK.md assumes) | ✗ | — | `npm` (bundled with Node 22) **or** `corepack enable pnpm` |
| Python (host) | Backend dev | ✓ (3.14) | 3.14.1 / 3.14.5 | **Target 3.12 in container**; host 3.14 ≠ deploy target — use container or `uv python install 3.12` |
| slopcheck | Package legitimacy gate | ✗ | — | Manual registry/repo verification done; planner adds verify checkpoint |
| ctx7 / Context7 MCP | Doc lookup | ✗ | — | Official docs via WebFetch (done) |
| cloudflared / ngrok | HTTPS tunnel for Telegram dev | unknown (not probed) | — | Either; Telegram requires HTTPS for Mini App. Planner should add an install/run step. |

**Missing dependencies with no fallback:** none — every gap has a viable path.
**Missing dependencies with fallback:**
- **pnpm** → use `npm` or enable via `corepack`. The planner should pick one and be consistent (lockfile).
- **Host Python 3.14** vs container 3.12 → run/test in the container (3.12) as source of truth.
- **slopcheck** → manual verification + a `checkpoint:human-verify` before first dependency install.

## Validation Architecture

> `nyquist_validation: true` (config) → this section is REQUIRED and drives VALIDATION.md. Test framework: **pytest + pytest-asyncio + httpx `ASGITransport`** (async in-process client; no live server needed). DB/Redis for integration tests via the same Docker Compose services (or testcontainers if the planner prefers isolation).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio + httpx (ASGITransport) — backend; Vitest — frontend utils (minimal in P1) |
| Config file | none yet — **Wave 0** creates `pyproject.toml [tool.pytest.ini_options]` (`asyncio_mode = "auto"`) + `conftest.py` |
| Quick run command | `pytest tests/unit -x -q` (initData/config — no DB) |
| Full suite command | `pytest -q` (unit + integration; integration needs Postgres+Redis up) |

### Phase Requirements → Test Map
| Req ID | Behavior (observable signal) | Test Type | Automated Command | File Exists? |
|--------|------------------------------|-----------|-------------------|-------------|
| AUTH-02 | Forged `hash` → `401` | unit | `pytest tests/unit/test_initdata.py::test_forged_hash_rejected -x` | ❌ Wave 0 |
| AUTH-02 | Tampered field (valid-looking but recomputed hash mismatch) → `401` | unit | `...::test_tampered_field_rejected` | ❌ Wave 0 |
| AUTH-02 | Stale `auth_date` (> MAX_AGE) → `401` | unit | `...::test_stale_auth_date_rejected` | ❌ Wave 0 |
| AUTH-02 | Missing `hash` → `401` | unit | `...::test_missing_hash_rejected` | ❌ Wave 0 |
| AUTH-01/02/03/04 | Valid initData → `200` + JWT present + `users` row upserted; `telegram_id` from validated data only | integration | `pytest tests/int/test_auth_flow.py::test_valid_initdata_issues_jwt_and_upserts -x` | ❌ Wave 0 |
| AUTH-03 | Second valid auth updates `last_seen_at`, does not duplicate user | integration | `...::test_repeat_auth_updates_last_seen` | ❌ Wave 0 |
| AUTH-04 | JWT used as Bearer on `GET /api/me` → `200`; bad/expired JWT → `401` | integration | `pytest tests/int/test_me.py` | ❌ Wave 0 |
| AUTH-05 | Non-allowlisted `telegram_id` → `403` on an admin probe endpoint | integration | `pytest tests/int/test_admin_guard.py::test_non_admin_403` | ❌ Wave 0 |
| AUTH-05 | Allowlisted `telegram_id` → `200` on the admin probe endpoint | integration | `...::test_admin_200` | ❌ Wave 0 |
| INFRA-04 | `GET /healthz` → `200` when DB+Redis reachable | integration | `pytest tests/int/test_health.py::test_healthz_ok` | ❌ Wave 0 |
| INFRA-04 | Missing required secret → process fails to start (`ValidationError`) | unit | `pytest tests/unit/test_config.py::test_missing_secret_fails_fast` | ❌ Wave 0 |
| INFRA-04 | `ADMIN_TELEGRAM_IDS="111,222"` parses to `[111,222]` (not JSON-crash) | unit | `...::test_admin_ids_csv_parsed` | ❌ Wave 0 |
| INFRA-02 | `alembic upgrade head` applies all 16 tables; `alembic downgrade base` clean | integration | `pytest tests/int/test_migration.py::test_full_schema_applies` (assert 16 tables + key uniques present via `information_schema`) | ❌ Wave 0 |
| INFRA-03 | Seed loads exact counts: topics=7, decks=6, spreads=7, cards=78, prompt_templates=N | integration | `pytest tests/int/test_seed.py::test_seed_counts` | ❌ Wave 0 |
| INFRA-03 | Seed is idempotent (run twice → same counts, no dup-key error) | integration | `...::test_seed_idempotent` | ❌ Wave 0 |
| INFRA-01 | `docker compose up` → backend container healthy, `/healthz` reachable on host | smoke (manual/CI) | `docker compose up -d && curl -f localhost:8000/healthz` | ❌ Wave 0 |
| INFRA-05 | Forced internal error returns soft JSON (no stack trace in body) | integration | `pytest tests/int/test_error_shape.py::test_no_stacktrace_leak` | ❌ Wave 0 |

**Capturing a real `initData` fixture:** the unit tests need a valid sample. Generate one deterministically in a fixture by *constructing* a valid initData from a fake `BOT_TOKEN` (compute the correct `hash` with the same two-stage HMAC), so tests don't depend on a live Telegram session. Tampered/stale variants mutate one field or `auth_date` from that fixture. (This doubles as a correctness check on the algorithm.)

### Sampling Rate
- **Per task commit:** `pytest tests/unit -x -q` (fast, no DB).
- **Per wave merge:** `pytest -q` (full unit+integration; DB+Redis up).
- **Phase gate:** full suite green + `docker compose up` smoke (`/healthz` 200) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `pyproject.toml [tool.pytest.ini_options]` with `asyncio_mode = "auto"` + framework install (`pytest pytest-asyncio httpx`).
- [ ] `tests/conftest.py` — async client (`ASGITransport`), test-DB session/transaction-rollback fixture, `make_init_data(bot_token, user, auth_date)` helper.
- [ ] `tests/unit/test_initdata.py`, `test_config.py`.
- [ ] `tests/int/test_auth_flow.py`, `test_me.py`, `test_admin_guard.py`, `test_health.py`, `test_migration.py`, `test_seed.py`, `test_error_shape.py`.
- [ ] An admin **probe endpoint** (e.g. `GET /api/admin/ping` behind `require_admin`) so AUTH-05 is testable before real admin bodies exist (Phase 8).

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high`. This phase IS the security spine — these controls are first-class, not advisory.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control (this phase) |
|---------------|---------|-------------------------------|
| V2 Authentication | **yes** | Telegram initData two-stage HMAC (Pattern 3) is the auth mechanism; constant-time compare; `auth_date` freshness = replay defense. |
| V3 Session Management | **yes** | Short-lived JWT (HS256), `JWT_SECRET` from env, `exp` auto-verified by PyJWT; no server session store (stateless bearer). |
| V4 Access Control | **yes** | `require_admin` server-side allowlist (`ADMIN_TELEGRAM_IDS`); deny-by-default on admin routes; `telegram_id` from validated data only. |
| V5 Input Validation | **yes** | Pydantic v2 request models; `init_data` parsed/validated before trust; reject malformed early. |
| V6 Cryptography | **yes** | stdlib `hmac`/`hashlib` for HMAC-SHA256; **never hand-roll the primitive** — use stdlib; `hmac.compare_digest` for compares. JWT signing via PyJWT. |
| V7 Error/Logging | **yes** | Soft errors to client (no stack traces — INFRA-05); detailed errors logged server-side; log auth failures. |
| V8 Data Protection | partial | Secrets only via env/`.env` (gitignored); `.env.example` carries names, never values; no secrets in logs. |
| V14 Configuration | **yes** | Fail-fast on missing secrets (pydantic-settings); HTTPS mandatory for Telegram; pin dependency versions. |

### Known Threat Patterns for {FastAPI + Telegram Mini App + JWT}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Spoofed `telegram_id` via `initDataUnsafe`/body | Spoofing | Server-side HMAC validation; derive id only from validated initData (Pattern 3). |
| Replay of leaked `initData` | Spoofing/Tampering | `auth_date` freshness window (`INITDATA_MAX_AGE_SECONDS`); reject stale. |
| Forged/tampered JWT | Spoofing/Tampering | HS256 signature verify with secret env; `algorithms=["HS256"]` (never `none`); reject on `InvalidTokenError`. |
| Privilege escalation to admin | Elevation of Privilege | Server-side allowlist check (`require_admin`); frontend guard is cosmetic only. |
| Secret leakage (token in repo/logs) | Information Disclosure | env-only secrets; `.env` gitignored; no secret in error bodies/logs; rotate `BOT_TOKEN` if exposed. |
| Timing attack on hash compare | Information Disclosure | `hmac.compare_digest` (constant-time) for both HMAC and any token compare. |
| Stack-trace / internal-error leakage | Information Disclosure | Global exception handler → soft in-character JSON; details server-side only (INFRA-05). |
| Dependency supply-chain (slopsquat) | Tampering | Pin versions; Package Legitimacy checkpoint before first install; `motion` (npm) ≠ any pip pkg. |
| `algorithm: none` JWT bypass | Spoofing | Explicit `algorithms=["HS256"]` on decode (PyJWT rejects `none` unless allowed). |

## Sources

### Primary (HIGH confidence)
- `https://alembic.sqlalchemy.org/en/latest/cookbook.html` — async `env.py` (`async_engine_from_config`, `run_sync`, `asyncio.run`) — fetched 2026-06-10.
- `https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/` — `BaseSettings` env/.env load, `ValidationError` on missing required field, complex-type JSON-decode default + `NoDecode`/`field_validator` for comma-separated lists — fetched 2026-06-10.
- `https://pyjwt.readthedocs.io/en/stable/usage.html` — `jwt.encode`/`decode` HS256, automatic `exp` verification, `ExpiredSignatureError`/`InvalidTokenError` — fetched 2026-06-10.
- PyPI JSON API (`pypi.org/pypi/<pkg>/json`) — fastapi 0.136.3, sqlalchemy 2.0.50, asyncpg 0.31.0, alembic 1.18.4, pydantic 2.13.4, pydantic-settings 2.14.1, pyjwt 2.13.0, redis 8.0.0 (2026-05-28) / 5.2.1, uvicorn 0.49.0, aiogram 3.28.2, tenacity 9.1.4 — queried 2026-06-10.
- npm registry (`registry.npmjs.org/<pkg>`) — react 19.2.7, vite 8.0.16 (`latest`) / 7.3.5, @tanstack/react-query 5.101.0, zustand 5.0.14, motion 12.40.0, tailwindcss/@tailwindcss/vite 4.3.0, @telegram-apps/sdk-react 3.3.9 — queried 2026-06-10.
- `.planning/research/STACK.md` (2026-06-09) — verified initData HMAC 5-liner, stack rationale, What-NOT-to-Use (HIGH; versions superseded by today's registry check where noted).
- `.planning/research/ARCHITECTURE.md` (2026-06-09) — component boundaries, thin-router/thick-service, bot-as-module, auth flow, data-model boundaries (HIGH).
- `.planning/research/PITFALLS.md` (2026-06-09) — Pitfall 1 (initData), security/perf tables, "looks-done-but-isn't" checklist (HIGH for Telegram protocol).
- `.planning/REFERENCE-TZ.md` §13 (16-table schema), §14 (API), §16–§19 (prompts), §27 (seed slugs), §29 (backend rules) — source of truth.

### Secondary (MEDIUM confidence)
- `https://redis.io/docs/.../8-0/` + redis-py GitHub releases — redis-py 8.0 RESP3-default + legacy response shapes; async API unchanged (verified via WebSearch 2026-06-10).
- `https://github.com/redis/redis-py/releases`, `https://github.com/redis/redis-py/blob/master/CHANGES` — redis-py changelog.

### Tertiary (LOW confidence)
- None requiring validation beyond the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack (versions): **HIGH** — every package re-verified on PyPI/npm 2026-06-10; drift from STACK.md explicitly corrected.
- Architecture/patterns (Alembic async, pydantic-settings, PyJWT, initData, upsert): **HIGH** — verified against official docs today; initData matches Telegram spec.
- Pitfalls: **HIGH** for Telegram/auth + version-drift; **MEDIUM** for redis-py 8.0 impact (PING is trivial so low practical risk).
- Open design questions (topics table, INFRA-05 scope): **flagged, not resolved** — need user/discuss decision; do not block planning of the core auth+schema work.

**Research date:** 2026-06-10
**Valid until:** ~2026-07-10 for stack pins (fast-moving: redis-py 8.x, Vite 8, anthropic SDK — re-check before install); patterns (Alembic/PyJWT/initData/pydantic-settings) stable for ~90 days.
