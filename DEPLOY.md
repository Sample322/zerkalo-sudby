# Deploy — first live test on timeweb.cloud (core loop)

Goal: get the **core reading loop** (Telegram auth → catalog → ritual → real reading →
history → free limits/paywall) live on timeweb.cloud for a closed test — **before** Phase 7
(Stars payments) and Phase 8 (admin/analytics/polish/legal). The paywall shows the soft
"скоро" sheet (no purchase) — that is correct for a pre-payments test.

## Topology (two App Platform apps + managed data stores)

```
Telegram client
      │  opens Mini App URL
      ▼
[frontend app]  nginx static (this repo /frontend, Dockerfile)   ── HTTPS url B
      │  cross-origin fetch + Bearer JWT (VITE_API_BASE = url A)
      ▼
[backend app]   FastAPI/uvicorn (this repo /backend, Dockerfile) ── HTTPS url A
      │                    │
      ▼                    ▼
[managed PostgreSQL]   [managed Redis]   (provisioned in the timeweb panel)
```

- The **bot/webhook is NOT needed** for this test — auth is via Mini App `initData`, not the
  bot. The bot appears in Phase 7 (payments).
- The backend container **auto-runs `alembic upgrade head` + `python -m app.seed`** on start
  (idempotent, see `backend/docker-entrypoint.sh`) — this closes the 06-01 migration smoke and
  seeds the 6 decks/spreads/cards/prompts automatically. Card art uses the CSS/SVG fallback;
  real art is not required for the test.

## Order of operations

1. **Push the repo to a Git provider** timeweb can pull (GitHub/GitLab). `master` is the
   deploy branch (all of Phases 1–6 are on it). _There is currently no git remote — add one._
2. **Provision managed PostgreSQL 16 + Redis 7** in the timeweb panel (MCP cannot create these
   — manual). Copy their connection strings.
3. **Create the backend app** from the repo (`/backend` Dockerfile). Set env (below). Deploy.
   On first boot the entrypoint migrates + seeds; watch logs for `seed complete: ...` and
   `GET /healthz` healthy. Note its HTTPS URL = **url A**.
4. **Create the frontend app** from the repo (`/frontend` Dockerfile) with build-arg
   `VITE_API_BASE=<url A>`. Deploy. Note its HTTPS URL = **url B**.
5. **Set the backend `CORS_ORIGINS=<url B>`** and redeploy the backend (so the Mini App origin
   is authorized).
6. **BotFather**: create a bot, grab `BOT_TOKEN`; set the Mini App URL = **url B** (`/setmenubutton`
   or a Web App in the bot menu). `BOT_TOKEN` must match the one in the backend env (initData
   HMAC validation uses it).
7. **Open the Mini App in Telegram** → run the 06-HUMAN-UAT smokes.

## Env vars

**Backend app** (required — boot fails fast if any required secret is missing):

| Var | Value |
|-----|-------|
| `BOT_TOKEN` | real bot token from BotFather (also used for initData HMAC) |
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASS@HOST:5432/DB` (managed PG; **async DSN**) |
| `REDIS_URL` | `redis://HOST:6379/0` (managed Redis; `rediss://` if TLS) |
| `JWT_SECRET` | random ≥32 bytes, e.g. `openssl rand -hex 32` |
| `ANTHROPIC_API_KEY` | real key — live readings cost ≈ $0.01 each (Haiku 4.5) |
| `ADMIN_TELEGRAM_IDS` | your Telegram numeric id(s), comma-separated, no brackets |
| `CORS_ORIGINS` | url B (the frontend origin), e.g. `https://zerkalo-frontend.timeweb.cloud` |
| `RUN_MIGRATIONS` | optional; `1` (default) auto migrate+seed, `0` to skip |

**Frontend app** (build-time, Docker build-arg — Vite inlines it):

| Build-arg | Value |
|-----------|-------|
| `VITE_API_BASE` | url A (the backend origin), e.g. `https://zerkalo-backend.timeweb.cloud` |

## First-test verification (from `.planning/phases/06-free-limits-soft-paywall/06-HUMAN-UAT.md`)

Once live, confirm: real reading renders per-deck (Phase 4 live-UAT), history persists (Phase 5),
and the Phase-6 limit machinery — `migration 0002 applied` (auto via entrypoint), exhaust 3 free →
soft paywall + reset countdown, rapid burst → throttle toast (429), «Осталось N из 3» + 1-remaining
hint, and **no «AI/нейросеть/модель»** copy anywhere.

## What is automated vs manual

- **Claude via timeweb MCP**: create App Platform app(s) from a connected VCS repo, read deploy
  settings/presets, trigger deploys.
- **Manual (panel / you)**: provision managed PostgreSQL + Redis, create the Git remote, set the
  real secrets (`BOT_TOKEN`, `ANTHROPIC_API_KEY`, `JWT_SECRET`), and the BotFather Mini App URL.

## Hardening deferred to public launch (Phase 8 — NOT required for a closed test)

- Nonce-based CSP + `connect-src` allowlist on the frontend (nginx) for the Telegram WebView.
- Separate release/job step for migrations if running multiple backend instances
  (`RUN_MIGRATIONS=0` on the web instances).
- Legal/IP review of deck assets before any public launch.
