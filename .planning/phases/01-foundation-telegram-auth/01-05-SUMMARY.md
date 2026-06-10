---
phase: 01-foundation-telegram-auth
plan: 05
subsystem: auth
tags: [telegram-webapp, initdata, jwt, zustand, react-19, vite, vitest, bearer-auth, brand-voice]

requires:
  - phase: 01-01
    provides: "Vite 7 + React 19 frontend shell (App.tsx, lib/api.ts with API_BASE from VITE_API_BASE), TS-strict build, .env.example"
  - phase: 01-04
    provides: "POST /api/auth/telegram contract ({init_data} -> {access_token, user, limits, settings}); generic 401 on any validation failure; GET /api/me Bearer-protected"
provides:
  - "lib/telegram.ts — getInitData() reads window.Telegram.WebApp.initData with a DEV-only VITE_DEV_INIT_DATA fallback (import.meta.env.DEV gated, stripped from prod bundle); telegramReady() calls .ready()/.expand()"
  - "stores/session.ts — Zustand useSession holding {jwt, user, availableReadings, status}; deriveAvailableReadings = (free_weekly_limit - free_used_this_week) + paid_spreads_balance"
  - "api/auth.ts — authenticate() POSTs {init_data} to /api/auth/telegram, typed AuthResponse, AuthError on non-2xx"
  - "api/client.ts — apiFetch(path, init) attaches Authorization: Bearer <jwt> from the session store (the reusable Bearer seam for all later phases)"
  - "components/AuthGate.tsx — boot flow with authenticating/authenticated/error states; in-character error copy, no stacktrace, no AI-branding"
  - "Vitest + jsdom frontend test infrastructure (npm run test) + telegram.test.ts unit test"
affects: [deck-catalog, ritual-ui, real-reading, history-profile, payments, admin-panel]

tech-stack:
  added: [vitest 3.2.6, jsdom 25.0.1]
  patterns:
    - "Frontend forwards raw initData verbatim; never parses identity client-side (threat T-05-01) — the backend is the sole authority"
    - "DEV-only mock initData via VITE_DEV_INIT_DATA gated on import.meta.env.DEV so it is tree-shaken out of the production bundle (verified absent from dist/)"
    - "Zustand holds ONLY session/JWT state; server catalog state is deferred to TanStack Query (ARCHITECTURE: never duplicate server state into Zustand)"
    - "apiFetch is the single Authorization: Bearer attachment point reused by every protected call in later phases"
    - "AuthGate renders an in-character error state on auth failure (no stacktrace/internals surfaced) — threat T-05-02"
    - "React StrictMode dev double-mount guarded with a useRef so boot auth fires exactly once"

key-files:
  created:
    - frontend/src/lib/telegram.ts
    - frontend/src/stores/session.ts
    - frontend/src/api/auth.ts
    - frontend/src/api/client.ts
    - frontend/src/components/AuthGate.tsx
    - frontend/src/lib/telegram.test.ts
  modified:
    - frontend/src/App.tsx
    - frontend/src/vite-env.d.ts
    - frontend/vite.config.ts
    - frontend/tsconfig.app.json
    - frontend/package.json
    - frontend/.env.example

key-decisions:
  - "Vitest + jsdom adopted as the frontend test framework (named in STACK.md/RESEARCH as the chosen tool); test files live next to source as *.test.ts and are excluded from the production tsc build"
  - "availableReadings derived from the auth response as (free_weekly_limit - free_used_this_week) + paid_spreads_balance, clamped at 0 — shown as 'Раскладов наготове: N' in the authenticated header"
  - "AuthError carries the HTTP status but AuthGate surfaces only a single in-character message; the failure cause never reaches the UI (mirrors the backend's no-oracle 401)"
  - "Dev mock fallback gated on import.meta.env.DEV (not a runtime env check) so Vite statically removes it from production — verified the bundle contains no VITE_DEV_INIT_DATA reference"

patterns-established:
  - "getInitData() is the single Telegram initData read point; everything else (auth, future SDK features) goes through lib/telegram.ts"
  - "apiFetch(path, init) is the Bearer-attaching client seam; protected calls in phases 2+ call it instead of raw fetch"
  - "Session store status machine: idle -> authenticating -> authenticated | error, driven by AuthGate on boot"

requirements-completed: [AUTH-01]

duration: 10min
completed: 2026-06-10
---

# Phase 01 Plan 05: Frontend Telegram Auth Wiring Summary

**The client half of the identity slice: on boot the Mini App reads `window.Telegram.WebApp.initData` (with a DEV-only mock fallback that is stripped from production), POSTs it to `POST /api/auth/telegram`, stores the JWT in a Zustand session store, attaches it as `Authorization: Bearer` via a reusable `apiFetch` seam, and renders an authenticated state ("Колода знает тебя, {first_name}" + available-readings count) — with an in-character error state on failure and zero AI-branding copy.**

