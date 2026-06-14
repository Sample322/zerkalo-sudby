---
phase: 5
slug: history-profile
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-14
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `05-RESEARCH.md` → Validation Architecture. Task IDs are filled in at execution time (plans not yet written); rows are keyed by requirement. No LLM/network in this phase — backend tests use the in-process ASGI harness with `FakeLLM`/`FakeSafety`; frontend uses vitest with mocked `apiFetch`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (backend)** | pytest >=8 + pytest-asyncio (`asyncio_mode = "auto"`) + httpx ASGITransport (in-process, no live server) |
| **Framework (frontend)** | vitest ^3 + @testing-library/react ^16 |
| **Config file (backend)** | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths=["tests"]`) |
| **Config file (frontend)** | existing vitest config |
| **Quick run command (backend)** | `cd backend && uv run pytest tests/integration/test_readings_list.py -x -q` (per-slice file) |
| **Quick run command (frontend)** | vitest on the slice's new screen test file |
| **Full suite command** | `cd backend && uv run pytest -q` + `cd frontend && node node_modules/vitest/vitest.mjs run` |
| **Estimated runtime** | ~20–30s backend (DB integration skips without Postgres) + ~5s frontend |

> Env note: backend deps live in the `uv` venv → use `uv run`; `pnpm` is not on PATH → frontend via the local vitest binary. Postgres/Docker absent → DB-touching integration tests skip cleanly (established Phase 1–4 convention).

---

## Sampling Rate

- **After every task commit:** the slice's own test file (`uv run pytest tests/integration/test_readings_list.py -x` for the list slice; the screen's vitest file for an FE slice).
- **After every plan wave:** full backend `uv run pytest -q` + full frontend `vitest run` green (baseline 82 pass / 49 skip backend, 80 pass frontend — new tests added on top).
- **Before `/gsd-verify-work`:** full suite green.
- **Max feedback latency:** ~30 seconds.

---

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists |
|-------------|----------|-----------|-------------------|-------------|
| HIST-01 | A completed reading then appears in `GET /api/readings` | integration | `uv run pytest tests/integration/test_readings_list.py -k auto_save -x` | ❌ W0 |
| HIST-02 | List returns light items (date/question/deck/spread/thumbnails/short summary), newest-first; NO full interpretation | integration | `... test_readings_list.py -k shape_and_order -x` | ❌ W0 |
| HIST-03 | `GET /api/readings/{id}` returns the immutable reading; a 2nd call is identical (no regen) | integration | `... test_readings_detail.py -k immutable -x` | ❌ W0 |
| HIST-04 | `DELETE` sets `deleted_at`; row gone from list AND `GET /{id}` 404s; restore unsets it and it reappears | integration | `... test_readings_delete.py -x` | ❌ W0 |
| HIST-04 | Soft-deleted reading EXCLUDED from list (core invariant) | integration | `... test_readings_delete.py -k excluded_from_list -x` | ❌ W0 |
| HIST-05 | Prompt contains NO history even when `allow_history_personalization=True` (closed gate) | integration | `... test_history_personalization_gate.py -x` | ❌ W0 |
| HIST-06 | A free user with 12 completed readings sees only the last 10; older rows remain in the DB (fetchable by id) | integration | `... test_readings_list.py -k last_ten_cap -x` | ❌ W0 |
| HIST-02/04 | Cross-user isolation (IDOR): user B's id → 404 on `GET /{id}` and `DELETE` | integration | `... test_readings_auth.py -k cross_user -x` | ⚠️ extend |
| PROF-01 | `GET /api/me` returns `{user, limits, settings}` (name/photo + settings; no schema change) | integration | extend `test_me.py` | ⚠️ extend |
| PROF-02 | `PATCH /api/me/settings` partial-updates each flag; round-trips via `GET /api/me`; JWT-scoped (body user_id ignored) | integration | `... test_settings_patch.py -x` | ❌ W0 |
| PROF-02 | New-reading `reversals_enabled` sourced from the persisted user flag (D-09) | integration | `... test_settings_patch.py -k reversals_source -x` | ❌ W0 |
| HIST-02 | History list-item renders date/question/deck/spread/thumbnails/short summary; empty state = §9.6 copy | component | vitest `HistoryScreen.test.tsx` | ❌ W0 |
| HIST-04 | Swipe → optimistic remove + undo snackbar; undo restores the cached item | component | vitest `HistoryScreen.delete.test.tsx` | ❌ W0 |
| HIST-03 | Reopen → `ResultScreen` detail with fade-in (no ritual chrome) | component | vitest `ResultScreen` detail test | ⚠️ extend |
| PROF-02 | Settings toggles optimistic-update + call `PATCH`; readings-count/subscription block NOT rendered (D-08) | component | vitest `ProfileScreen.test.tsx` | ❌ W0 |
| SAFE-06 | All new history/profile/settings copy passes `BANNED_BRAND_TOKENS` | unit | extend `copy.test.ts` | ⚠️ extend |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## The 4 load-bearing invariants (each needs a dedicated automated test)

1. **Soft-deleted excluded from list** (HIST-04) — delete then list omits the row.
2. **Last-10 cap retains data** (HIST-06) — 12 completed readings → list returns 10, the 11th/12th still fetchable by id (retained, NOT pruned).
3. **Settings round-trip** (PROF-02) — `PATCH` then `GET /api/me` reflects it; partial patch leaves other flags untouched.
4. **Consent gate keeps history out of the prompt** (HIST-05) — assembled prompt has no prior-reading content even with `allow_history_personalization=True` (trivially true today since no history path exists; the test LOCKS it).

---

## Wave 0 Requirements

- [ ] `backend/tests/integration/test_readings_list.py` — HIST-01/02/06 (auto-save visible, light shape + order, last-10 cap)
- [ ] `backend/tests/integration/test_readings_detail.py` — HIST-03 immutability (two GETs identical; deleted → 404)
- [ ] `backend/tests/integration/test_readings_delete.py` — HIST-04 soft-delete + restore + excluded-from-list
- [ ] `backend/tests/integration/test_history_personalization_gate.py` — HIST-05 negative-requirement lock
- [ ] `backend/tests/integration/test_settings_patch.py` — PROF-02 partial update + round-trip + reversals-source
- [ ] Extend `backend/tests/integration/test_me.py` — PROF-01 (settings block present, no schema change)
- [ ] Extend `backend/tests/integration/test_readings_auth.py` — cross-user 404 on detail/delete (IDOR)
- [ ] `frontend/src/components/history/HistoryScreen.test.tsx` (+ delete/undo) and `frontend/src/components/profile/ProfileScreen.test.tsx`
- [ ] Extend `frontend/src/reading/copy.test.ts` — scan the new strings
- [ ] **Shared helper:** `create_completed_reading(session, user, ...)` integration helper (reuses `fake_service` = FakeSafety+FakeLLM, no Anthropic) so list/detail/delete tests don't re-drive the full POST
- Framework install: none — pytest + vitest already configured.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| History list + detail + swipe-delete/undo feel on a live device | HIST-02/03/04 | Touch gesture + animation feel; needs a running stack + Telegram | Open Mini App, run readings, browse history, swipe-delete + undo, reopen a reading |
| Profile shows Telegram name/photo; settings persist across reloads | PROF-01/02 | Needs real Telegram identity + live backend | Toggle reversals/personalization, reload, confirm persisted server-side |

*Backend invariants (soft-delete exclusion, last-10 cap, settings round-trip, consent gate, IDOR) all have automated integration tests — they skip only because Postgres is absent in the dev sandbox, and run on a live stack.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
