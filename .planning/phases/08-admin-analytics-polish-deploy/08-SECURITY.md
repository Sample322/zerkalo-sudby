---
phase: 08-admin-analytics-polish-deploy
audited: 2026-07-07
depth: standard
auditor: inline (orchestrator — gsd-security-auditor subagent hits provider session limits)
threats_reviewed: 9
threats_open: 0
findings:
  high: 1
  medium: 0
  low: 0
resolution:
  fixed: [SEC-01]
  resolved_date: 2026-07-07
status: resolved
---

# Phase 8 — Security Audit

Scope: the Phase-8 attack surface — the admin prompt-version endpoints, the new `POST /api/events`
sink, migration 0005, the analytics writer, and the FE `track()`/share-card. One HIGH finding
(the events endpoint), fixed; everything else verified clean.

## Findings

### SEC-01 (HIGH) — `POST /api/events`: unbounded payload + no rate cap → authed DoS/bloat (FIXED)
**Surface:** `api/events.py`. The endpoint is JWT-gated, but `EventIn.properties` was an unbounded
JSONB dict and there was NO per-user rate cap, while `record_event` opens its OWN pooled DB
connection per call. An authenticated client could therefore (a) bloat `app_events` with huge
payloads and (b) burst the endpoint to exhaust the DB connection pool — starving the core reading /
payment requests. The best-effort swallow hides the *error* but not the *pool contention*.
**Fix (applied):** a per-user **fail-open** burst cap on its own `events` Redis bucket (60/60s;
`throttle_ok` gained a `bucket` param so it never shares the reading budget) — over-cap events are
silently dropped (202, never 429 a fire-and-forget call); a Redis outage fails OPEN (analytics must
not break the client). Plus `_bounded()` drops abusive `properties` (>20 keys or >2 KB) while still
recording the event name. Tests: `test_over_cap_event_is_dropped`, `test_throttle_error_fails_open`,
`test_bounded_drops_oversized_properties`.

## Verified clean (no finding)

- **Admin prompt endpoints** (`admin_prompts.py`): every route behind `require_admin` (server-side
  `ADMIN_TELEGRAM_IDS` allowlist, deny-by-default); inputs are Pydantic-validated (`extra="forbid"`);
  all DB access is ORM `select()`/`update()` (no string SQL → no injection); activation is atomic
  (deactivate-then-activate in one tx, existence-checked first so the 404 path mutates nothing) and
  the partial-unique index guarantees the "one active per slug" invariant can't be violated by a
  race. Admin-global data — no IDOR surface. Templates are DATA, never echoed as UI copy.
- **`POST /api/events` user scoping:** `user_id` is taken from the JWT subject ONLY; `EventIn` is
  `extra="forbid"` so a body-supplied `user_id` is rejected (422) — no spoofing (test-covered).
- **`record_event`:** own short-lived session, swallow-all, ORM insert, bare-UUID `user_id` (matches
  the §13.15 anonymous-capable, non-FK design). Cannot poison a caller's transaction.
- **Migration 0005:** additive + reversible; `DROP … IF EXISTS` for the single-column uniqueness,
  no data migration, no data loss. Round-trip validated on real Postgres.
- **FE `track()` / share-card:** `track` sends only non-PII slugs/enums and never the question; the
  share-card `ShareCardInput` has no `question` field, so the personal question can never leave the
  device or be drawn (UI-06 privacy, test-covered). `ErrorBoundary` shows in-voice copy and logs the
  stack to `console.error` only (never to the user).

## Result
1 HIGH found and fixed (SEC-01); **threats_open: 0**. Backend 154 pass, ruff clean.