## Performance

- **Duration:** ~10 min (implementation + verification; real-Telegram checkpoint deferred)
- **Started:** 2026-06-10T14:31Z
- **Completed:** 2026-06-10T14:41Z
- **Tasks:** 1 of 2 executed (Task 2 is the human-verify checkpoint — deferred to deploy, see below)
- **Files modified:** 13 (6 created, 7 modified incl. package-lock)

## Accomplishments

- **AUTH-01 (frontend) — the boot identity flow:** `AuthGate` mounts, calls `telegramReady()`, sets status `authenticating`, runs `authenticate()` (which reads `getInitData()` and POSTs `{init_data}` to `/api/auth/telegram`), stores the JWT + user in Zustand on success, and renders the authenticated greeting; on failure it shows the in-character error state. The full vertical slice "open the Mini App → it knows who I am" is wired client-side against the Plan 04 backend contract.
- **initData reader + dev fallback:** `lib/telegram.ts::getInitData()` returns `window.Telegram?.WebApp?.initData ?? ""` and, only under `import.meta.env.DEV`, falls back to `VITE_DEV_INIT_DATA` so the FE→BE→JWT flow is testable in a plain browser without a Telegram WebView. The fallback is **verified absent from the production bundle** (`grep VITE_DEV_INIT_DATA dist/` → no match), so the mock can never ship to prod. A `window.Telegram` type declaration was added.
- **Zustand session store:** `useSession` holds `{jwt, user, availableReadings, status}` with `setAuthenticating`/`setAuthenticated`/`setError`. It holds ONLY session/JWT state — server catalog state is left to TanStack Query in later phases (ARCHITECTURE). `availableReadings = max(0, free_weekly_limit - free_used_this_week) + max(0, paid_spreads_balance)`.
- **Bearer-attaching client (the reusable seam):** `api/client.ts::apiFetch(path, init)` reads `jwt` from `useSession.getState()` and sets `Authorization: Bearer <jwt>` when present. This is the single attachment point every protected call in Phases 2+ reuses.
- **In-character error handling (T-05-02):** a forged/stale/missing initData → backend 401 → `AuthError` → `setError()` → the user sees "Колода не узнала тебя. Открой ритуал из Telegram…" — no stacktrace, no exception class, no internals. Network/CSP failures map to the same soft state.
- **Brand voice:** no "AI / нейросеть / модель / сгенерировано ИИ" string anywhere in `frontend/src` user-facing copy (the only "AI" occurrence is a code comment documenting the ban). All copy is ritual/oracle framing.
- **Tests + build green:** `npm run build` (tsc -b && vite build) succeeds with 0 type errors; `vitest run src/lib/telegram.test.ts` passes 3/3 (returns injected value; returns "" without throwing when Telegram absent; returns "" when WebApp present but initData missing).

## Verification Performed (stand-in for the real-Telegram checkpoint)

A live Telegram WebView + a running backend stack are **not available in this environment** (no BotFather Mini App URL is provisioned — that is Phase 8/deploy — and the Docker daemon is not running, so `docker compose up` cannot bring up Postgres+Redis+backend). To verify the slice as strongly as possible without them, a temporary headless probe (`src/__verify__/auth-flow.probe.test.ts`, run then removed) drove the **real production modules** end-to-end against a mocked backend mirroring the `POST /api/auth/telegram` contract:

- **FE→BE contract:** `getInitData()` (mock Telegram WebView) → `authenticate()` POSTs exactly `{ init_data: "<raw string>" }` to a URL ending `/api/auth/telegram` with method POST. ✅
- **JWT storage + render data:** `setAuthenticated(response)` → status `authenticated`, `jwt` stored, `user.first_name = "Ариадна"`, `availableReadings = (3 − 1 free) + 2 paid = 4`. ✅
- **Bearer attachment:** a subsequent `apiFetch("/api/me")` carried `Authorization: Bearer <jwt>`. ✅
- **401 path:** a forged/stale 401 → `AuthError` → `setError()` → status `error`, jwt cleared, availableReadings 0 (the in-character state, no stacktrace). ✅
- **Prod-safety of the dev mock:** production bundle contains no `VITE_DEV_INIT_DATA` reference (DEV gate strips it); the real `window.Telegram` initData read path IS present in the bundle. ✅

The probe was deleted after running (it was a verification artifact, not a permanent test); the permanent `telegram.test.ts` remains. Build re-confirmed green after removal (identical `dist/` hashes).

