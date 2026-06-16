---
status: partial
phase: 06-free-limits-soft-paywall
source: [06-VERIFICATION.md]
started: 2026-06-15
updated: 2026-06-15
---

## Current Test

[awaiting human testing — all require live infrastructure absent from the build environment: Postgres, Redis, and the deployed Telegram Mini App]

## Tests

### 1. Apply migration 0002 against a live database (06-01 Task 4 — BLOCKING)
expected: `cd backend && uv run alembic upgrade head` applies without error; `uv run alembic current` shows `0002_user_limits_rolling_window`. In psql `\d user_limits`: `week_start` is `timestamp with time zone`; `uq_user_limits_user_id` is a UNIQUE constraint. Pre-existing ISO-Monday `DATE` rows survived as midnight `timestamptz` (not NULL, not errored). `uv run alembic downgrade -1` then `upgrade head` succeeds (reversible).
result: [pending]

### 2. Concurrent boundary atomicity — no over-spend (LIMIT-03, success-criterion 3)
expected: against a live DB, two concurrent `POST /api/readings` for the same user at the limit boundary (used=2, limit=3) → exactly ONE completes, the other gets the soft paywall body; `free_used_this_week` never exceeds `free_weekly_limit`. (The `test_limit_concurrency` two-committed-session test xpasses once Postgres is available.)
result: [pending]

### 3. Weekly reset + 4th-reading paywall (LIMIT-01/LIMIT-02)
expected: after 3 completed free readings in a window, the 4th is blocked with the soft paywall (HTTP 200 soft body, `reason="paywall"` + `reset_at` = first-reading + 7 days); the counter resets only when `now ≥ week_start + 7d` (per-user rolling, D-01) — a fresh-but-exhausted window still blocks. A user at the boundary gets exactly 3 per window, not extra.
result: [pending]

### 4. Live Redis throttle burst (LIMIT-05, success-criterion 4)
expected: against live Redis, firing >5 reading requests within ~60s trips HTTP 429 on the 6th BEFORE any DB session / LLM call (no draw, no consume); a normal-paced user (readings 30s+ apart) is never throttled; the counter always gets a TTL (no stuck-counter lockout); recovery after the window.
result: [pending]

### 5. Three FE surfaces in the real Telegram Mini App (06-04 Task 4 — BLOCKING)
expected: in a deployed build with a live exhausted-limit state —
- **Paywall (D-03/D-04):** tapping «Начать расклад» on the 4th surfaces the soft bottom-sheet — headline «На этой неделе бесплатные расклады закончились», an accent-tinted countdown («вернутся через N дней» / a date), the «скоро ещё» note, NO «buy»/price/Stars, NO red/alarm hue; dismissing preserves the question + selections.
- **Count (D-09/D-10):** «Осталось N из 3» shows quietly near the CTA at 2 and 3 left; the accent «Последний расклад на этой неделе» hint at exactly 1 left; suppressed at 0 (the sheet carries it); the free-count block appears in the profile.
- **Throttle (D-08):** rapid requests (>5/60s) trip the transient «Колода переводит дыхание…» toast — auto-dismisses (~3.75s), visibly DIFFERENT from the persistent paywall sheet; a normal-paced retry works.
result: [pending]

### 6. Brand-voice scan on the new surfaces (SAFE-06 / TZ §11.2)
expected: no «AI / ИИ / нейросеть / модель / сгенерировано ИИ» and no fear/pressure/«приговор» copy anywhere on the paywall sheet, throttle toast, or count surfaces (the headless `copy.test.ts` ban-list already passes; this is the live visual confirmation).
result: [pending]

## Summary

total: 6
passed: 0
issues: 0
pending: 6
skipped: 0
blocked: 0

## Gaps
