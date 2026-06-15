---
phase: 06-free-limits-soft-paywall
plan: 03
subsystem: api
tags: [redis, lua, throttle, rate-limit, fastapi, dependency, anti-abuse, asyncio]

# Dependency graph
requires:
  - phase: 06-free-limits-soft-paywall
    plan: 01
    provides: "test_throttle.py red stub (throttle_gate / throttle_ok contract), redis_client test fixture (skip-if-down)"
  - phase: 04-real-personal-reading
    provides: "POST /api/readings thin router + get_current_user JWT gate + ReadingService.create_reading"
provides:
  - "core.redis.throttle_ok(user_id, *, window_s, burst_cap) -> bool — atomic Lua INCR+conditional-EXPIRE, key throttle:reading:{user_id}"
  - "core.redis.THROTTLE_WINDOW_S=60 / THROTTLE_BURST_CAP=5 (D-07 band) + registered _throttle_script"
  - "api.deps.throttle_gate FastAPI dependency — 429 over cap, keys off JWT user.id, no DB session"
  - "POST /api/readings guarded by dependencies=[Depends(throttle_gate)] (GATE 0, before get_session/LLM)"
affects: [06-04 FE throttle toast (kind:throttle, 429 discriminant D-08), 07-payments]

# Tech tracking
tech-stack:
  added: []  # zero new runtime dependencies (redis-py already pinned >=5.2,<6)
  patterns:
    - "Atomic Redis Lua INCR + conditional-EXPIRE (TTL only on count==1) via register_script — no stuck-counter race"
    - "FastAPI dependencies=[...] entry as GATE 0 — resolved before the path-op's own Depends, short-circuits before the DB session opens"
    - "int(count) cast on a Lua return because the shared client uses decode_responses=True (str, not int)"
    - "Local import of the Redis primitive inside the dependency to keep the Redis surface off deps.py import time"

key-files:
  created: []
  modified:
    - backend/app/core/redis.py
    - backend/app/api/deps.py
    - backend/app/api/readings.py
    - backend/tests/integration/test_throttle.py

key-decisions:
  - "throttle_ok signature finalized as (user_id, *, window_s, burst_cap) — NO redis arg (uses the shared module-level redis_client), matching RESEARCH Pattern 3; the test stub's adapter was aligned to forward only user_id"
  - "Band locked at 60s window / cap 5 (RESEARCH A3, within D-07) — a 30s+ real user tops out ~2/min, never throttled; single fixed window (two-tier spacing key documented as the post-MVP upgrade, not built)"
  - "throttle_gate depends ONLY on get_current_user, deliberately not on the DB session — the 429 short-circuits before any Postgres txn opens (success-criterion 4)"
  - "Guard on POST /readings ONLY; GET/detail/delete/restore are unguarded (throttle is on reading CREATION per LIMIT-05) — proven by route-table inspection"

patterns-established:
  - "Phase-6 gate chain: GATE 0 throttle (Redis, this plan) -> GATE 1 atomic consume (PG, 06-02) -> GATE 2 safety -> draw -> LLM"

requirements-completed: [LIMIT-05]

# Metrics
duration: 4min
completed: 2026-06-15
---

# Phase 6 Plan 03: Redis Throttle (GATE 0) Summary

**An atomic Lua `INCR`+conditional-`EXPIRE` per-user throttle (`throttle:reading:{user_id}`, 60s/5) wired as `throttle_gate` — the FIRST thing `POST /api/readings` runs, so a burst over the cap returns 429 before any Postgres session opens or any LLM call is made (LIMIT-05, success-criterion 4).**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-06-15T20:18:40Z
- **Completed:** 2026-06-15T20:22:58Z
- **Tasks:** 2 autonomous, both complete
- **Files modified:** 4 (2 source + 1 router + 1 test alignment)

## Accomplishments