## Task Commits

Committed atomically on `gsd/phase-01-foundation-telegram-auth`:

1. **Task 1: initData reader + session store + Bearer client + auth-on-boot flow + authenticated UI + Vitest test** — `3ba9a34` (feat)

**Plan metadata:** committed separately (docs: complete plan) with this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates.

_Task 2 is a `checkpoint:human-verify` (real Telegram WebView) — deferred to deploy; see "Outstanding: Real-Telegram Verification" below. No code remains; only human confirmation in a real Telegram client is pending._

## Files Created/Modified

**Created**
- `frontend/src/lib/telegram.ts` — `getInitData()` (real WebView + DEV-only `VITE_DEV_INIT_DATA` fallback) + `telegramReady()` + `window.Telegram` type decl
- `frontend/src/stores/session.ts` — Zustand `useSession` (`jwt`/`user`/`availableReadings`/`status`) + `deriveAvailableReadings`
- `frontend/src/api/auth.ts` — `authenticate()` POST `/api/auth/telegram`, typed `AuthResponse`/`SessionUser`/`SessionLimits`/`SessionSettings`, `AuthError`
- `frontend/src/api/client.ts` — `apiFetch()` Bearer-attaching wrapper (+ CSP `connect-src` deployment note)
- `frontend/src/components/AuthGate.tsx` — boot flow + authenticating/authenticated/error UI (StrictMode-guarded)
- `frontend/src/lib/telegram.test.ts` — Vitest unit test for `getInitData()`

**Modified**
- `frontend/src/App.tsx` — wraps content in `<AuthGate>`; authenticated `SanctumStatus` panel (keeps the Plan-01 health glance as secondary content)
- `frontend/src/vite-env.d.ts` — added `VITE_DEV_INIT_DATA?` typing
- `frontend/vite.config.ts` — Vitest config (jsdom env, `*.test.{ts,tsx}` include) + `vitest/config` reference
- `frontend/tsconfig.app.json` — exclude `*.test.ts(x)` from the production tsc build
- `frontend/package.json` (+ `package-lock.json`) — `vitest`/`jsdom` devDeps + `test` script
- `frontend/.env.example` — documented `VITE_DEV_INIT_DATA` (DEV-only, signed-by-test-bot-token guidance)

## Decisions Made

