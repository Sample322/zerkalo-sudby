---
phase: 06-free-limits-soft-paywall
reviewed: 2026-07-06
depth: standard
files_reviewed: 4
files_reviewed_list:
  - backend/app/core/redis.py
  - backend/app/api/deps.py
  - frontend/src/components/ThrottleToast.tsx
  - frontend/src/reading/createReading.ts
findings:
  critical: 0
  warning: 2
  info: 0
  total: 2
status: resolved
resolution:
  fixed: [WR-01, WR-02]
  resolved_date: 2026-07-06
  commit: 13cdfed
---

# Phase 6: Code Review Report

**Reviewed:** 2026-07-06 · **Depth:** standard · **Files:** 4 · **Status:** resolved (both fixed)

**Note:** authored inline by the orchestrator — the `gsd-code-reviewer` subagent hit provider session
limits repeatedly (P5 too), so the P6 review was done inline. Scope: the Phase-6-distinctive
un-reviewed surface — the Lua throttle (`redis.py`), its gate (`deps.py:throttle_gate`), the throttle
toast, and the FE error discriminant. The atomic consume-gate + `determine_access` in `reading.py`
were covered under Phase 4/7 reviews (04/07-REVIEW.md) and the security dimension by 06-SECURITY.md
(18/18, incl. the atomic INCR+conditional-EXPIRE) — not re-litigated here.

## Summary

The Lua throttle (atomic `INCR` + conditional-`EXPIRE`, no stranded-counter race) and the FE error
discriminant (429→throttle, 200+`reason=paywall`→paywall+resetAt, else→failure) are correct. Two
genuine defects — one a real live-availability risk — both fixed.

## Warnings

### WR-01: `throttle_gate` fails CLOSED on a Redis outage → 500s every reading create (FIXED)

**File:** `backend/app/api/deps.py:76-89`
**Issue:** `throttle_gate` called `if not await throttle_ok(user.id): raise 429`. When Redis is
unreachable, `throttle_ok` (`_throttle_script(...)`) RAISES a connection error that propagates
uncaught → a 500 on **every** `POST /api/readings`. The throttle is a best-effort anti-abuse burst
cap — NOT a hard gate — and the weekly free limit is PG-authoritative (enforced downstream in the
consume-gate), so a Redis blip should degrade the burst cap, not take down the core reading flow. This
is a real live-availability risk (the managed Redis at `…:6379` blipping would 500 all readings until
recovery) — and is exactly why the local `test_readings_auth` suite 500s when local Redis is down.
**Fix (applied):** `throttle_gate` wraps `throttle_ok` in try/except and fails OPEN on any error
(logs `throttle_unavailable_fail_open`, allows the reading). No quota bypass — the weekly limit still
enforces. + a no-Redis fail-open test (`test_throttle_gate_fails_open_on_redis_error`).

### WR-02: ThrottleToast auto-dismiss timer resets on every parent re-render (FIXED)

**File:** `frontend/src/components/ThrottleToast.tsx:35-39`
**Issue:** The ~3.75s auto-dismiss `useEffect` depended on `[open, onDismiss]`; `CatalogScreen`
passes a non-memoized inline `onDismiss`, and the create-reading flow re-renders CatalogScreen
frequently, so the timer was cleared + re-armed on each render — measuring the window from the last
render rather than from open (the same class as the P5 UndoSnackbar WR-01; the file's own comment
says it "reuses the UndoSnackbar pattern"). Minor UX (the toast could linger), no data impact.
**Fix (applied):** ref the latest `onDismiss` so the timer effect depends only on `open` — armed once
per open, independent of parent memoization.

## Info

None — the Lua throttle and `createReading` discriminant were clean.

---

_Reviewed inline: 2026-07-06 · both warnings fixed same-day (13cdfed)._