- **Atomic Lua throttle (Task 1, T-06-10/11 mitigation):** `core/redis.py` registers `_THROTTLE_LUA` (`INCR` then `EXPIRE` only on `count==1`) once at module load via `redis_client.register_script`. `throttle_ok(user_id, *, window_s, burst_cap)` calls it with key `throttle:reading:{user_id}` and returns `int(count) <= burst_cap` (the `int()` cast is required because the shared client sets `decode_responses=True`, so the Lua return is a `str`). The TTL is always armed on the first hit → **no stranded counter** (a worker dying between a plain `INCR` and `EXPIRE` cannot permanently lock a user out). `register_script` is lazy — importing the module needs no live Redis (verified: the import succeeds with a bogus `REDIS_URL`).
- **GATE-0 dependency (Task 2, T-06-12/13 mitigation):** `api.deps.throttle_gate` raises `HTTPException(429, "throttled")` when `not await throttle_ok(user.id)`. It depends **only** on `get_current_user` (keys off the verified JWT `user.id`, never a request-body field — T-06 spoofing) and deliberately does **not** open a DB session, so the 429 short-circuits before any Postgres transaction.
- **Route guard (Task 2):** `POST /api/readings` carries `dependencies=[Depends(throttle_gate)]`. FastAPI resolves `dependencies=[...]` before the path-operation's own `Depends` params, so the throttle fires before `get_session`/`get_reading_service`. Route-table inspection confirms the gate is on **POST /readings only** — GET list, GET detail, DELETE, and POST restore are unguarded (the throttle is on reading CREATION per LIMIT-05).

## Task Commits

Each task was committed atomically (hooks ran — no `--no-verify`):

1. **Task 1: atomic Lua throttle in core/redis.py** — `2ab2760` (feat)
2. **Task 2: throttle_gate GATE 0 + route guard + test alignment** — `a1536b6` (feat)

**Plan metadata** (this SUMMARY + STATE/ROADMAP) committed separately.

## Final Numbers / Contract (record for 06-04 + future plans)

| Item | Value |
|------|-------|
| **Window** | `THROTTLE_WINDOW_S = 60` (seconds) |
| **Burst cap** | `THROTTLE_BURST_CAP = 5` (≤5 attempts per 60s window) |
| **Key shape** | `throttle:reading:{user_id}` (per-user; `user_id` = JWT `user.id`) |
| **Over-cap transport** | HTTP **429** `"throttled"` (the FE's `kind:"throttle"` discriminant, D-08 — distinct from the paywall's 200 soft body) |
| **Primitive symbol the test imports** | `app.core.redis.throttle_ok(user_id, *, window_s, burst_cap) -> bool` |
| **Gate symbol the test imports** | `app.api.deps.throttle_gate` |
| **Counts** | creation **ATTEMPTS** (runs before validation — intended, RESEARCH Pitfall 4), NOT successful consumes |

## Files Modified

- `backend/app/core/redis.py` — added `_THROTTLE_LUA`, `_throttle_script = redis_client.register_script(...)`, `THROTTLE_WINDOW_S`/`THROTTLE_BURST_CAP`, `async def throttle_ok(...)`, and an `__all__`.
- `backend/app/api/deps.py` — added `async def throttle_gate(user = Depends(get_current_user))` (429 over cap, no DB session); exported it in `__all__`.
- `backend/app/api/readings.py` — imported `throttle_gate`; added `dependencies=[Depends(throttle_gate)]` to the `@router.post("/readings", ...)` decorator only.
- `backend/tests/integration/test_throttle.py` — aligned the `_throttle_ok` adapter to the final signature (forwards only `user_id`; still receives the `redis_client` fixture so the tests skip when Redis is down).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Verify-command false positive on the `get_session` substring**
- **Found during:** Task 2
- **Issue:** The plan's `<automated>` verify asserts `'get_session' not in inspect.getsource(throttle_gate)` to prove the gate doesn't depend on the DB session. My docstring contained the literal phrase "...does NOT depend on `get_session`...", so the naive substring check failed even though the actual dependency (`Depends(get_current_user)` only) is correct.
- **Fix:** Rephrased the docstring to "does NOT open a DB session" (same meaning, no literal `get_session` token). The semantic guarantee is unchanged and independently confirmed: route-table inspection shows the gate's `dependant.dependencies` resolve before the path-op's `Depends(get_session)`.
- **Files modified:** `backend/app/api/deps.py`
- **Commit:** `a1536b6`