- **Vitest + jsdom as the frontend test framework** — named as the chosen tool in STACK.md/RESEARCH; needed to satisfy the plan's own `vitest run` verify command and the mandated `telegram.test.ts` artifact. Test files sit beside source and are excluded from the production `tsc` build so no test code ships.
- **`availableReadings` derivation** — `(free_weekly_limit − free_used_this_week) + paid_spreads_balance`, clamped at 0; rendered as "Раскладов наготове: N" in the authenticated header (the plan's "available readings count").
- **Dev mock gated on `import.meta.env.DEV`** (a build-time constant Vite folds) rather than a runtime env read, so the fallback branch is statically eliminated from production — confirmed by grepping the built bundle.
- **`AuthError` carries the status but the UI shows one generic in-character message** — mirrors the backend's single-401 no-oracle behavior; the cause never reaches the WebView.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed Vitest + jsdom (frontend test infrastructure)**
- **Found during:** Task 1 (verify step)
- **Issue:** The plan's automated verify is `npx vitest run src/lib/telegram.test.ts` and the plan mandates the `telegram.test.ts` artifact, but Plan 01 set up no JS test runner (`vitest` absent from `node_modules`). The test (which uses `window`) also needs a DOM environment.
- **Fix:** Added `vitest@^3` + `jsdom@^25` as devDeps (both named in STACK.md/RESEARCH as the chosen frontend test tools — not an arbitrary substitution), a `test` script, a Vitest config block (jsdom env), and excluded `*.test.ts(x)` from the production tsc build so no test code ships.
- **Files modified:** frontend/package.json, frontend/package-lock.json, frontend/vite.config.ts, frontend/tsconfig.app.json
- **Verification:** `npm install` → 0 vulnerabilities; `vitest run` → 3/3 pass; `npm run build` green; production bundle unaffected (no test/dev-mock code in `dist/`).
- **Committed in:** `3ba9a34` (Task 1).

**2. [Rule 2 - Coverage] Added a third initData unit case + a removed-after end-to-end probe**
- **Found during:** Task 1
- **Issue:** The plan mandates two `getInitData()` cases (returns injected value; returns "" when absent). The "WebApp present but initData missing" case and the full FE→BE→JWT→Bearer→401 flow were not covered, though both are core to the boundary contract and the (un-runnable here) human-verify checkpoint.
- **Fix:** Added a third permanent case to `telegram.test.ts` (WebApp present, initData missing → ""); wrote a temporary `auth-flow.probe.test.ts` that drove the real modules end-to-end against a mocked backend (asserting POST body, JWT storage, availableReadings math, Bearer header, and the 401→error state), then removed it as a verification artifact.
- **Files modified:** frontend/src/lib/telegram.test.ts (permanent); src/__verify__/auth-flow.probe.test.ts (temporary, removed)
- **Verification:** permanent suite 3/3 green; probe 2/2 green before removal; build green after removal.
- **Committed in:** `3ba9a34` (the permanent test; the probe was never committed).

---

**Total deviations:** 2 (1 blocking test-infra, 1 coverage). Both necessary to satisfy the plan's own verify command and to verify the slice in the absence of a live Telegram/stack. No scope creep — no UI feature beyond the plan; the contract (route, body, response shape, Bearer, brand voice) matches Plan 04 and the plan exactly.

**Impact on plan:** None negative. Every `<threat_model>` mitigation is honored — T-05-01 (frontend forwards raw initData, never trusts client identity), T-05-02 (in-character error, no internals), T-05-04 (env-driven `API_BASE` + documented CSP `connect-src` requirement). T-05-03 (in-memory JWT, CSP hardening) is the accepted MVP posture, revisited at deploy.

## Issues Encountered

- **No live Telegram WebView or backend stack in this environment** — the real-Telegram human-verify checkpoint (Task 2) cannot be executed here: no BotFather Mini App URL is provisioned (Phase 8/deploy) and the Docker daemon is not running (`docker version` hangs, same as Plans 01-01/01-02/01-04), so `docker compose up` cannot serve `POST /api/auth/telegram`. Compensated with the headless end-to-end probe described above (real frontend modules vs a mocked backend) + production-bundle safety checks. Real-device confirmation is genuinely deferred — see below.
- **Windows line endings** — git normalized LF→CRLF on staged files (benign warnings); the working tree is Windows but the Bash tool is POSIX (used `/c/zerkalo-sudby/...` paths).

## Outstanding: Real-Telegram Verification (deferred to deploy)

The one thing only a human can confirm, and only in a real Telegram client, remains open. It requires infrastructure provisioned at the deploy phase (Phase 8) — a real bot, a public HTTPS frontend, and a running backend:

1. `cp .env.example .env` and fill `BOT_TOKEN`, `ADMIN_TELEGRAM_IDS` (your numeric id), `JWT_SECRET`, `ANTHROPIC_API_KEY` (any non-empty for Phase 1).
2. `docker compose up` and confirm `curl -f localhost:8000/healthz` → 200 `{db:ok,redis:ok}`.
3. `cd frontend && npm run dev`, expose it over HTTPS (`cloudflared tunnel --url http://localhost:5173`), point `VITE_API_BASE` at an HTTPS backend tunnel, and ensure the WebView CSP `connect-src` allows it.
4. In @BotFather set the bot's Mini App / Web App URL to the frontend tunnel; open the Mini App from your bot.
5. Confirm the app renders the authenticated greeting (your Telegram first name) and the backend logs `200` on `POST /api/auth/telegram`; confirm a forged/stale `init_data` (via curl) returns `401`.

**To dry-run the flow locally without Telegram right now:** set `VITE_DEV_INIT_DATA` (DEV only) to a string signed by your test `BOT_TOKEN` (use the backend's `make_init_data` two-stage-HMAC signer from `backend/tests/conftest.py`), run `npm run dev` against a live backend, and the authenticated state will render; an unsigned/garbage value will (correctly) hit the in-character 401 error state.

## Next Phase Readiness

- **Phase 2 (catalog):** `apiFetch` is the ready Bearer seam for `GET /api/decks` / `/api/spreads`; `useSession` exposes the JWT + user; TanStack Query (already a dependency) will own the catalog server state on top of `apiFetch`.
- **Phase 1 closure:** all five plans' code is implemented; the only gate to "Phase 1 done" is the human real-Telegram smoke (Task 2) above + the user-run `docker compose up` cold-boot smoke carried from Plans 01-01/01-04.
- **No code blockers.** Build + unit tests green; brand-voice clean; dev mock prod-stripped.

## Self-Check: PASSED

- All 6 created files + 6 modified files verified present on disk.
- Task commit `3ba9a34` verified in git history.
- `npm run build` green (0 type errors); `vitest run src/lib/telegram.test.ts` → 3/3; full `vitest run` → 3/3.
- No banned brand-voice string in `frontend/src` UI copy; `VITE_DEV_INIT_DATA` verified absent from the production bundle.

---
*Phase: 01-foundation-telegram-auth*
*Completed: 2026-06-10*
