# Phase 8 — Discussion Log

**Date:** 2026-07-06 · Mode: discuss (default) · Human-reference only (not consumed downstream).

## Context at entry
Phase 8 = last roadmap phase ("Admin, Analytics, Polish & Deploy"). BUT the app is already LIVE:
deploy (both timeweb apps), ЮKassa payments (live + verified with 2 real purchases), and the
stats-dashboard (`GET /api/admin/stats` + AdminScreen) all shipped earlier. So criterion 5
(deploy+payments) and part of criterion 2 (metrics) are DONE — the roadmap text predates the D-01
Stars→ЮKassa pivot. Scope had to be re-cut around what's actually left, not the original wording.

## Areas presented
One scoping question — how much of the un-built admin surface to build now:
· **Full admin CRUD-UI** (rich editors for decks/cards/spreads/products) vs
· **Lean high-value slice** (safety-valve + analytics + share-card + polish; skip CRUD) vs
· **Minimal** (analytics + polish only).

## Turns & decisions

1. **Scope → «Lean high-value slice».** Owner selected the lean cut.
   - **Build:** (1) prompt-version safety-valve (quick-disable a bad generation prompt WITHOUT a
     redeploy), (2) analytics `app_events` (~15 funnel events, opened→reading→paywall→payment),
     (3) privacy-safe share-card (deck+3 cards+summary, EXCLUDES the question), (4) in-character
     empty/error/loading polish.
   - **Skip:** full admin CRUD-UI — the operator is technical + solo and edits seed JSON + redeploys
     (the loader upserts by slug, so a redeploy re-seeds; already proven with the 10₽ price change).
   - **Already done (don't rebuild):** deploy, payments (ЮKassa live), stats-dashboard.

## Grounding checks (codebase, this session)
- `app_events` table **already exists** (`models/analytics.py`, §13.15: user_id + event_name +
  event_properties JSONB) → analytics needs WRITERS, not a schema.
- `prompt_templates` exists with a versioning concept + `PromptEngine.build` composes by type →
  safety-valve gates on an active-version flag (migration if `is_active` absent).
- No `POST /api/events` yet → new thin client-event sink.
- `require_admin` + `AdminScreen` + `AdminStatsOut` exist → extend, don't rewrite.

## Net result
Lean Phase 8: prompt-version safety-valve · analytics-into-`app_events` (server-inline + a new
best-effort `POST /api/events`, writes NEVER block the core flow) · client-canvas privacy-safe
share-card · empty/error/loading gap-audit. Full CRUD-UI, browsable admin data views, server-side
share-image, and an extended KPI dashboard are explicitly **Deferred**. Decisions captured in
08-CONTEXT.md (D-01..D-05 + open research questions). Criterion-5 deploy+payments recorded as already
satisfied via the ЮKassa live-verification (supersedes the roadmap's Stars wording).
