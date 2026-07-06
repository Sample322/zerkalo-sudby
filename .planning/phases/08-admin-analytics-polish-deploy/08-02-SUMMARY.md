---
phase: 08-admin-analytics-polish-deploy
plan: 02
title: Analytics into app_events (ANALYTICS-01)
status: complete
completed: 2026-07-07
requirements: [ANALYTICS-01]
---

# 08-02 — Analytics into `app_events` — SUMMARY

## What shipped
Product-funnel analytics into the already-existing `app_events` table (which had zero writers).

- **`services/analytics.py::record_event`** — best-effort writer: opens its OWN short-lived
  `SessionLocal` (never the caller's tx), inserts one row, commits, and swallows ALL errors; unknown
  names are dropped via `EVENT_ALLOWLIST`. Analytics can never slow or break the core flow.
- **`POST /api/events`** (`api/events.py` + `schemas/events.py`, Bearer): `user_id` from the JWT
  ONLY (`EventIn` is `extra="forbid"` — the body can't carry a user); allowlist-validated inside the
  helper; ALWAYS returns 202 (even for an unknown name or a write failure). Mounted at `/api`.
- **FE `api/events.ts::track()`** — fire-and-forget `apiFetch` POST, never awaited on a UI path,
  `.catch(()=>{})`. Properties are non-PII (slugs/enums/counts) — NEVER the question text.
- **11 funnel events wired** (best-effort): `reading_started` / `reading_completed` /
  `reading_failed` (in `createReading.ts`, from the response — the question is never sent),
  `app_opened` (FlowRoot), `summary_viewed` (ResultScreen), `history_opened` (HistoryScreen),
  `paywall_viewed` (PaywallSheet), `product_clicked` (ShopTariffs), `topic_selected` /
  `deck_selected` / `spread_selected` (CatalogScreen).

## Verification
- **Backend `uv run pytest`: 151 passed** (+8 new: `test_analytics_helper` — unknown-name no-op /
  valid-write / None-user / error-swallowed; `test_events_api` — 401 / 202+row / unknown→202+no-row /
  body-can't-spoof-user_id→422). Ruff clean.
- **Frontend `tsc -b` clean, `vitest run` 123 passed** (mocked the fire-and-forget `track` in
  `createReading.test.ts` + `HistoryScreen.delete.test.tsx` — the two files that assert exact fetch
  behaviour, so the extra `/api/events` call doesn't perturb them).

## Deviations / notes
- **No server-side emits + no Redis cap (deliberate, lean + zero money-path risk).** The RESEARCH
  suggested emitting reading/payment events server-inline; threading `record_event` through the
  reading service's many exit points and the payment grant (money path) was NOT trivial, so the
  whole funnel is emitted CLIENT-side via `track()`. Tradeoff: best-effort (a user who closes the app
  mid-flow won't emit the tail events) — acceptable for a solo-founder funnel, and it keeps the
  reading + payment paths completely untouched. The `/api/events` Redis burst-cap was also skipped
  (the endpoint is JWT-gated + best-effort); `throttle_ok` hardcodes the reading key so reuse would
  wrongly share that budget. Both are easy follow-on hardening.
- **Deferred events (each a one-line `track()` add):** `onboarding_started`/`onboarding_completed`,
  `question_entered`, `card_revealed`, `settings_changed`, and the authoritative server-side
  `payment_succeeded`/`subscription_started` (the webhook is the reliable source — worth adding when
  revenue analytics matter). The allowlist already includes them.
- 10 pre-existing integration failures (card_draw greenlet + migration/seed DuplicateTable) are
  unchanged — not from this plan (see 08-01-SUMMARY; incidental local Postgres, user env skips them).