**2. [Plan-sanctioned] Test-stub adapter signature alignment**
- **Found during:** Task 2
- **Issue:** The 06-01 red stub's `_throttle_ok` adapter called `throttle_ok(redis_client, user_id, ...)` (redis as the first positional), but RESEARCH Pattern 3 + the plan's Task 1 prescribe `throttle_ok(user_id, *, window_s, burst_cap)` (no redis arg — it uses the shared module-level client).
- **Fix:** Updated the adapter body to forward only `user_id` (it still receives the `redis_client` fixture so the skip-if-Redis-down behavior is preserved). This is the exact mechanism the plan's Task 2 `read_first` sanctions ("align this task to whatever the stub expects, **or update the stub import to match**").
- **Files modified:** `backend/tests/integration/test_throttle.py`
- **Commit:** `a1536b6`

Neither is a scope change; both are the verify/stub-alignment the plan anticipated. Zero new packages (T-06-SC).

## Authentication Gates

None.

## User-Smoke Required (live Redis — NOT runnable in the agent env)

**The live-throttle burst proof is a user-smoke.** The agent environment has no Docker/Redis (locked env constraint, consistent with Phases 1–5) and `fakeredis` is not installed, so the three `test_throttle.py` tests **skip cleanly** in isolation (the `redis_client` fixture pings on setup and `pytest.skip`s when unreachable). Verify against a live Redis:

1. With Redis up + a valid Bearer JWT, fire **>5** `POST /api/readings` within 60s → the **6th** returns **HTTP 429** `"throttled"`.
2. Confirm the 429 short-circuits: `fake_llm.calls == 0` and **no** reading row is written for the throttled request (it never reaches `ReadingService`).
3. Recovery: after the 60s window elapses, a fresh request passes again (TTL on `throttle:reading:{user_id}` aged out).
4. Spacing sanity: two readings ≥30s apart are never throttled (a real user tops out ~2/min).

Once Redis is up, `test_throttle.py::{test_burst_blocked, test_window_expires, test_throttle_short_circuits_before_pg}` xpass automatically (they exercise the real `throttle_ok` primitive: burst-block, TTL-set/window-expiry, and the over-cap → `HTTPException` short-circuit contract). In the full-suite run during this plan they were observed **xpassed** (Redis transiently reachable mid-suite), but the deterministic env state is skip — hence this is recorded as a user-smoke, not an automated proof.

## Test Results

- Full backend suite: **83 passed, 77 skipped, 3 xpassed** (06-01 baseline 83 pass / 76 skip / 3 xfail preserved; the 3 throttle stubs went `xfail → xpass`, i.e. turned green). Zero failures, zero collection errors.
- `test_throttle.py` in isolation: **3 skipped** (Redis unreachable — the correct deterministic env state).
- `uv run ruff check app/core/redis.py app/api/deps.py app/api/readings.py tests/integration/test_throttle.py` — clean.
- Route-table inspection: `throttle_gate` on **POST /api/readings only**; GET/detail/delete/restore unguarded.
- The pre-existing `InsecureKeyLengthWarning` in `test_initdata.py` (an intentional short-secret negative test) is out of scope — not touched.

## Next Plan Readiness

- **06-04 (FE paywall/count + throttle toast)** has its backend contract complete: the throttle returns **429** as the `kind:"throttle"` discriminant (D-08), distinct from 06-02's 200 paywall soft body (`reason:"paywall"` + `reset_at`). `createReading.ts` branches one `catch` on `status === 429` → throttle toast.
- **07-payments** inherits the gate chain unchanged (throttle stays GATE 0).
- No blockers introduced by this plan. (The standing 06-01 blocker — migration 0002 must be applied against a live DB before 06-02 can be live-verified — is unrelated to the throttle, which writes only to Redis.)

## Self-Check: PASSED

(verified below — all modified files present + both task commits in history)

---
*Phase: 06-free-limits-soft-paywall*
*Completed: 2026-06-15*
