---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: planning
last_updated: "2026-06-12T16:47:39.755Z"
last_activity: 2026-06-12
progress:
  total_phases: 8
  completed_phases: 3
  total_plans: 14
  completed_plans: 14
  percent: 38
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-09)

**Core value:** Один и тот же вопрос ощущается по-разному в разных колодах — красивый мистический ритуал в Telegram, дающий глубокий, но бережный ответ.
**Current focus:** Phase 4 — real personal reading (keystone)

## Current Position

Phase: 4
Plan: Not started
Status: Ready to plan
Last activity: 2026-06-12

Progress: [███████░░░] 71%

## Performance Metrics

**Velocity:**

- Total plans completed: 9
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3 | - | - |
| 03 | 6 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P01 | 35 | 3 tasks | 47 files |
| Phase 01 P02 | 30 | 2 tasks | 14 files |
| Phase 01 P03 | 35 | 2 tasks | 10 files |
| Phase 01 P04 | 40 | 3 tasks | 19 files |
| Phase 01 P05 | 10 | 1 tasks | 13 files |
| Phase 03 P01 | 10 | 3 tasks | 16 files |
| Phase 03 P02 | 5 | 2 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Build order: vertical-MVP slices — each phase ships an end-to-end user-visible capability, not a horizontal layer.
- Phase 1: aiogram bot is an in-process FastAPI module (not a separate service); bot module first wired in Phase 7 (Payments).
- Phase 1: `initData` two-stage HMAC + `auth_date` freshness is the security spine; `telegram_id` derived only from validated initData.
- Phase 4 (KEYSTONE): one structured LLM call per reading + mandatory safety classifier gating generation (crisis short-circuits before draw/charge); limit never consumed on failure.
- Card draw + limit checks are backend-only (CSPRNG) throughout.
- [Phase ?]: Phase 1: full 17-table schema (16 TZ §13 + topics lookup) locked in one initial Alembic migration 0001; native PG ENUMs for the 9 fixed status/type sets; topics is a lookup only (not a FK target), readings.topic stays a TEXT slug.
- [Phase ?]: Phase 1: slug keys + users.telegram_id + payments.payload UNIQUE constraints are the durable integrity guarantees later phases (auth upsert, payment idempotency) and the admin panel rely on.
- [Phase ?]: Phase 1: MVP seed shipped as JSON files + `python -m app.seed` CLI (not an Alembic data-migration) — re-runnable, content editable independent of schema history (RESEARCH Pattern 6).
- [Phase ?]: Phase 1: idempotent seed via upsert-by-slug (ON CONFLICT DO UPDATE); spread_positions (no single-column unique key) rebuilt per spread via a scoped delete->insert inside the same transaction.
- [Phase ?]: Phase 1: initData validator is hand-rolled to the exact Telegram two-stage HMAC (secret=HMAC_SHA256(b'WebAppData',bot_token), constant-time hmac.compare_digest, auth_date freshness); telegram_id derived ONLY from the validated user blob, never the request body.
- [Phase ?]: Phase 1: JWT is PyJWT HS256 with sub=user UUID + telegram_id claim; decode pins algorithms=['HS256'] so alg:none is rejected; get_current_user is the reusable Bearer gate, require_admin the server-side ADMIN_TELEGRAM_IDS allowlist.
- [Phase ?]: Phase 1: thin routers delegate to services/telegram_auth.authenticate() (TelegramAuthService reused by the bot in Phase 7); INFRA-05 global Exception handler returns soft in-character JSON (no stacktrace leak), Sentry is a no-op seam deferred to Phase 8.
- [Phase ?]: Phase 1: frontend auth wiring complete — getInitData() reads window.Telegram.WebApp.initData with a DEV-only VITE_DEV_INIT_DATA fallback (stripped from prod bundle); useSession (Zustand) holds jwt/user/availableReadings/status; apiFetch is the reusable Authorization: Bearer seam for all later phases; AuthGate renders authenticating/authenticated/error with in-character copy and zero AI-branding.
- [Phase ?]: Phase 3: FlowRoot is the single AnimatePresence step-switch (D-02); Wave-2 plans replace only their own screen stub, never FlowRoot.
- [Phase ?]: Phase 3: ephemeral mock reading lives only in the Zustand store (reading slot + setReading), never TanStack Query; createReading() is the single Phase-4 source-swap seam (D-05).
- [Phase ?]: Phase 3: canonical SAFE-06 BANNED_BRAND_TOKENS helper in reading/copy.ts detects the standalone Cyrillic ИИ token without false-positiving benign words (W-1); all Wave-2 SAFE-06 tests import it.

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- Phase 4 flagged for deeper research at plan time: single-call JSON schema design, cheap safety-classifier approach, retry/timeout/fallback contract (highest product+technical risk).
- Phase 7 flagged for research: exact aiogram Stars surface, refund semantics (21-day), native recurring subscription modeling (lock native-recurring vs manual-window before schema usage — choose one, not a hybrid).
- Phase 8: timeweb.cloud deploy specifics deferred by design (MCP only does App Platform git deploy; managed PG/Redis/S3 + VPS provisioned manually); IP/legal review of deck assets required before public launch.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-06-12T16:47:39.745Z
Stopped at: Phase 4 context gathered
Resume file: .planning/phases/04-real-personal-reading-keystone/04-CONTEXT.md
