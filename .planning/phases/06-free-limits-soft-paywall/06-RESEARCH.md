# Phase 6: Free Limits & Soft Paywall - Research

**Researched:** 2026-06-15
**Domain:** Concurrency-safe quota accounting (PostgreSQL atomic conditional UPDATE) + Redis fixed-window throttle, on FastAPI + SQLAlchemy 2.0 async + asyncpg + redis-py async
**Confidence:** HIGH (core mechanics verified against official SQLAlchemy/redis-py docs + the live codebase seam)

## Summary

This phase is a **backend correctness phase wearing a small frontend hat**. The UI contract is fully locked in `06-UI-SPEC.md` (approved): three surfaces (paywall sheet, throttle toast, remaining-count line), zero new dependencies, all copy in `copy.ts`. The real risk surface — and the entire focus of this research — is the backend's **atomic check+decrement under concurrency**, the **lazy race-safe rolling reset**, and the **Redis throttle as the first gate**. All three already have a Phase-4 seam to extend: `ReadingService._get_limits / _has_quota / _consume_limit` and the locked `create_reading` order (`limit check → safety → draw → … → consume`).

The single most important output is the atomicity mechanism. The recommendation is a **single conditional `UPDATE … WHERE free_used_this_week < free_weekly_limit … RETURNING free_used_this_week`** that **folds the lazy 7-day reset INTO the same statement via SQL `CASE` expressions**. This makes reset+check+increment+re-anchor one indivisible round-trip — no read-then-maybe-reset-then-decrement TOCTOU window can double-spend or mis-reset. PostgreSQL takes a row lock for the duration of the UPDATE, so two concurrent requests at the boundary serialize: exactly one matches the WHERE and increments; the other matches zero rows (`scalar_one_or_none() → None`) → paywall. This is verified-correct, lock-free of application code, and needs no `SELECT … FOR UPDATE`.

**Two findings contradict the CONTEXT "no schema change expected" assumption and must be surfaced to the planner (see Assumptions Log + Open Questions):** (1) `user_limits.week_start` is a `DATE` column (`sa.Date()`), but D-01's rolling window with re-anchoring (`week_start = now`, check `now − week_start ≥ 7d`) needs sub-day precision — a `DATE` truncates time-of-day and makes the reset day-granular. (2) The existing integration-test isolation runs all sessions over **one connection via SAVEPOINTs**, which cannot exercise true cross-connection DB row-lock concurrency — the boundary-race test needs a distinct fixture. Both are addressable; neither blocks planning.

