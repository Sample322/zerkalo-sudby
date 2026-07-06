---
phase: 08-admin-analytics-polish-deploy
reviewed: 2026-07-07
depth: standard
reviewer: inline (orchestrator — gsd-code-reviewer subagent hits provider session limits)
files_reviewed: 11
findings:
  critical: 0
  high: 1
  medium: 0
  low: 2
  total: 3
status: resolved
resolution:
  fixed: [SEC-01]
  advisory: [LOW-01, LOW-02]
  resolved_date: 2026-07-07
---

# Phase 8 — Code Review

Reviewed the Phase-8 diff (safety-valve, analytics, share-card, polish). One HIGH (SEC-01, also the
security finding) — fixed. Two LOW advisories, non-blocking. No CRITICAL.

## HIGH (fixed)
- **SEC-01** — `POST /api/events` unbounded payload + no rate cap (authed DoS/bloat). Fixed: fail-open
  per-user `events`-bucket cap + bounded `properties`. Full detail + tests in `08-SECURITY.md`.

## LOW (advisory, not fixed)
- **LOW-01** — analytics double-count: `topic_selected`/`deck_selected`/`spread_selected` fire on
  every tap (including re-selecting the same value), and `summary_viewed` refires on a
  result→readingDetail transition. Best-effort funnel signal; a small over-count is acceptable and
  cheaper than de-duping. No data/UX impact.
- **LOW-02** — share-card `deckName`/`spreadName` read `reading.deckSlug`/`spreadSlug`, which hold the
  RU display titles for live readings but may hold the raw slug for a reopened OLD past reading whose
  meta predates the title-in-meta change. Cosmetic only (the share image would show a slug); privacy
  and function are unaffected. Fix if/when old readings are re-mapped.

## Verified clean
- Admin endpoints: `require_admin` on all routes, ORM (no injection), atomic activation with the
  partial-unique invariant as backstop, existence-check-before-mutate on the 404 path.
- `record_event`: own session, swallow-all, never poisons the caller tx (the core best-effort rule).
- Migration 0005: additive/reversible, round-trip validated on real Postgres.
- Share-card privacy invariant (no `question` field) is type- and test-enforced.
- ErrorBoundary logs to `console.error` for diagnostics only (acceptable for a boundary); the user
  sees in-voice copy. `track()` is fire-and-forget and swallows errors everywhere.

## Result
0 CRITICAL, 1 HIGH (fixed), 2 LOW (advisory). Backend 154 pass + ruff clean; frontend 130 pass +
tsc + prod build clean. Status: **resolved**.
