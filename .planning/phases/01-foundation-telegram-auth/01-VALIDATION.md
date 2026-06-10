---
phase: 1
slug: foundation-telegram-auth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `01-RESEARCH.md` → `## Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio + httpx AsyncClient (ASGITransport) |
| **Config file** | `backend/pyproject.toml` ([tool.pytest.ini_options]) — installed in Wave 0 |
| **Quick run command** | `cd backend && pytest -q tests/unit` |
| **Full suite command** | `cd backend && pytest -q` |
| **Estimated runtime** | ~20–40 seconds (unit + auth integration against test DB) |

DB for tests: ephemeral PostgreSQL via docker-compose service (or testcontainers); Redis via compose. `alembic upgrade head` runs against the test DB in a session fixture.

---

## Sampling Rate

- **After every task commit:** Run `pytest -q tests/unit`
- **After every plan wave:** Run `pytest -q` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green + `alembic upgrade head` clean + `docker compose up` healthcheck 200
- **Max feedback latency:** 40 seconds

---

## Per-Task Verification Map

> Refined by planner/executor as PLAN.md tasks are created. Representative coverage of phase success criteria:

| ID | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|----|-------------|-----------------|-----------|-------------------|--------|
| initdata-valid | AUTH-01/02/03/04 | valid initData → 200 + JWT + user upserted; telegram_id from validated data only | integration | `pytest -q tests/integration/test_auth.py::test_valid_initdata` | ⬜ pending |
| initdata-forged | AUTH-02 | forged `hash` → 401 | integration | `pytest -q tests/integration/test_auth.py::test_forged_hash` | ⬜ pending |
| initdata-tampered | AUTH-02 | tampered field (hash recomputed mismatch) → 401 | integration | `pytest -q ...::test_tampered_field` | ⬜ pending |
| initdata-stale | AUTH-02 | stale `auth_date` beyond freshness window → 401 | integration | `pytest -q ...::test_stale_auth_date` | ⬜ pending |
| jwt-bearer | AUTH-04 | protected route rejects missing/invalid Bearer (401), accepts valid | integration | `pytest -q ...::test_bearer_dependency` | ⬜ pending |
| admin-allowlist | AUTH-05 | non-allowlisted telegram_id → 403 on admin probe; allowlisted → 200 | integration | `pytest -q tests/integration/test_admin.py` | ⬜ pending |
| healthz | INFRA-04 | `GET /healthz` → 200 with DB+Redis reachable | integration | `pytest -q ...::test_healthz_ok` | ⬜ pending |
| secret-failfast | INFRA-04 | missing required secret → app fails to start (ValidationError) | unit | `pytest -q tests/unit/test_settings.py` | ⬜ pending |
| admin-ids-parse | INFRA-04 | `ADMIN_TELEGRAM_IDS=111,222` parses to [111,222] (NoDecode), not JSON crash | unit | `pytest -q tests/unit/test_settings.py::test_admin_ids` | ⬜ pending |
| migration-schema | INFRA-02 | `alembic upgrade head` creates all 16 tables (+ topics) with key uniques | integration | `pytest -q tests/integration/test_migration.py` | ⬜ pending |
| seed-counts | INFRA-03 | seed loads exactly 7 topics, 6 decks, 7 spreads, 78 cards, N prompt templates; re-run idempotent | integration | `pytest -q tests/integration/test_seed.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] pytest + pytest-asyncio + httpx installed (`backend/pyproject.toml` test deps)
- [ ] `tests/conftest.py` — shared fixtures: async DB session, app client (ASGITransport), Redis, and a deterministic `make_init_data(bot_token, user, auth_date)` helper that produces correctly-signed initData
- [ ] `tests/unit/` + `tests/integration/` test stubs for AUTH-01..05, INFRA-02/03/04

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Mini App opens inside real Telegram and authenticates | AUTH-01 | Requires real Telegram WebView + BotFather Mini App URL | Open the bot's Mini App on a device/Telegram Desktop; confirm authenticated state renders; check backend logs for 200 on /api/auth/telegram |
| `docker compose up` cold boot | INFRA-01 | Full-stack smoke across containers | Run `docker compose up`; confirm Postgres+Redis+backend healthy and `/healthz` 200 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
