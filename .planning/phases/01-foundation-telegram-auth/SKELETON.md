# Walking Skeleton — Зеркало Судьбы

**Phase:** 1
**Generated:** 2026-06-10

## Capability Proven End-to-End

A booting full stack: `docker compose up` runs PostgreSQL 16 + Redis 7 + a FastAPI backend that fails fast on any missing secret and answers `GET /healthz` after a real DB `SELECT 1` and Redis `PING`; a Vite/React frontend shell fetches and renders that live health result. By the end of Phase 1 the same skeleton carries the first real **write** (Telegram-validated user upsert) and the first authenticated round-trip (`initData` → JWT → `GET /api/me`).

> Note on read/write: the skeleton (Plan 01) proves a real DB **read** (`SELECT 1`) and the FE→BE round-trip. The canonical first **write** is the `users` upsert in the auth slice (Plan 04), which is the architecturally honest first mutation for this product (no row should exist before a validated identity does). The schema substrate (Plan 02) and seed (Plan 03) land between the skeleton and the auth write.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI 0.136 + Python 3.12 (async) | Locked in PROJECT.md/TZ §12.1; async-native for the validate→DB→(LLM)→persist path; thin routers + thick `services/`. |
| ASGI server | uvicorn[standard] >=0.49 | Standard FastAPI server; container `CMD uvicorn app.main:app`. |
| ORM / driver | SQLAlchemy 2.0 async + asyncpg 0.31 | `Mapped[]` typed models, `select()`, `AsyncSession`; DSN `postgresql+asyncpg://`. |
| Migrations | Alembic 1.18, async `env.py` template | One initial migration (Plan 02) owns all 17 tables; `target_metadata = Base.metadata`, URL injected from settings (not `alembic.ini`). |
| Config / secrets | pydantic-settings 2.14, fail-fast | Required secrets have no defaults → `ValidationError` at import. `ADMIN_TELEGRAM_IDS` uses `Annotated[list[int], NoDecode]` + comma-split validator (JSON-decode footgun). |
| Data store | PostgreSQL 16 (container) | JSONB, `TEXT[]`, UUID PKs, native ENUMs for fixed status sets. |
| Cache / throttle | Redis 7 (container) via redis-py `>=5.2,<6` | PING-only in Phase 1; weekly limits/throttle in later phases. Pinned `<6` to avoid the fresh redis-py 8.0 RESP3 default. |
| Auth (security spine) | Telegram `initData` two-stage HMAC + `auth_date` freshness → short-lived JWT (PyJWT HS256) | `secret = HMAC_SHA256("WebAppData", BOT_TOKEN)`; constant-time compare; `telegram_id` derived ONLY from validated data. JWT (`sub`=user UUID) is the bearer for later calls. Hand-rolled stdlib validator (auditable, zero supply-chain). |
| Authorization | Server-side allowlist `require_admin` (`telegram_id ∈ ADMIN_TELEGRAM_IDS`) | Admin = guarded routes in the same SPA; frontend guard is cosmetic. Seam wired in Phase 1 before any admin body exists (probe endpoint `GET /api/admin/ping`). |
| Bot | aiogram 3.28 as an **in-process module** (folder skeleton only in P1) | Shares DB session + idempotency with the API; first wired in Phase 7. No webhook route in Phase 1. |
| Frontend | React 19.2 + TS + Vite 7.3 (NOT 8) + Tailwind 4.3 + `motion` (NOT framer-motion) + Zustand 5 + TanStack Query 5 | Locked in PROJECT.md; Vite 7 avoids Rolldown plugin churn; React Query owns server state, Zustand holds session/JWT. |
| Error handling | Global exception handler → soft in-character JSON (no stack trace) + structured logging + optional no-op Sentry | INFRA-05; user never sees a stacktrace (TZ §29.2). Sentry init is a no-op when `SENTRY_DSN` unset; full dashboards deferred to Phase 8. |
| Package manager | `npm` (frontend), `uv`/pip (backend) | pnpm not installed locally; one lockfile per side. |
| Deploy target | timeweb.cloud App Platform (Docker), HTTPS mandatory | Compose mirrors the deploy shape; single backend container hosts REST (+ dispatcher later). Details finalized at the deploy phase (Phase 8). |

