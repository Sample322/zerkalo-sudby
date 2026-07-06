---
phase: 08-admin-analytics-polish-deploy
verified: 2026-07-07
verifier: inline (orchestrator — gsd-verifier subagent hits provider session limits)
mode: goal-backward (lean-slice scope, 08-CONTEXT D-01)
status: passed
requirements_covered: [ADMIN-05, ADMIN-01, ANALYTICS-01, UI-05, UI-06]
requirements_deferred: [ADMIN-02, ADMIN-03, ADMIN-04, ADMIN-06, ADMIN-07, ADMIN-08, "ADMIN-09 (extended KPIs)"]
---

# Phase 8 — Verification (goal-backward)

Verified against the **lean-slice** goal the owner locked (08-CONTEXT D-01), not the full original
roadmap wording. Each lean criterion is delivered in real, tested code.

## Success criteria

1. **Roll back a bad prompt version without a redeploy (safety valve).** ✅ `prompt_templates`
   versions coexist (migration 0005, one active per slug); admin can create/activate/**roll back** a
   version live (`POST /api/admin/prompts/{slug}/versions` + `/activate`); the engine reads only the
   active row. Tested (8 integration tests incl. rollback + the partial-unique guard) + migration
   round-trip validated on real Postgres. *Full CRUD-UI over decks/cards/spreads/products =
   Deferred (owner: seed-JSON + redeploy).*
2. **Metrics dashboard.** ◑ Partial by design: the shipped `GET /api/admin/stats` + AdminScreen
   (users/readings/by-deck/topic/answer-style) satisfy the core of ADMIN-09; the extended KPIs
   (payment conversion, revenue, error-rate, avg latency) + browsable users/readings/payments/logs
   views (ADMIN-07/08) are **Deferred** — a solo founder queries the raw `app_events` + DB.
3. **Key events logged to `app_events`.** ✅ `record_event` + `POST /api/events` + FE `track()`; 11
   funnel events wired (opened → select → reading lifecycle → summary; paywall; product). Best-effort,
   never blocks the core flow (SEC-01 hardened). 4 finer events deferred as one-line follow-ons.
4. **Privacy-safe share-card + in-voice states.** ✅ Client-canvas share-card excludes the question
   by construction (UI-06, test-enforced); every empty/error/loading state renders in-voice copy and
   an app-level ErrorBoundary covers unexpected render errors (UI-05).
5. **Deployed over HTTPS + payments + legal.** ✅ deploy+payments already live (ЮKassa, 2 real
   purchases — supersedes the roadmap's "Stars" wording). The Phase-8 code deploy (migration 0005) is
   the coordinated deploy step. Legal/IP review of deck assets = owner task, documented.

## Evidence
- Backend 154 pass (+16 Phase-8 tests), ruff clean; migration 0005 round-trip clean on real PG.
- Frontend 130 pass, tsc clean, prod build clean (~125 kB gz).
- Gates: 08-SECURITY.md threats_open:0 (SEC-01 fixed); 08-REVIEW.md 0 critical / 1 HIGH fixed / 2 LOW
  advisory.

## Caveats (not gaps in Phase 8)
- 10 pre-existing integration failures (card_draw greenlet + migration/seed DuplicateTable) are a
  harness-isolation issue exposed by an incidental local Postgres; the user's no-Postgres environment
  skips them. Standing debt, tracked — not a Phase-8 regression.

## Result
Lean-slice goal **achieved**; deferrals are the owner's explicit scope choice (documented in CONTEXT
+ ROADMAP). Status: **passed**.
