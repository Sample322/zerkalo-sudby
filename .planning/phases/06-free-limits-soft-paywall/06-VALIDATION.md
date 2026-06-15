---
phase: 6
slug: free-limits-soft-paywall
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-15
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from 06-RESEARCH.md "## Validation Architecture". The load-bearing test is the
> concurrent-boundary atomicity check (success-criterion 3) — it requires a NEW fixture
> because the existing savepoint harness cannot exercise true cross-connection row locks.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest 8.x + pytest-asyncio + httpx ASGITransport |
| **Framework (frontend)** | vitest (+ Testing Library) |
| **Config file** | `backend/pyproject.toml` (pytest/asyncio) ; `frontend/vitest.config.ts` |
| **Quick run command** | `cd backend && uv run pytest -q` |
| **Full suite command** | `cd backend && uv run pytest` ; `cd frontend && node_modules/.bin/vitest run` |
| **Estimated runtime** | backend ~20–40s (integration DB tests skip without Postgres) ; frontend ~10s |

> Env note (locked, see memory/CLAUDE.md): system Python has no pytest → backend tests run via
> `uv run pytest` / `uv run ruff`. `pnpm` not on PATH → frontend via `node_modules/.bin`.
> No Docker daemon in agent env → Postgres/Redis integration tests are authored but SKIP locally;
> the live concurrency / throttle / migration-applied checks are user-smokes (document in SUMMARY).

---

## Sampling Rate

- **After every task commit:** Run `cd backend && uv run pytest -q` (or the targeted test file)
- **After every plan wave:** Run the full backend suite + `vitest run`
- **Before `/gsd-verify-work`:** Full suite green (DB-integration skips allowed, as Phases 1–5)
- **Max feedback latency:** ~40 seconds

---

## Per-Task Verification Map

> Populated by the planner during planning (task IDs do not exist yet). Every LIMIT-0x task must
> map to an `<automated>` verify or a Wave 0 dependency. Key rows below are pre-seeded from research.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| {N}-0x | — | 0 | LIMIT-03 | — | Two concurrent create_reading at the boundary → exactly ONE succeeds, the other is limit-blocked (used never exceeds limit) | integration (2 committed AsyncSessions + `asyncio.gather`) | `uv run pytest backend/tests/.../test_limit_concurrency.py -q` | ❌ W0 | ⬜ pending |
| {N}-0x | — | 0 | LIMIT-02 | — | Rolling reset fires exactly at `now ≥ week_start + 7d`, re-anchors `week_start`, zeroes `free_used_this_week` (boundary + just-under) | unit/integration | `uv run pytest -k rolling_reset -q` | ❌ W0 | ⬜ pending |
| {N}-0x | — | 0 | LIMIT-04 | — | Throttle: Nth request inside the window → 429 BEFORE any PG/LLM work; TTL always set (Lua atomic INCR+EXPIRE), counter never stranded | integration (fakeredis/real Redis) | `uv run pytest -k throttle -q` | ❌ W0 | ⬜ pending |
| {N}-0x | — | 0 | LIMIT-05 | — | `determine_access` selects free → subscription → paid in order; only `free` non-zero this phase; consume hits only the chosen bucket | unit (pure fn) | `uv run pytest -k determine_access -q` | ❌ W0 | ⬜ pending |
| {N}-0x | — | 0 | LIMIT-01 | — | After 3 consumed, 4th create_reading → soft paywall body (200, `reason` + `reset_at`), limit NOT further decremented | integration | `uv run pytest -k paywall_block -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/integration/test_limit_concurrency.py` — boundary-race stub (LIMIT-03); MUST use two independent **committed** `AsyncSession`s + `asyncio.gather` (the existing single-connection savepoint harness CANNOT exercise cross-connection row locks — research Pitfall 3)
- [ ] `backend/tests/.../test_limits_reset.py` — rolling-reset boundary stubs (LIMIT-02)
- [ ] `backend/tests/.../test_throttle.py` — Redis throttle gate stubs (LIMIT-04); fakeredis or a real Redis fixture
- [ ] `backend/tests/.../test_determine_access.py` — bucket-order stubs (LIMIT-05)
- [ ] `backend/tests/.../test_paywall_block.py` — exhaustion → paywall body + refund-on-failure stubs (LIMIT-01); assert `test_limit_untouched_on_*` (Phase-4) stay green under the new consume-as-gate + refund order
- [ ] New fixture in `conftest.py` — two-committed-session factory for true concurrency

*Mutation-test the atomicity: break the conditional `WHERE free_used_this_week < free_weekly_limit` and confirm the concurrency test then observes `used == 4` (proves the test is load-bearing, not vacuous).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Migration applied (`week_start` TIMESTAMP + `user_id` UNIQUE) self-heals existing rows | LIMIT-02/D-02 | No Docker/Postgres in agent env | `cd backend && uv run alembic upgrade head` against a real DB, confirm columns/constraint |
| Live throttle under real burst (readings <10–15s apart → 429) | LIMIT-04 | Needs live Redis + timing | Fire rapid reading requests, observe 429 then recovery after window |
| Paywall sheet + countdown render in the real Mini App | LIMIT-01 | Telegram WebApp + live limit state | Exhaust 3 free, confirm soft paywall + correct reset countdown, no «AI»/fear copy |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (concurrency fixture is the critical one)
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