## Directory Layout (contract)

```
zerkalo-sudby/
├── docker-compose.yml          # postgres:16 + redis:7 + backend (+ frontend dev)
├── .env.example                # every required secret NAME, no values
├── backend/
│   ├── Dockerfile · pyproject.toml · alembic.ini
│   ├── alembic/ env.py + versions/0001_*.py (all 17 tables, Plan 02)
│   └── app/
│       ├── main.py             # app, lifespan, routers, global exception handler
│       ├── api/  deps.py auth.py health.py users.py admin.py   # THIN routers
│       ├── services/ telegram_auth.py                          # THICK logic
│       ├── models/ base.py + one file per aggregate            # SQLAlchemy 2 typed
│       ├── schemas/  AuthResponse, MeResponse                  # Pydantic v2
│       ├── core/  config.py db.py redis.py security.py logging.py
│       ├── seed/  __main__.py + data/*.json                    # idempotent loader
│       └── bot/                # aiogram skeleton only (Phase 7)
├── frontend/
│   └── src/ main.tsx App.tsx · api/ · stores/session.ts · lib/telegram.ts
└── docs/
```

## Stack Touched in Phase 1

- [x] Project scaffold (FastAPI + pyproject + ruff; Vite + TS + Tailwind; pytest harness) — Plan 01
- [x] Routing — `GET /healthz` (Plan 01); `POST /api/auth/telegram`, `GET /api/me`, `GET /api/admin/ping` (Plan 04)
- [x] Database — real read `SELECT 1` (Plan 01); full 17-table schema (Plan 02); real write `users` upsert + seed rows (Plan 03/04)
- [x] UI — health round-trip (Plan 01); initData → JWT → authenticated state (Plan 05)
- [x] Deployment — `docker compose up` full-stack local run + documented `curl /healthz` smoke

## Out of Scope (Deferred to Later Slices)

- Real readings, LLM calls, prompt assembly, safety classifier (Phase 4).
- Deck/spread catalog APIs + per-deck theming (Phase 2); ritual/onboarding UX (Phase 3).
- Limits enforcement + paywall (Phase 6); Telegram Stars payments + the wired bot webhook (Phase 7).
- Admin CRUD bodies + dashboards + full Sentry/analytics (Phase 8). Phase 1 ships only the `require_admin` seam + a probe endpoint + a no-op Sentry init.
- Real card art (78×6 illustrations) — Phase 1 seeds all 78 universal `cards` rows with placeholder meaning text; `deck_cards` image slots use CSS/SVG fallbacks later.
- Native Postgres ENUM value changes, read replicas, PgBouncer, queues — none in MVP.

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- **Phase 1 (this):** "It knows who I am" — open Mini App → validated `initData` → JWT → authenticated state; schema + seed substrate + admin allowlist seam.
- **Phase 2:** "I can browse decks & spreads" — 6 decks, 7 spreads, topic recommendation, per-deck theming from seeded data.
- **Phase 3:** "I can run the whole ritual (mock)" — onboarding → question/topic/deck/spread → ritual → reveal against a mock reading.
- **Phase 4 (keystone):** "I get a real, personal reading" — backend CSPRNG draw + one structured LLM call + safety classifier (crisis short-circuit) + JSON-schema validation.
- **Phase 5:** "I can revisit past readings" — history list/detail/soft-delete over immutable `reading_cards`.
- **Phase 6:** "I'm limited to 3 free/week" — weekly reset + atomic check+decrement + Redis throttle + paywall surface.
- **Phase 7:** "I can buy more / subscribe" — Telegram Stars packs + native recurring subscription via the in-process aiogram webhook.
- **Phase 8:** "Operators can run it without code" — admin CRUD + dashboards + analytics + polish + HTTPS deploy to timeweb.cloud behind a legal/IP gate.