**Primary recommendation:** Extend `ReadingService`'s limit seam (do **not** add a separate `LimitService`) with one `_consume_free_atomic()` helper issuing the fold-the-reset conditional `UPDATE…RETURNING`; add a Redis Lua `INCR`+conditional-`EXPIRE` throttle as a new first gate before the safety classifier; keep PostgreSQL authoritative (no Redis count cache this phase). Migrate `week_start` `DATE → TIMESTAMP(timezone=True)`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Free weekly limit = **per-user rolling 7-day window**, anchored at the **first reading of each window** (`week_start` = timestamp of the first reading after a reset), NOT a fixed ISO-Monday calendar week. **Deliberately OVERRIDES ROADMAP success-criterion-2's "ISO week, UTC".** Reset is **lazy-on-read**: on the next reading request, if `now − week_start ≥ 7 days`, reset `free_used_this_week = 0` and re-anchor `week_start = now`. NO cron (no queue, edit #2). **[Verifier note: do NOT flag against criterion-2's "ISO week" — it is a deliberate, user-approved override.]**
- **D-02:** Every user gets a `user_limits` row **at auth (user upsert)** — default `free_weekly_limit = 3`, `free_used_this_week = 0`, `week_start = NULL` (anchors on first reading). Fixes the Phase-4 "no row → unlimited" gap.
- **D-03:** On exhaustion the paywall shows **"бесплатные расклады закончились + вернутся через N" + a soft "скоро можно будет открыть ещё" note** — NO tariffs, NO dead "buy" buttons (payments are Phase 7). Copy anchored in TZ §9.8 / §11.2.
- **D-04:** Paywall shows a **reset countdown** (days or date). Especially important under per-user rolling (D-01) where the reset moment differs per user.
- **D-05:** Paywall **form = inline / bottom-sheet on the selection screen** — NOT a dedicated full tariffs screen (TZ §9.7 deferred to Phase 7).
- **D-06:** `determine_access(limits)` consumes buckets in order **free → subscription → paid_balance** — spend expiring buckets first, preserve permanent `paid_spreads_balance` last. Seam built in Phase 6, but only `free` is ever populated here (paid/subscription = 0 until Phase 7).
- **D-07:** Redis throttle = **moderate (~1 reading / 10–15 s + a short-window burst cap, e.g. ≤ 5 / min)** via `INCR` + `EXPIRE` per-user key. **FIRST gate** — before the limit check and before Postgres/LLM. Exact window/cap is the planner's within this band.
- **D-08:** **Distinct messages** for throttle vs limit-exhaustion: throttle → soft transient "колода переводит дыхание" (HTTP 429, retryable); limit → the paywall (D-03). Never conflate.
- **D-09:** Show the **remaining free count** ("осталось N из 3") subtly near «Начать расклад» AND in the profile. Un-hides the Phase-5 D-08 count block. Sourced from `GET /api/me` `limits`.
- **D-10:** Prominence = **subtle always + a gentle "последний на этой неделе" hint when 1 remains**. No pressure/alarm.

### Claude's Discretion

- Exact reset / throttle / paywall copy (TZ §9.8 + §11.2; the «скоро» note) — brand-safe (no «AI/нейросеть/модель»), via `copy.ts`.
- **Atomicity mechanism** for check+decrement (`SELECT … FOR UPDATE` vs atomic `UPDATE … WHERE … RETURNING`) — success-criterion 3 "no over-spend under concurrency".
- Exact throttle window / burst-cap numbers within the D-07 band; the `INCR`+`EXPIRE` key shape.
- Lazy-reset placement (in the limit seam before the consume); `LimitService` vs extend `ReadingService`.
- Whether to cache the count in Redis vs always read PG (PG authoritative).

### Deferred Ideas (OUT OF SCOPE)

- Telegram Stars purchase flow (invoice → `successful_payment` → grant), populating `paid_spreads_balance` + subscription buckets, the real tariffs screen (TZ §9.7) — **Phase 7**.
- A dedicated full paywall/tariffs screen — Phase 7 (Phase 6 is inline/sheet, D-05).
- Heavier anti-abuse (per-IP throttle, CAPTCHA, device fingerprint) — out of MVP scope.
- Caching the remaining count in Redis as the read path — optional optimization; PG stays authoritative.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LIMIT-01 | Бесплатный лимит 3 расклада/неделя per-user (`user_limits`) | Row guaranteed at auth (D-02, `_ensure_user_limits` already exists — adjust `week_start=NULL`); `free_weekly_limit=3` default already on the model + migration 0001. Paywall body returned by the existing `_soft_body`. |
| LIMIT-02 | Недельный лимит сбрасывается (`week_start`) | Lazy rolling-7-day reset folded into the conditional UPDATE via `CASE` (Pattern 2). **Requires `week_start` `DATE→TIMESTAMP` migration** (see Open Q1). |
| LIMIT-03 | Перед раскладом проверяется доступ (free/paid/subscription); при исчерпании — мягкий paywall | `determine_access` bucket function (Pattern 4) + the atomic conditional UPDATE (Pattern 1). 0-rows-matched → paywall. |
| LIMIT-04 | Платные из `paid_spreads_balance`, подписочные из subscription-лимита; бесплатные отдельно | `determine_access` returns the bucket to spend; only `free` non-zero this phase. Phase-4 `_consume_limit` already has the free/paid/subscription branch shape to generalize. |
| LIMIT-05 | Anti-abuse/rate-limit через Redis (атомарный throttle на создание раскладов) | Redis Lua `INCR`+conditional-`EXPIRE` throttle, first gate before PG/LLM (Pattern 3). redis-py async `register_script`. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

These have the same authority as locked decisions — research recommendations never contradict them:

- **PG-authoritative quota:** weekly limit source of truth in Postgres `user_limits` (`free_used_this_week`, `week_start`); Redis is a **fast counter/cache only**. (→ this phase keeps PG authoritative; Redis is used ONLY for the throttle, not as the count read-path.)
- **Throttle = `INCR` + `EXPIRE` per-user short-window key.** Explicitly named the mechanism.
- **NO Celery/RQ/Arq** (edit #2) — no cron for the reset; reset MUST be lazy-on-read. (D-01 already encodes this.)
- **Limit checks backend-only** (TZ §29.2) — the frontend count line is display-only; the gate is server-side.
- **Throttle before Postgres** (TZ §29.2 / success-criterion 4).
- **Brand voice:** no «AI / нейросеть / модель / сгенерировано» in any copy (SAFE-06). All new strings in `frontend/src/reading/copy.ts` (scanned by `copy.test.ts`).
- **SQLAlchemy 2.0 `select()`/`update()` + `AsyncSession` + `Mapped[]`** — never legacy `Query`. Pydantic v2 idioms (`from_attributes`, `model_dump`).
- **Backend coding style (python rules):** thin router → service; functions <50 lines; explicit error handling; type annotations on all signatures.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Atomic free-quota check+decrement | Database (PostgreSQL) | API/service (`ReadingService`) | Correctness under concurrency belongs to the DB's row-lock + a conditional WHERE — not application-side compare. PG is the locked source of truth. |
| Lazy 7-day rolling reset | Database (single UPDATE `CASE`) | API/service | Folding the reset into the same atomic statement is the only TOCTOU-free placement; the service decides *when* to call it (first gate after throttle). |
| Burst/rapid-fire throttle | Redis (in-memory, Lua atomic) | API/service (first gate) | Sub-second counter that must reject *before* any PG/LLM work — Redis is the right tier (CLAUDE.md). Ephemeral, not authoritative. |
| Bucket selection (free→sub→paid) | API/service (`determine_access`) | — | Pure business policy over the loaded row; no tier below needs to know the order. |
| `user_limits` row creation | Database (ON CONFLICT) | API/service (auth) | Race-safe row-ensure is a DB upsert; the auth service is the placement. |
| Remaining-count display | Frontend (read `GET /api/me`) | — | Pure presentation; the count is non-authoritative chrome (D-09). |
| Error transport (throttle vs paywall vs failure) | API (status codes + body shape) | Frontend (discriminates) | The backend owns the discriminant; the FE branches one `catch` (06-UI-SPEC). |

## Standard Stack

**No new runtime dependencies.** Every mechanic uses libraries already pinned in `backend/pyproject.toml`. This is a deliberate, verified outcome (matches the UI-SPEC "zero new dependency" finding).

### Core (already pinned — versions verified on PyPI 2026-06-15)

| Library | Pinned | Latest | Purpose | Why Standard |
|---------|--------|--------|---------|--------------|
| SQLAlchemy (async) | `2.0.*` | 2.0.50 `[VERIFIED: PyPI]` | `update().where().values(case(...)).returning()` for the atomic consume | 2.0 Core async is the locked ORM; conditional UPDATE…RETURNING is the canonical atomic-decrement idiom `[CITED: docs.sqlalchemy.org/en/20/tutorial/data_update.html]` |
| asyncpg | `0.31.*` | 0.31.0 `[VERIFIED: PyPI]` | PG driver; supports "sane rowcount" for plain UPDATE, RETURNING rows for the consume | Fastest async PG driver; rowcount semantics confirmed (see Pattern 1 caveat) |
| redis-py | `>=5.2,<6` | 8.0.0 (pin stays <6 by design) `[VERIFIED: PyPI]` | `register_script` Lua throttle + `INCR`/`EXPIRE` on `redis.asyncio` | Async client; `register_script` is a long-stable API `[CITED: redis.readthedocs.io/en/stable/lua_scripting.html]`. **Pin `<6` is intentional** (avoids redis-py 8.0 RESP3 default — see `app/core/redis.py` docstring). |
| PostgreSQL | `16.x` | — | Row-level lock during UPDATE serializes boundary races | Default-isolation `UPDATE…WHERE` takes a row lock; concurrent writers block then re-evaluate — the mechanism that makes Pattern 1 correct |

### Supporting (already present)

| Library | Pinned | Purpose | When to Use |
|---------|--------|---------|-------------|
| Pydantic | `2.13.*` | If a typed limit-block response field (`reset_at`) is added to `ReadingOut` | Only if extending the response schema for the FE countdown (see Error Transport) |
| pytest + pytest-asyncio | `>=8` / `>=0.24` | `asyncio.gather` two `create_reading` at the boundary; reset/throttle/bucket tests | `asyncio_mode = "auto"` already set in `pyproject.toml` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Conditional `UPDATE…WHERE…RETURNING` (Pattern 1) | `SELECT … FOR UPDATE` + app-side check + `UPDATE` | FOR UPDATE works but needs 2 round-trips, holds the lock across a Python await (longer lock window), and re-implements in app code what one WHERE does atomically. **Rejected** — more code, more lock contention, same guarantee. |
| Lua `INCR`+conditional-`EXPIRE` throttle (Pattern 3) | Plain `INCR` then `EXPIRE` (two awaits) | The two-call form has a real race: if the process dies between `INCR` and `EXPIRE`, the key never expires → a user is throttled forever (a "stuck counter"). `[VERIFIED: redis.io + dev.to]` MULTI/EXEC can't branch on `count==1`. Lua is the documented fix. A simpler **idempotent fallback** (pipeline `INCR`+`EXPIRE`-every-call) is acceptable (re-arms TTL each call; never stuck) — document as the fallback if Lua is deemed heavy. |
| Extend `ReadingService` | New `LimitService` | A separate service splits the transaction owner from the limit logic that must run inside `create_reading`'s session/order. The Phase-4 `_get_limits/_has_quota/_consume_limit` seam is already there. **Rejected** — extend in place (D-discretion resolved: extend). |
| `week_start` `TIMESTAMP` migration | Keep `DATE`, reset at day-granularity | Keeping `DATE` makes "7 days from your first reading" actually "7 calendar-day-boundaries", and re-anchoring loses the hour — the countdown (D-04) would be imprecise and a user reading at 23:00 then 00:01 two days later mis-counts. **Migrate** (see Open Q1). |

**Installation:** none — `backend/pyproject.toml` already pins every library. No `pip install` step in any task. Confirm at plan time with `uv run python -c "import redis.asyncio, sqlalchemy, asyncpg"`.

**Version verification (2026-06-15, `pip index versions`):** sqlalchemy 2.0.50 (pin `2.0.*` ✓), asyncpg 0.31.0 (pin `0.31.*` ✓), redis 8.0.0 available but pin `>=5.2,<6` holds by design ✓.

## Package Legitimacy Audit

> **Not applicable — zero external packages installed this phase.** Every library used is already in the locked `pyproject.toml` (human-approved at prior Package-Legitimacy checkpoints, per the inline comments in the file: anthropic/tenacity/aiogram all slopcheck-[OK] + PyPI-confirmed). No new `pip install`, no new registry fetch. slopcheck not run because no new package is introduced; if the planner adds any package (it should not need to), gate it behind `checkpoint:human-verify`.

| Package | Registry | Disposition |
|---------|----------|-------------|
| *(none — no new packages)* | — | N/A |

## Architecture Patterns

### System Architecture Diagram (the reading-create gate chain, Phase-6 extension)

```
POST /api/readings  (createReading mutation; user = JWT sub, never body)
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  GATE 0 — REDIS THROTTLE  (NEW first gate, D-07/LIMIT-05)        │
│  Lua: c = INCR(throttle:{user_id}); if c==1 EXPIRE(key, window) │
│  c > burst_cap?  ──► 429 {kind:"throttle"}  (NO PG, NO LLM)      │
└─────────────────────────────────────────────────────────────────┘
        │ within band
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  ReadingService.create_reading  (owns the AsyncSession txn)     │
│                                                                 │
│  GATE 1 — ATOMIC FREE CONSUME + LAZY RESET  (D-01/02/03, L-02/03)│
│   determine_access(limits) picks the bucket (free→sub→paid)     │
│   free bucket ►  one UPDATE user_limits                         │
│     SET free_used = CASE WHEN stale THEN 1 ELSE free_used+1 END,│
│         week_start = CASE WHEN stale OR NULL THEN now ELSE ws   │
│     WHERE user_id=:id                                            │
│       AND (stale OR week_start IS NULL                           │
│            OR free_used < free_weekly_limit)                     │
│     RETURNING free_used_this_week, free_weekly_limit            │
│   row is None (0 matched) ─► soft paywall body + reset_at       │
│                              {kind:"paywall"}  (NO draw)         │
│        │ row returned (consumed)                                 │
│        ▼                                                         │
│  GATE 2 — SAFETY (unchanged Phase-4)  crisis/abusive ─► refusal │
│        │  (NOTE: consume now precedes draw — see Pitfall 4)      │
│        ▼                                                         │
│  CSPRNG draw → persist pending → PromptEngine → ONE LLM call    │
│        │  honest-fail ─► status=failed + REFUND the consume      │
│        ▼                                                         │
│  persist output → status=completed → commit → ReadingOut        │
└─────────────────────────────────────────────────────────────────┘

GET /api/me  limits ──► FE remaining-count line (display only, D-09)
```

**Critical ordering change vs Phase 4:** Phase 4 consumes the limit LAST (success-only, after generation). Phase 6's atomic-consume-then-maybe-refund flips this: the atomic UPDATE is the *gate* (it must decide "got a slot?" atomically before the draw). This means **a non-success exit after the consume (crisis / abusive / honest-fail) MUST refund** (`free_used_this_week -= 1`) to preserve READ-10/D-09 ("limit never consumed on failure"). See Pitfall 4 — this is the highest-risk interaction in the phase. The alternative (keep consume last, add a separate atomic check first) re-introduces a check→draw→consume TOCTOU. Recommend the **consume-as-gate + refund-on-failure** model and test every refund path.

### Pattern 1: Atomic conditional consume with RETURNING (THE core mechanic, LIMIT-03)

**What:** A single `UPDATE … WHERE free_used_this_week < free_weekly_limit … RETURNING` is the entire check+decrement. PostgreSQL locks the matched row for the statement's duration; a second concurrent UPDATE blocks, then re-reads the just-committed value and re-evaluates its WHERE — so at the boundary (used=2, limit=3) exactly one of two racers matches and increments to 3; the other matches **zero rows**. Zero rows is detected by `result.scalar_one_or_none() is None` (or `result.first() is None`). `[CITED: docs.sqlalchemy.org/en/20/tutorial/data_update.html — "CursorResult.rowcount is not necessarily available for an UPDATE … that uses RETURNING"]`

**When to use:** Always, for the free bucket. This replaces the Phase-4 read-`_has_quota`-then-`_consume_limit` pair on the hot path.

**Verified caveat (decisive for the design):**
- With `.returning()`, `result.rowcount` is **NOT reliable** (you get a `ChunkedIteratorResult`). Detect 0-matches via the **returned row being absent**, not rowcount. `[CITED: docs.sqlalchemy.org/en/20/tutorial/data_update.html; github.com/sqlalchemy/sqlalchemy discussion #12095]`
- Without `.returning()`, asyncpg **does** support "sane rowcount" — `result.rowcount` is rows *matched by WHERE* (modified or not). `[VERIFIED: WebSearch — SQLAlchemy asyncpg "sane_rowcount"]` So a no-RETURNING variant (`rowcount == 1` → consumed, `0` → paywall) is equally valid, but then you need a second read for the remaining count. **Recommend the RETURNING variant** — one round-trip returns both the verdict (row present?) and the new count (for `remaining_limits` + the FE).

```python
# Source pattern: SQLAlchemy 2.0 Core async (docs.sqlalchemy.org/en/20/tutorial/data_update.html
# + core/sqlelement.html case()). Folds the lazy reset (Pattern 2) into the SAME statement.
from datetime import datetime, timedelta, UTC
from sqlalchemy import update, case, or_, and_
from app.models import UserLimits

WINDOW = timedelta(days=7)

async def _consume_free_atomic(session, user_id, now: datetime) -> tuple[int, int] | None:
    """One indivisible reset+check+increment+re-anchor. Returns (used, limit) or None if no slot."""
    stale = and_(UserLimits.week_start.is_not(None),
                 UserLimits.week_start <= now - WINDOW)
    fresh_has_room = and_(UserLimits.week_start.is_not(None),
                          UserLimits.week_start > now - WINDOW,
                          UserLimits.free_used_this_week < UserLimits.free_weekly_limit)
    first_ever = UserLimits.week_start.is_(None)  # week_start NULL → anchors now (D-02)

    stmt = (
        update(UserLimits)
        .where(UserLimits.user_id == user_id)
        .where(or_(stale, first_ever, fresh_has_room))
        .values(
            free_used_this_week=case((stale, 1), (first_ever, 1),
                                     else_=UserLimits.free_used_this_week + 1),
            week_start=case((stale, now), (first_ever, now),
                            else_=UserLimits.week_start),
        )
        .returning(UserLimits.free_used_this_week, UserLimits.free_weekly_limit)
    )
    row = (await session.execute(stmt)).first()   # None ⇒ no slot ⇒ paywall
    return (row[0], row[1]) if row is not None else None
```

**Why this is race-safe (the proof obligation for success-criterion 3):** the WHERE predicate and the SET both read `free_used_this_week`/`week_start` *inside the same locked UPDATE*. There is no Python-side gap where another transaction can observe a stale value and also pass the check. Two `asyncio.gather`-ed requests at the boundary execute as two serialized UPDATEs (the second waits on the first's row lock, then re-evaluates against the committed new value). One increments, one returns no row. **No `SELECT … FOR UPDATE` needed; no application lock; no advisory lock.**

### Pattern 2: Lazy rolling reset folded into the conditional UPDATE (LIMIT-02, D-01)

**What:** Rather than read → "is it stale?" → maybe-reset → then decrement (three steps, two TOCTOU windows), express the reset as `CASE` arms in the SAME UPDATE (shown in Pattern 1). The three states collapse into one statement:
- **stale** (`week_start ≤ now − 7d`): `free_used := 1`, `week_start := now` (reset + immediately count this reading + re-anchor).
- **first_ever** (`week_start IS NULL`, D-02): `free_used := 1`, `week_start := now` (anchor on first reading).
- **fresh with room** (`week_start > now − 7d AND free_used < limit`): `free_used := free_used + 1`, `week_start` unchanged.
- **fresh, no room**: no WHERE arm matches → 0 rows → paywall (the reset did NOT fire, so a within-window exhausted user is correctly blocked).

**When to use:** This IS the free-bucket consume. There is no separate "reset" call.

**Why folded, not separate:** a separate `if now - ws >= 7d: reset()` then `consume()` has a window where two requests both read a stale `week_start`, both reset to `used=0`, both increment to 1 → **two free readings spent as one** (double-spend) or the second reset clobbers the first's increment (mis-reset). Folding eliminates the window because the lock is held across the whole reset-and-increment. `[ASSUMED — the double-spend scenario is reasoned from the lock semantics, not separately benchmarked; the fold is the standard defense and is verified-correct by Pattern 1's lock proof.]`

### Pattern 3: Redis Lua throttle as the first gate (LIMIT-05, D-07)

**What:** Before any PG/LLM work, run an atomic `INCR` + conditional `EXPIRE` in one Lua script. The script sets the TTL **only when `INCR` returns 1** (first hit in the window), so the window is a true fixed window with no separate-call race.

**When to use:** As a FastAPI gate in the router (or the first lines of `create_reading`, before the session is touched). Returns 429 `{kind:"throttle"}` if the count exceeds the burst cap.

```python
# Source: redis.readthedocs.io/en/stable/lua_scripting.html (register_script) +
# redis.io/docs/latest/commands/incr (INCR/EXPIRE rate-limit pattern). Async client.
_THROTTLE_LUA = """
local c = redis.call('INCR', KEYS[1])
if c == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return c
"""
# registered once at module load against redis.asyncio client:
_throttle = redis_client.register_script(_THROTTLE_LUA)

async def _throttle_ok(user_id, *, window_s: int, burst_cap: int) -> bool:
    count = await _throttle(keys=[f"throttle:reading:{user_id}"], args=[window_s])
    return int(count) <= burst_cap
```

**Recommended band (within D-07; planner finalizes the exact numbers):**
- **Single fixed-window, burst-cap form (recommend — simplest, satisfies D-07):** `window_s = 60`, `burst_cap = 5` → "≤5 readings per rolling-ish 60s window". A real user (30s+ between readings) tops out at ~2/min, never hit. Rapid-fire double-taps and scripts are caught.
- The "~1 / 10–15s" spacing in D-07 is *softer* than the burst cap and the same single window covers it; a **two-tier** form (a 12s `EXPIRE`/`cap=1` "spacing" key + a 60s/`cap=5` "burst" key, both checked) is available if the planner wants stricter spacing, at the cost of a second key + a slightly more complex Lua. **Recommend the single 60s/5 window for MVP**; document the two-tier as the upgrade.
- **`INCR`/`EXPIRE` ordering + the race (D-07 asks explicitly):** set `EXPIRE` **only on `count == 1`** and do it **inside Lua** so the INCR-then-EXPIRE pair is atomic. The plain two-await form (`await incr; await expire`) can strand a counter without a TTL if the worker dies between the two — permanent throttle. `[VERIFIED: dev.to/silentwatcher_95 "Fixing Race Conditions in Redis Counters"; redis.io ratelimiting tutorial]`
- **`decode_responses=True`** is set on the shared client — the Lua `return c` arrives as a `str`; `int(count)` it.
- **Fallback if Lua is rejected for any reason:** an idempotent `pipeline(transaction=True)` doing `INCR` **and** `EXPIRE` every call (re-arming the TTL each hit) is race-free against the stuck-counter problem (the key always has a fresh TTL) — it just makes the window "sliding from last hit" rather than "fixed". Acceptable for a throttle. `[CITED: redis.readthedocs.io asyncio_examples — pipeline(transaction=True)]`

**redis-py async API confirmation:** `register_script(lua)` returns a `Script`; invoke `await script(keys=[...], args=[...])` on the async client; it auto-loads on `NOSCRIPT` and retries. `[CITED: redis.readthedocs.io/en/stable/lua_scripting.html]`

### Pattern 4: `determine_access` bucket seam (LIMIT-04, D-06)

**What:** A pure function over the loaded `UserLimits` that returns *which bucket* the next reading should spend, in order free → subscription → paid_balance. This phase only ever returns `free` (sub/paid are 0), but the shape is built so Phase 7 fills the other buckets with **no re-architecture** — Phase 7 adds the sub/paid consume statements behind the same enum.

**When to use:** Called inside `create_reading` immediately before the consume, to pick which atomic statement runs. Generalizes the Phase-4 `_consume_limit` free/paid/subscription branch (which already exists in `reading.py`).

```python
import enum
class Bucket(enum.StrEnum):
    FREE = "free"; SUBSCRIPTION = "subscription"; PAID = "paid"; NONE = "none"

def determine_access(limits) -> Bucket:
    """Order: spend expiring buckets first (free weekly, then subscription), preserve permanent paid last (D-06).
    Phase 6: only FREE is ever populated; the sub/paid arms are seams (always skipped until Phase 7)."""
    free_left = (limits.free_weekly_limit or 0) - (limits.free_used_this_week or 0)
    sub_left  = (limits.subscription_spreads_limit or 0) - (limits.subscription_spreads_used or 0)
    if free_left > 0:               # NOTE: a *stale* window also has a slot — see below
        return Bucket.FREE
    if sub_left > 0:
        return Bucket.SUBSCRIPTION  # Phase 7
    if (limits.paid_spreads_balance or 0) > 0:
        return Bucket.PAID          # Phase 7
    return Bucket.NONE
```

**Subtlety the planner must wire:** `determine_access` reads the row's *current* `free_used`, but the rolling reset (Pattern 2) is applied *inside* the atomic UPDATE. So a user whose window is stale shows `free_left == 0` on the pre-read yet genuinely has a slot after reset. **Resolution:** the cleanest design is `determine_access` returns `FREE` whenever the window is stale OR `free_left > 0` (i.e. treat stale-window as "free available"), and the atomic UPDATE is the final arbiter (it returns None only if truly exhausted within a fresh window). Alternatively, *always attempt the free atomic UPDATE first* (it self-handles stale+room+exhausted) and only fall through to sub/paid when it returns None — this is simpler and recommended: **try free-atomic; on None, this phase returns paywall** (Phase 7 will try sub/paid on None). Document this so Phase 7 slots in.

### Pattern 5: Race-safe `user_limits` row at auth (D-02)

**What:** Guarantee one row per user at upsert. The existing `_ensure_user_limits` (telegram_auth.py) does a **SELECT-then-INSERT** — a race on a brand-new user's first two concurrent logins could insert two rows (no unique constraint on `user_id` — it's only `index=True`, not `unique=True`). Recommend replacing with a single PG `INSERT … ON CONFLICT DO NOTHING`. **But** `ON CONFLICT` needs a unique constraint/index on the conflict target; `ix_user_limits_user_id` is a plain (non-unique) index. Two sub-options:
- (a) Add a **unique** constraint on `user_limits.user_id` (it should be 1:1 with users anyway) + `ON CONFLICT (user_id) DO NOTHING`. **Recommend** — also prevents duplicate-row bugs structurally. (Small migration.)
- (b) Keep SELECT-then-INSERT but accept the tiny race (first-login double-insert is benign-ish but violates the 1:1 invariant and breaks `scalar_one()` reads elsewhere). **Not recommended.**

**Also adjust for D-02:** the current `_ensure_user_limits` sets `week_start=_current_week_start()` (ISO Monday). D-02 requires **`week_start=NULL`** (anchors on first reading). Change the insert to omit `week_start` (NULL default) and **delete the now-unused `_current_week_start()` helper** (it encodes the overridden ISO-week model).

### Anti-Patterns to Avoid

- **Read-check-then-write the limit in Python** (`if _has_quota(): _consume_limit()`): the exact TOCTOU success-criterion 3 forbids. Two requests both read used=2, both pass, both write 3 → 4 readings on a 3 limit. **Use Pattern 1.**
- **Separate reset call before consume:** double-spend / mis-reset window (Pattern 2 rationale).
- **Plain `INCR` then `EXPIRE` as two awaits:** stuck-counter race (Pattern 3). Use Lua or the re-arming pipeline.
- **Throttle after the limit check or after the DB session opens:** violates "before Postgres" (D-07/§29.2). It must be GATE 0.
- **Caching the free count in Redis as the read source:** CLAUDE.md keeps PG authoritative; a Redis mirror that drifts from PG would mis-gate. The throttle is the only Redis write this phase.
- **Returning the paywall as a non-200 error that the global handler catches:** the codebase's convention is a **deliberate 200 soft body** with a `status` field (see `_soft_body`); keep the paywall a 200 body (or a chosen dedicated status — see Error Transport), never a 500.
- **`max_length`/validators that 500 on the reset math:** keep the consume in SQL; do not reconstruct dates in Python and risk naive/aware `datetime` subtraction errors.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic check+decrement under concurrency | A Python mutex / asyncio.Lock / app-level "is it free?" guard | One PG conditional `UPDATE…WHERE…RETURNING` (Pattern 1) | An in-process lock does not span Uvicorn workers/processes; only the DB row lock is correct across the fleet. |
| "Set TTL only on first hit" atomically | INCR then a Python `if count==1: await expire` | Lua `INCR`+conditional-`EXPIRE` (Pattern 3) | The Python branch is across an await — the stuck-counter race. Lua runs atomically server-side. |
| Rolling-window reset scheduling | A cron / Celery beat / background task | Lazy-on-read fold into the UPDATE (Pattern 2) | Edit #2 forbids a queue; lazy reset needs no scheduler and is race-safe when folded. |
| Per-user 1:1 row guarantee | SELECT-then-INSERT with app retry | `INSERT … ON CONFLICT (user_id) DO NOTHING` + unique constraint (Pattern 5) | DB upsert is atomic; app retry races. |
| HTTP-status rate-limit plumbing | A custom middleware stack | Return 429 from the gate; let the FE branch on status (06-UI-SPEC) | The transport is one status code; slowapi exists but the *business* throttle is custom Redis (per STACK.md note) — keep it in the gate. |

**Key insight:** every "limit" bug in this domain is a concurrency bug, and every concurrency bug here is solved by *pushing the decision into a single atomic primitive* — the DB row lock for the quota, the Lua script for the throttle. The moment a check and its corresponding write live in two separate round-trips with Python in between, the boundary race is back.

## Runtime State Inventory

> This is a feature phase, not a rename/refactor — but D-02 changes how a runtime datastore (`user_limits`) is *seeded* and the reset model changes how an existing column is *interpreted*. The relevant runtime-state questions:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (existing rows) | Any `user_limits` rows already created by the **current** `_ensure_user_limits` carry `week_start = <ISO Monday date>`, not NULL, and the column is `DATE`. After the D-01 switch to rolling-timestamp semantics, these legacy values are a *date at midnight* — the lazy reset will treat them as "anchored at 00:00 of that Monday", which self-heals on the first post-deploy reading (stale → reset → re-anchor to `now`). **No destructive migration of row values needed**, but the **column type** must change (DATE→TIMESTAMP) — an Alembic `alter_column`. | Alembic migration: `alter_column('user_limits','week_start', type_=TIMESTAMP(timezone=True))`. Existing date values cast to midnight-timestamp cleanly. |
| Live service config | None — no external service stores this string/state. | None. |
| OS-registered state | None — no cron/scheduler (edit #2 forbids; lazy reset). **Verified by absence:** there is no Celery/cron to update. | None. |
| Secrets/env vars | `REDIS_URL` already present + validated at startup (config.py). The throttle adds Redis *writes* but no new secret. | None. |
| Build artifacts | None — no new package, no egg-info churn. | None. |

**The canonical question — after code is updated, what runtime state still holds the old model?** Only the `user_limits.week_start` column (type + a handful of seeded ISO-Monday dates). Both self-heal: the column via one `alter_column`, the values via the first lazy reset. No data backfill task required.

## Common Pitfalls

### Pitfall 1: `week_start` is a DATE, but the rolling window needs a TIMESTAMP
**What goes wrong:** D-01 says `week_start = timestamp of the first reading` and reset fires when `now − week_start ≥ 7 days`. With a `DATE` column, `week_start` loses the time-of-day; re-anchoring `week_start = now` stores only the date; the 7-day check becomes day-granular. A user who reads at 23:50 Monday and again at 00:10 the following Monday-8d sees an off-by-up-to-a-day reset, and the D-04 countdown ("вернутся через N") can't compute hours.
**Why it happens:** the column was designed in Phase 1 for the *original* ISO-week model (a date is fine for "which Monday"). D-01 changed the model in Phase 6; the column type didn't follow.
**How to avoid:** Alembic `alter_column` `week_start` → `TIMESTAMP(timezone=True)`; update the model `Mapped[datetime | None]` and the `LimitsOut` schema (`week_start: datetime | None`). Use `datetime.now(UTC)` (the codebase's `deleted_at` convention) or `func.now()` consistently.
**Warning signs:** the planner writes `now.date()` anywhere; the countdown helper receives a date and renders "0 дней"; tests pass at day-granularity but the reset is hours-off in staging.

### Pitfall 2: Consuming before the draw without refunding on failure breaks READ-10
**What goes wrong:** Phase 4's invariant (asserted by `test_readings_limit.py`) is "limit consumed exactly once on success, never on crisis/abusive/honest-fail". Pattern 1 consumes *as the gate* (before draw), so every post-consume non-success exit now over-charges unless it refunds.
**Why it happens:** the atomic-consume-as-gate model inverts the Phase-4 "consume last" order to get the TOCTOU-free check.
**How to avoid:** on crisis, abusive, AND honest-fail, issue a compensating `UPDATE user_limits SET free_used_this_week = free_used_this_week - 1 WHERE user_id=:id` (only for the free bucket; Phase 7 refunds sub/paid analogously) inside the same transaction before the soft-body return. Add explicit tests mirroring the existing `test_limit_untouched_on_crisis/_abusive/_honest_fail` — they must still pass with the consume-then-refund flow.
**Warning signs:** `test_limit_untouched_on_*` go red; a user "loses" a free reading on a crisis question.
**Alternative (avoids refunds entirely):** keep consume LAST (Phase-4 order) and make the *gate* a non-mutating atomic check that also reserves — but a pure check can't reserve without a write, so you're back to TOCTOU. The refund model is the recommended, lower-surprise choice; document the tradeoff for the planner.

### Pitfall 3: The existing test harness can't exercise true row-lock concurrency
**What goes wrong:** the boundary-race test (`asyncio.gather(create_reading, create_reading)` at used=2/limit=3) is the proof for success-criterion 3. But the integration harness (`auth_session`) binds the session to **one connection** with `join_transaction_mode="create_savepoint"` and rolls back at teardown. Two coroutines sharing one `AsyncSession`/connection **cannot** demonstrate cross-connection row locking — asyncpg forbids concurrent ops on one connection, and savepoints aren't separate transactions. The test would either error ("another operation in progress") or pass trivially without proving anything.
**Why it happens:** the harness was built for transactional isolation/speed (per-test rollback), the opposite of what a real-concurrency test needs (two real committed transactions on two connections).
**How to avoid:** the concurrency test needs a **dedicated fixture** that (a) opens **two independent `AsyncSession`s on two real connections** (not the savepoint-shared one), (b) seeds a committed user at the boundary, (c) `asyncio.gather`s two real `create_reading` calls that each `commit`, then (d) asserts exactly one COMPLETED + one paywall and `free_used_this_week == limit` (never `limit+1`), and (e) cleans up with a real delete (no outer-rollback). Mark it skip-if-PG-down like the rest. This is the single most important test to design correctly — see Validation Architecture.
**Warning signs:** the race test uses `auth_session`; it passes but `free_used` is never observed at `limit+1` even when you deliberately break the atomicity (a test that can't fail isn't testing).

### Pitfall 4: Throttle counted on requests that never consumed
**What goes wrong:** if the throttle `INCR`s for *every* POST including ones that 404 (bad deck) or hit the paywall, a user near the burst cap who taps a broken deck gets throttled. Usually fine (it IS a rate limit on the *endpoint*), but verify it's intended: the throttle is "creation attempts", not "successful creations".
**Why it happens:** the gate runs first, before any validation.
**How to avoid:** confirm with the band — D-07's intent is anti-burst-abuse, so counting all attempts is correct and desirable (a script hammering with bad bodies should still be throttled). Document that the throttle counts *attempts*, the weekly limit counts *successful free consumes*. No change needed; just be explicit so it's not mistaken for a bug.
**Warning signs:** a test expects the throttle to only count successes (it shouldn't).

### Pitfall 5: `case()` / `or_()` predicate drift between the WHERE and the SET
**What goes wrong:** the "stale" condition appears in both the WHERE (to allow the row to match) and the SET `CASE` (to choose reset vs increment). If the two expressions diverge (e.g. `<` vs `<=` on the 7-day boundary), a row can match WHERE-stale but hit the SET else-branch (`+1` on a stale window → reset never happens, count climbs past limit), or vice-versa.
**Why it happens:** duplicated boundary logic.
**How to avoid:** define the `stale` / `first_ever` / `fresh_has_room` expressions **once** as Python variables and reuse the same objects in both `.where(or_(...))` and `.values(case(...))` (as in the Pattern 1 snippet). Test the exact boundary (`week_start == now − 7d` to the second).
**Warning signs:** a reset boundary test is flaky; `free_used` occasionally exceeds `free_weekly_limit` in the reset test.

## Code Examples

### Detecting "no slot" (0 rows) from the atomic consume
```python
# Source: docs.sqlalchemy.org/en/20/tutorial/data_update.html (RETURNING + no reliable rowcount)
row = (await session.execute(consume_stmt)).first()
if row is None:
    # the WHERE matched nothing → within a fresh window and free_used == limit → paywall
    reset_at = _compute_reset_at(limits.week_start)   # week_start + 7d (None ⇒ "совсем скоро")
    return self._soft_paywall_body(reset_at=reset_at)
used, limit = row[0], row[1]
remaining = max(0, limit - used)
```

### Throttle gate wired as a FastAPI dependency (first gate, before the service)
```python
# Source: redis.readthedocs.io/en/stable/lua_scripting.html ; runs before get_session opens a txn.
async def throttle_gate(user: User = Depends(get_current_user)) -> None:
    if not await _throttle_ok(user.id, window_s=60, burst_cap=5):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "throttled")
# router: @router.post("/readings", dependencies=[Depends(throttle_gate)])
# 429 body/headers carry enough for createReading.ts to throw kind:"throttle" (06-UI-SPEC).
```

### Reset-moment for the FE countdown (D-04) — backend supplies `reset_at`
```python
# week_start + 7d is the per-user reopen moment (D-01). Surfaced so formatReset() renders «через N».
def _compute_reset_at(week_start: datetime | None) -> datetime | None:
    return (week_start + timedelta(days=7)) if week_start is not None else None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `SELECT FOR UPDATE` + app check | Single conditional `UPDATE…WHERE…RETURNING` | SQLAlchemy 2.0 RETURNING is first-class | Fewer round-trips, shorter lock window, less app code |
| INCR + EXPIRE (two commands) | Lua `INCR`+conditional-`EXPIRE` (one atomic) | Long-standing Redis best practice, re-affirmed 2024-2026 | Eliminates the stuck-counter race |
| `rowcount` to detect UPDATE matches | `.returning()` + row-present check (rowcount unreliable with RETURNING) | SQLAlchemy 2.0 behavior | Must read the returned row, not rowcount |

**Deprecated/outdated:**
- `_current_week_start()` (ISO Monday) in `telegram_auth.py` — encodes the model D-01 overrides. Remove with D-02.
- The Phase-4 read-`_has_quota`-then-`_consume_limit` pair on the create hot path — superseded by the atomic consume (keep `_remaining` for the read-only `GET /api/me` projection).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `week_start` must migrate `DATE → TIMESTAMP` for D-01's rolling window to be hour-accurate. CONTEXT says "no schema change expected"; this research finds one IS needed. | Pitfall 1 / Open Q1 | If the planner keeps `DATE`, the reset and D-04 countdown are day-granular — a degraded but not broken UX. The migration is small; recommend doing it. Needs user/planner confirmation since it contradicts CONTEXT. |
| A2 | A unique constraint should be added to `user_limits.user_id` to enable `ON CONFLICT DO NOTHING` (Pattern 5). Currently only a non-unique index exists. | Pattern 5 / Open Q2 | Without it, either keep the (racy) SELECT-INSERT or use `ON CONFLICT` on a constraint that doesn't exist (errors). Small migration; aligns with the real 1:1 invariant. |
| A3 | The recommended throttle band = single 60s window, cap 5. D-07 delegates exact numbers to the planner; these are *a* valid choice within the band, not user-confirmed. | Pattern 3 | Too tight → real users hit it (bad); too loose → abuse leaks. 60s/5 is conservative-safe; planner may tune. Low risk. |
| A4 | Consume-as-gate + refund-on-failure is preferred over keep-consume-last. Reasoned from lock semantics; both satisfy the criteria, the choice is a design tradeoff. | Pitfall 2 | If the planner prefers consume-last, they must add a separate non-mutating atomic reservation — harder to keep TOCTOU-free. Refund model is lower-surprise. |
| A5 | The double-spend scenario for a *separate* reset call is reasoned from lock semantics, not independently benchmarked. The fold (Pattern 2) is verified-correct via Pattern 1's lock proof. | Pattern 2 | The fold is strictly safer regardless; the only risk is over-justifying. None practical. |

**These are the items discuss-phase / the planner should confirm before locking** — especially A1 and A2 (schema changes contradicting the "no schema change" CONTEXT note).

## Open Questions (RESOLVED)

> **RESOLVED 2026-06-15 (before planning).** All four answered and reflected in the plans:
> Q1 (A1) + Q2 (A2) → the user **APPROVED** the bundled Alembic migration (`week_start` Date→TIMESTAMP + UNIQUE on `user_limits.user_id`), implemented in **06-01-PLAN.md**. Q3 → **FastAPI dependency** (`throttle_gate`), **06-03-PLAN.md**. Q4 → **throttle 429 / paywall 200 soft body** carrying `reason` + `reset_at`, across **06-02 / 06-03 / 06-04**. The recommendations below are the chosen path.

1. **`week_start` DATE→TIMESTAMP migration (A1).** *(RESOLVED → user-approved, 06-01)*
   - What we know: the column is `sa.Date()` (model + migration 0001 confirmed); D-01 needs timestamp precision; an Alembic `alter_column` casts existing dates to midnight-timestamps cleanly.
   - What's unclear: whether the user accepts a schema change here (CONTEXT said none expected).
   - Recommendation: **do the migration** — it's the correct fix and self-heals existing rows. Flag prominently; let discuss-phase/planner confirm. If declined, fall back to day-granular reset (document the imprecision in the countdown).

2. **Unique constraint on `user_limits.user_id` for race-safe upsert (A2).**
   - What we know: only `ix_user_limits_user_id` (non-unique) exists; `ON CONFLICT` needs a unique target; the relationship is logically 1:1.
   - Recommendation: add the unique constraint (small migration), then `ON CONFLICT (user_id) DO NOTHING`. Bundles naturally with the Q1 migration (one revision).

3. **Throttle placement: FastAPI dependency vs first lines of `create_reading`.**
   - What we know: both run "before Postgres"; a dependency keeps the router thin and is testable in isolation; in-service keeps all gates in one place.
   - Recommendation: **FastAPI dependency** (`dependencies=[Depends(throttle_gate)]`) — cleanest, matches the thin-router convention, and the 429 short-circuits before `get_session` even opens. (Either is defensible; planner's call.)

4. **Error transport for the paywall: 200 soft body vs a dedicated status.**
   - What we know: the codebase convention is a deliberate **200** soft body with a `status` field (`_soft_body` → `status="failed"`, copy in `summary.soft_advice`). 06-UI-SPEC says the FE branches on a discriminant and needs `reset_at`; it explicitly leaves the exact status/shape to the planner ("soft 200 or a dedicated status the planner picks").
   - Recommendation: keep the **200 soft body** for consistency with refusal/honest-fail, BUT add a machine-readable discriminator the FE can branch on without string-matching — e.g. a `reason: "paywall" | "throttle" | "failure"` field (or reuse `status` with a new value) plus a `reset_at` field on `ReadingOut`. The throttle, being a true rate-limit, is the one case that fits a real **429** (06-UI-SPEC's `status === 429` discriminant). So: **throttle → 429**, **paywall/honest-fail/refusal → 200 soft body** carrying `reason` + (`reset_at` for paywall). Planner finalizes the field names; this satisfies the FE's three-way `catch` without conflating (D-08).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL 16 | Atomic consume, reset, `user_limits` | ✓ (compose / managed) | 16.x | — (hard requirement; integration tests skip if down, per harness) |
| Redis 7 | Throttle Lua `INCR`/`EXPIRE` | ✓ (compose / managed) | 7.x | Re-arming pipeline if Lua rejected (Pattern 3 fallback); tests skip if Redis down |
| redis-py async | `register_script`, async client | ✓ pinned `>=5.2,<6` | 5.2.x resolved | — |
| SQLAlchemy 2.0 async | `update().values(case()).returning()` | ✓ pinned `2.0.*` | 2.0.50 | — |
| asyncpg | RETURNING + sane rowcount | ✓ pinned `0.31.*` | 0.31.0 | — |
| uv venv (`uv run pytest`) | Test execution (pnpm not in PATH per MEMORY) | ✓ | — | — |

**Missing dependencies with no fallback:** none — all required infra is already provisioned and pinned.
**Missing dependencies with fallback:** Redis Lua (fallback = re-arming pipeline). No blockers.

## Validation Architecture

> `workflow.nyquist_validation = true` (config.json) — this section is REQUIRED and the nyquist VALIDATION.md is generated from it.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8 + pytest-asyncio (`asyncio_mode = "auto"`) — confirmed in `backend/pyproject.toml` |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` (testpaths=`tests`) |
| Quick run command | `cd backend && uv run pytest tests/integration/test_readings_limit.py -x` |
| Full suite command | `cd backend && uv run pytest` |
| LLM isolation | `FakeLLM` / `FakeSafety` injected via `ReadingService(safety=…, llm=…)` or `app.dependency_overrides[get_reading_service]` — **no Anthropic call** (Phase-4 pattern, in `tests/integration/conftest.py`) |
| DB/Redis skip | DB-touching + Redis tests `pytest.skip` cleanly when the dependency is unreachable (root + integration conftest) — suite stays green without `docker compose up` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LIMIT-03 | **Two concurrent requests at the boundary cannot both succeed** (success-criterion 3) | integration (real concurrency) | `uv run pytest tests/integration/test_readings_concurrency.py -x` | ❌ Wave 0 — **new fixture required** (Pitfall 3) |
| LIMIT-03 | 4th free reading in a fresh window → paywall body + `reset_at`, no draw | integration | `uv run pytest tests/integration/test_readings_limit.py::test_paywall_on_exhausted -x` | ⚠️ extend existing `test_limit_untouched_on_no_quota` |
| LIMIT-02 | Reset boundary: `week_start = now − 7d` (stale) → next reading resets to used=1, re-anchors week_start≈now | integration | `uv run pytest tests/integration/test_readings_reset.py::test_reset_on_stale_window -x` | ❌ Wave 0 |
| LIMIT-02 | Within window (`week_start = now − 3d`, used=3) → still blocked (reset does NOT fire early) | integration | `…::test_no_reset_within_window -x` | ❌ Wave 0 |
| LIMIT-02 | First reading ever (`week_start IS NULL`, D-02) → anchors week_start, used=1 | integration | `…::test_first_reading_anchors -x` | ❌ Wave 0 |
| LIMIT-05 | Throttle: ≤cap rapid calls pass, the (cap+1)th → 429 `{kind:"throttle"}` before PG/LLM | integration | `uv run pytest tests/integration/test_throttle.py::test_burst_blocked -x` | ❌ Wave 0 (needs `redis_client` fixture) |
| LIMIT-05 | Throttle window expiry: after `window_s`, the counter resets (a later call passes) | integration | `…::test_window_expires -x` | ❌ Wave 0 |
| LIMIT-05 | Throttle never reaches PG: `fake_llm.calls == 0` and no reading row on a throttled call | integration | `…::test_throttle_short_circuits_before_pg -x` | ❌ Wave 0 |
| LIMIT-04 | `determine_access` returns FREE when free_left>0 or window stale; NONE only when truly exhausted (sub/paid=0) | unit (pure fn) | `uv run pytest tests/unit/test_determine_access.py -x` | ❌ Wave 0 |
| LIMIT-04 | Bucket order: with (mocked) sub/paid>0, returns SUBSCRIPTION before PAID (Phase-7 seam proof) | unit | `…::test_bucket_order -x` | ❌ Wave 0 |
| LIMIT-01/READ-10 | Consume exactly once on success; **refund** on crisis/abusive/honest-fail (Pitfall 2) | integration | `uv run pytest tests/integration/test_readings_limit.py -x` (extend the 4 existing untouched-on-* tests) | ⚠️ existing tests must still pass with consume+refund |
| D-02 | `user_limits` row created at auth with `week_start=NULL`, used=0, limit=3 | integration | `uv run pytest tests/integration/test_auth_flow.py::test_limits_row_created -x` | ⚠️ extend (row already created; assert `week_start is None`) |
| D-02 | Concurrent first-logins create exactly one row (ON CONFLICT) | integration | `…::test_double_login_single_limits_row -x` | ❌ Wave 0 (needs two-connection fixture) |

### The concurrency test (the load-bearing one — design spec)
This is the proof for success-criterion 3 and the highest-value test in the phase. It **cannot** use the savepoint-shared `auth_session` (Pitfall 3). Required shape:

```python
# tests/integration/test_readings_concurrency.py  (NEW)
# Two REAL connections (not the savepoint session), a committed boundary user, gather two creates.
async def test_two_concurrent_at_boundary_only_one_succeeds(seeded_catalog_committed):
    # Arrange: a user with free_weekly_limit=3, free_used_this_week=2, week_start=now (fresh),
    #          COMMITTED so both connections see it.
    async def attempt():
        async with SessionLocal() as s:          # independent connection
            svc = ReadingService(safety=FakeSafety(), llm=FakeLLM(output))
            r = await svc.create_reading(s, user, _REQ)  # service commits
            return r.status
    s1, s2 = await asyncio.gather(attempt(), attempt())
    # Assert: exactly one COMPLETED, one FAILED(paywall); counter is EXACTLY the limit, never limit+1.
    statuses = sorted([s1, s2])
    assert statuses == ["completed", "failed"]      # one each (order-independent)
    async with SessionLocal() as s:
        used = (await s.execute(select(UserLimits.free_used_this_week)
                                .where(UserLimits.user_id == user.id))).scalar_one()
    assert used == 3                                 # NOT 4 — the atomicity proof
```

Notes: (a) needs a **committed** seed (a sibling fixture to `seeded_catalog` that commits + cleans up via explicit delete, since the savepoint-rollback harness can't share rows across connections); (b) skip-if-PG-down like the rest; (c) **mutation test the test**: temporarily replace the atomic UPDATE with a read-check-write and confirm this test goes red (`used == 4`) — a concurrency test that can't observe the failure isn't proving anything (Pitfall 3 warning sign).

### Sampling Rate
- **Per task commit:** `uv run pytest tests/integration/test_readings_limit.py tests/unit/test_determine_access.py -x` (the touched-area quick run, <30s without the live LLM).
- **Per wave merge:** `cd backend && uv run pytest` (full backend suite — baseline 83 pass / 65 skip without Docker; with Docker the new concurrency/throttle/reset tests run).
- **Phase gate:** full suite green (all new LIMIT tests pass with PG+Redis up) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/integration/test_readings_concurrency.py` — covers LIMIT-03 boundary race (NEW, two-connection fixture)
- [ ] `tests/integration/test_readings_reset.py` — covers LIMIT-02 (stale / within-window / first-ever)
- [ ] `tests/integration/test_throttle.py` — covers LIMIT-05 (burst / window-expiry / short-circuit-before-PG); uses `redis_client`
- [ ] `tests/unit/test_determine_access.py` — covers LIMIT-04 bucket order (pure fn, no DB)
- [ ] A **committed-seed fixture** (sibling of `seeded_catalog`) + a **two-independent-connections** helper in `tests/integration/conftest.py` — the substrate the concurrency + double-login tests need (the existing savepoint harness can't do cross-connection concurrency)
- [ ] Extend `tests/integration/test_readings_limit.py` — invert/extend the 4 untouched-on-* tests to assert consume+**refund** keeps the counter correct; add `test_paywall_on_exhausted` asserting the `reset_at` field
- [ ] Extend `tests/integration/test_auth_flow.py` — assert `week_start is None` at creation (D-02) + single-row-on-double-login
- [ ] Frontend (UI-SPEC-locked, lighter): `createReading.test.ts` (429→`kind:"throttle"`, paywall-body→`kind:"paywall"` with `reset_at`, non-completed→`kind:"failure"`); `copy.test.ts` already scans the new `PAYWALL_*`/`THROTTLE_*`/`LIMIT_*` strings for SAFE-06; **invert** the Phase-5 `ProfileScreen.test.tsx` assertion that the count is ABSENT (06-UI-SPEC flags this — it's now present, D-09); `formatReset`/`formatRemaining` pure-helper unit tests (plural rules, clamp ≥0, NaN-guard)

*Framework install: none — pytest/pytest-asyncio already in `[project.optional-dependencies].dev`.*

## Security Domain

> `security_enforcement = true`, `security_asvs_level = 1`, `security_block_on = "high"` (config.json). Required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (reused) | Throttle keys off `user.id` from the verified JWT (`get_current_user`) — never a body field. Unchanged auth spine. |
| V3 Session Management | no | No session change. |
| V4 Access Control | **yes** | The limit/throttle gate is **backend-only** (TZ §29.2); the FE count is display-only and forgeable, so the server gate is authoritative. Throttle + consume both key off the JWT `user.id`, never a request-body `user_id` (the same T-04-23/T-05-SPOOF discipline as the existing handlers). A user cannot raise their own limit or bypass the throttle by editing the request. |
| V5 Input Validation | **yes** | `ReadingCreate` already validates the body (422 before the service). The throttle window/cap and `reset_at` are server-computed, never client-supplied. |
| V6 Cryptography | no | No new crypto. (Card draw CSPRNG is Phase-4, unchanged.) |
| V7 Error Handling | **yes** | Paywall/throttle return soft bodies / 429 with **no internal detail** (no stacktrace, no SQL) — consistent with the global handler + `_soft_body`. The `reset_at` is the only new field exposed; it leaks nothing sensitive (it's the user's own reopen time). |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Quota bypass via concurrent requests (the boundary race) | Tampering / Elevation | Atomic conditional UPDATE (Pattern 1) — the row lock serializes; success-criterion 3. This IS the security control, not just a correctness one. |
| Forged `user_id` to spend another user's quota or dodge throttle | Spoofing / Tampering | Both gates key off the verified JWT `user.id` only (never body) — same discipline as `create_reading`/`patch_settings`. |
| Rapid-fire reading creation (cost/abuse — each reading is a paid LLM call) | Denial of Service | Redis throttle as GATE 0 before any PG/LLM work (LIMIT-05/D-07) — caps the burst at the cheapest possible layer. |
| Stuck throttle counter (self-inflicted permanent lockout) | Denial of Service | Lua atomic `INCR`+conditional-`EXPIRE` (or re-arming pipeline) — TTL always set; no orphaned counter. |
| SQL injection in the new UPDATE/`case()` | Tampering | Parameterized SQLAlchemy Core (`update()/case()/bindparams`) — no string-built SQL, same as the existing `on_conflict_do_update`. |
| Limit-block body leaking another user's data | Information Disclosure | The soft body carries only the caller's own `remaining`/`reset_at`; no cross-user fields. |

**Phase-specific note:** the throttle is itself a DoS *mitigation* but introduces a (low) **self-DoS** surface (a user could throttle themselves with rapid taps). That's intended and gentle (D-08: "колода переводит дыхание", 429 retryable). No per-IP throttle this phase (deferred — CONTEXT). At ASVS L1 with `block_on=high`, the load-bearing control is V4 (the backend-only atomic gate); ensure `/gsd-secure-phase` confirms no path lets the FE count or a body field influence the server decision. (Carry-forward: the deferred `/gsd-secure-phase` for Phases 4 & 5 flagged IDOR=HIGH in P5 — the same JWT-scoping discipline applies here and should be re-verified together.)

## Sources

### Primary (HIGH confidence)
- docs.sqlalchemy.org/en/20/tutorial/data_update.html — UPDATE…WHERE…RETURNING syntax; **"CursorResult.rowcount is not necessarily available for an UPDATE…that uses RETURNING"** (the decisive caveat for Pattern 1's 0-row detection)
- docs.sqlalchemy.org/en/20/core/sqlelement.html — `case()` construct (`when` tuples + `else_`) used to fold the reset into the UPDATE (Pattern 2)
- redis.readthedocs.io/en/stable/lua_scripting.html — `register_script(lua)` → `Script`, invoked `script(keys=[...], args=[...])`, auto-loads on NOSCRIPT (Pattern 3); confirmed available on `redis.asyncio`
- redis.readthedocs.io/en/stable/examples/asyncio_examples.html — async client + `pipeline(transaction=True)` (the throttle fallback)
- Live codebase (HIGH — read this session): `backend/app/services/reading.py` (the seam), `models/billing.py` + `alembic/versions/0001_initial_schema.py` (**`week_start = sa.Date()` confirmed**), `services/telegram_auth.py` (`_ensure_user_limits` SELECT-then-INSERT + ISO-Monday `week_start`), `core/redis.py` (`decode_responses=True`, pin `<6`), `tests/integration/conftest.py` (**savepoint single-connection isolation — Pitfall 3**), `pyproject.toml` (pins)

### Secondary (MEDIUM confidence — verified against official sources)
- github.com/sqlalchemy/sqlalchemy discussion #12095 + issue #9048 — asyncpg "sane rowcount" for plain UPDATE; rowcount gap with RETURNING (cross-checked with the official tutorial above)
- dev.to/silentwatcher_95 "Fixing Race Conditions in Redis Counters" + redis.io ratelimiting tutorial + redis.io/docs/.../incr — the INCR/EXPIRE stuck-counter race and the Lua fix (multiple sources agree; matches CLAUDE.md's named mechanism)

### Tertiary (LOW confidence — reasoned, flagged in Assumptions Log)
- The separate-reset double-spend scenario (A5) — reasoned from lock semantics, not independently benchmarked; the fold is verified-safe regardless via Pattern 1's lock proof.

## Metadata

**Confidence breakdown:**
- Atomic consume + RETURNING 0-row detection (Pattern 1): **HIGH** — official SQLAlchemy docs + the live column types; the single most important output is source-grounded.
- Lazy reset fold via `case()` (Pattern 2): **HIGH** on the SQL construct (official docs); **MEDIUM** on the exact predicate boundaries (planner must test `==`/`<`/`<=` at the 7d edge — Pitfall 5).
- Redis Lua throttle (Pattern 3): **HIGH** on the API + the race rationale (official redis-py docs + multiple sources); **MEDIUM** on the exact band numbers (A3, delegated by D-07).
- `determine_access` seam (Pattern 4): **HIGH** — pure function, generalizes existing code.
- Schema findings (week_start type, unique constraint): **HIGH** that they exist (confirmed in migration 0001 + model); **MEDIUM** that the user accepts the migrations (contradicts CONTEXT — A1/A2, needs confirmation).
- Validation Architecture (concurrency-test fixture gap): **HIGH** — the savepoint harness limitation is confirmed by reading the conftest.

**Research date:** 2026-06-15
**Valid until:** ~2026-07-15 (stable stack; the pinned versions and SQLAlchemy/redis-py APIs are long-stable — 30 days). Re-verify only if the redis-py pin is lifted past `<6` (RESP3 default would change client behavior).
