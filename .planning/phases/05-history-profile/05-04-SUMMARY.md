---
phase: 05-history-profile
plan: 04
subsystem: backend
tags: [fastapi, sqlalchemy-async, history-crud, immutable-detail, soft-delete, restore, idor, hist-03, hist-04, prof-02, d-09, reversals-source]

# Dependency graph
requires:
  - phase: 05-history-profile
    provides: "05-01 red test substrate (test_readings_detail immutable/deleted-404/unknown-404/completed-status; test_readings_delete soft-delete/excluded-from-list/restore; test_readings_auth cross-user-IDOR-404; test_settings_patch reversals_source) + create_completed_reading/make_user_with_limits helpers + encode_jwt Bearer minting"
  - phase: 05-history-profile
    provides: "05-02 GET /api/readings list (the surface delete/restore reappearance assert against) + ReadingService.list_readings deleted_at-aware query + thin-router GET pattern"
  - phase: 05-history-profile
    provides: "05-03 PATCH /api/me/settings (persists user.reversals_enabled — the flag D-09 now sources the draw from)"
  - phase: 04-real-reading
    provides: "ReadingService.create_reading keystone + _build_response immutable mapper (reads summary_full JSON + reading_cards) + ReadingInputError->404 convention + CardDrawService reversals_enabled draw + get_current_user JWT gate + auth_session savepoint harness"
provides:
  - "ReadingService.get_reading_detail (user-scoped, deleted_at-aware, reuses _build_response — immutable, no regeneration)"
  - "ReadingService.soft_delete (sets deleted_at on the owned row; non-owned/already-deleted -> ReadingInputError)"
  - "ReadingService.restore (nulls deleted_at on the owned row; non-owned -> ReadingInputError)"
  - "GET /api/readings/{id}, DELETE /api/readings/{id}, POST /api/readings/{id}/restore thin routers (uuid path -> 422; ReadingInputError -> 404)"
  - "D-09 reversals source: create_reading draws with user.reversals_enabled (both draw + _persist_pending sites) — the persisted flag is authoritative, the request body is overridden"
affects: [05-06, reading-detail-screen, history-swipe-delete, undo-snackbar, reversals-source]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Immutable detail reuses the create path's _build_response mapper: reading_cards + summary_full JSON read back as-is, transient _card_title/_position_title labels rebuilt from explicit select(Card.title)/select(SpreadPosition.title) joins (no fresh draw, no lazy load, no regeneration)"
    - "User-scoped CRUD closes IDOR with 404 (not 403): where(id, user_id == user.id[, deleted_at IS NULL]); a non-owned or deleted id is indistinguishable from non-existent (no existence leak)"
    - "Soft delete = a deleted_at timestamp write (retain data, D-04); restore is a dedicated explicit POST .../restore that nulls it (no deleted_at column leaked over the API)"
    - "uuid.UUID-typed path params give a 422 on a malformed id from path validation before the service runs"

key-files:
  created: []
  modified:
    - "backend/app/services/reading.py"
    - "backend/app/api/readings.py"

key-decisions:
  - "Detail is IMMUTABLE and reuses _build_response (no second mapper, no regeneration): two GETs return byte-identical bodies; interpretation/short_meaning/mystical_accent come straight off the persisted reading_cards and the five summary fields from summary_full JSON"
  - "IDOR (the phase HIGH threat T-05) is closed with 404 not 403: a non-owned id and a deleted id both raise ReadingInputError -> 404 so existence is never leaked"
  - "Restore is a dedicated POST /api/readings/{id}/restore (RESEARCH Open Question 1) rather than a PATCH exposing deleted_at — explicit undo intent, no internal column over the wire"
  - "D-09: create_reading sources reversals_enabled from the PERSISTED user.reversals_enabled for BOTH the draw and _persist_pending; ReadingCreate.reversals_enabled stays an accepted field for backward compatibility but the persisted flag wins (after PATCH reversals_enabled=false a new reading is upright-only)"
  - "The crisis/abusive short-circuit FAILED row also records user.reversals_enabled (not the body) so the column is consistent with D-09 even on the no-draw path"
  - "No Reading.cards relationship added (Pitfall 1): detail loads reading_cards + labels via explicit selects, the established codebase style"

patterns-established:
  - "Detail/delete/restore live as three more thin routers in readings.py, each deriving the user from get_current_user and mirroring the POST handler's ReadingInputError -> 404 mapping; the literal GET /readings list is declared before the /{reading_id} routes so they never shadow"
  - "_titles_by_id(session, model, ids) -> {id: title} is the small explicit-select helper that rebuilds the authoritative card/position labels _build_response expects, sourced from the persisted joins"

requirements-completed: [HIST-03, HIST-04, PROF-02]

# Metrics
duration: 12min
completed: 2026-06-14
---

# Phase 5 Plan 04: Immutable Detail + Soft-Delete + Restore + D-09 Reversals Source Summary

**The backend history CRUD is complete: `GET /api/readings/{id}` serves the immutable stored reading by reusing the create path's `_build_response` mapper (no regeneration — two GETs are byte-identical), `DELETE /api/readings/{id}` soft-deletes via `deleted_at` (retain-data) with a dedicated `POST /api/readings/{id}/restore` undo, every path is JWT-user-scoped so a cross-user or deleted id is a 404 (closing the phase's HIGH IDOR threat), and `create_reading` now sources the draw's `reversals_enabled` from the persisted `user.reversals_enabled` (D-09) — turning the 05-01 detail/delete/restore + cross-user-IDOR + reversals-source red tests green (clean-skip without Postgres) with zero new dependencies.**

## What Was Built

### Task 1 — `ReadingService`: detail + soft-delete + restore + D-09 (`889630f`)

- **`get_reading_detail(session, user, reading_id) -> ReadingOut`** — `select(Reading).where(id, user_id == user.id, deleted_at IS NULL)`; `None` → `ReadingInputError`. Loads `reading_cards` via explicit `select(...).order_by(position_index)`, rebuilds the transient `_card_title`/`_position_title` labels `_build_response` expects from explicit `select(Card.title)` / `select(SpreadPosition.title)` joins (new `_titles_by_id` helper), and returns `self._build_response(reading, cards, remaining=None)`. **No LLM call, no re-draw** — interpretation/summary read straight off the persisted rows + `summary_full` JSON.
- **`soft_delete(session, user, reading_id) -> None`** — `select(Reading).where(id, user_id == user.id)`; `None` OR `deleted_at is not None` → `ReadingInputError`; sets `deleted_at = datetime.now(UTC)`; commits. Never hard-deletes (D-04).
- **`restore(session, user, reading_id) -> None`** — same user-scoped lookup; `None` → `ReadingInputError`; sets `deleted_at = None`; commits.
- **D-09 reversals source** — `create_reading` now resolves `reversals_enabled = user.reversals_enabled` and passes it to BOTH `CardDrawService.draw(...)` and `_persist_pending(...)` (signature extended to record the resolved flag onto `readings.reversals_enabled`). The crisis/abusive short-circuit FAILED row records `user.reversals_enabled` too. `ReadingCreate.reversals_enabled` remains an accepted field but the persisted user flag is authoritative.

### Task 2 — three thin routers in `readings.py` (`51380e2`)

- `@router.get("/readings/{reading_id}", response_model=ReadingOut)` → `get_reading_detail`; `reading_id: uuid.UUID` so a malformed id is a 422 (V5).
- `@router.delete("/readings/{reading_id}", status_code=204)` → `soft_delete`.
- `@router.post("/readings/{reading_id}/restore", status_code=204)` → `restore`.
- Each derives the user from `get_current_user` (never the body) and maps `ReadingInputError` → `HTTPException(404, str(exc))` exactly like the POST handler. The literal `/readings` list stays declared before the `/{reading_id}` routes so FastAPI matches the static path first.

## Verification Evidence

- `uv run pytest -q` (full backend suite): **83 passed, 65 skipped, 1 warning** (the DB-touching integration tests — incl. the 4 target files — skip cleanly without Postgres; the warning is a pre-existing unrelated jwt-key-length test). No regression vs. the documented 83/65 baseline.
- `uv run pytest` on the four target files + `test_readings_list.py` + `test_readings_flow.py`: clean-skip, no collection errors.
- `uv run ruff check app/services/reading.py app/api/readings.py`: **All checks passed.**
- Route registration (test env): `GET/POST /api/readings`, `GET/DELETE /api/readings/{reading_id}`, `POST /api/readings/{reading_id}/restore` — list does not shadow the parametrized routes.
- Plan grep checks: `user_id == user.id` present in detail/delete/restore (lines 401/471/493) + list (315); `user.reversals_enabled` sourced (225 → draw 849); **no `Reading.cards` relationship** (only a confirming comment).
- **Logic validation (throwaway, not committed):** a fake-`AsyncSession` harness (no DB engine, no new deps — the real models use PG-native ARRAY/ENUM and `aiosqlite` is unavailable) exercised all branches: owned detail → immutable `ReadingOut` with reconstructed labels + no commit; non-owned/deleted detail → `ReadingInputError`; soft_delete sets `deleted_at` + commits, already-deleted/non-owned → error no commit; restore nulls `deleted_at` + commits, non-owned → error; D-09 draw seam receives `user.reversals_enabled` (req ignored). All 11 assertions passed; harness deleted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Consistency] crisis/abusive short-circuit row records the persisted reversals flag**
- **Found during:** Task 1 (D-09 wiring)
- **Issue:** `_short_circuit` persisted the FAILED parent row with `reversals_enabled=req.reversals_enabled`, leaving the column sourced from the (now non-authoritative) request body on the no-draw path — inconsistent with D-09.
- **Fix:** sources it from `user.reversals_enabled` (the persisted flag) like the draw path; a short-circuited reading never draws, so this is purely a consistency fix on the recorded column.
- **Files modified:** `backend/app/services/reading.py`
- **Commit:** `889630f`

## Deferred Issues (out of scope)

Logged to `.planning/phases/05-history-profile/deferred-items.md` (NOT fixed here — not caused by this plan's changes):

- `backend/app/models/spread.py:38,56` — `ruff UP037` (quotes on forward-ref type annotations). Pre-existing since Phase 2; the file is not in this plan's touched set. Auto-fixable; safe to clean up in a chore or the Phase-5 code-review pass.

## Known Stubs

None — both endpoints are fully wired to real persisted data; no placeholder/empty-data paths introduced.

## Threat Flags

None — no new security surface beyond the planned `threat_model`. The new routes are exactly the three the register covers (T-05-IDOR-GET/DEL mitigated with user-scoped 404s, T-05-LEAK mitigated by reusing `ReadingOut` which excludes internal columns, T-05-SOFTDEL mitigated by `deleted_at IS NULL` on detail + restore-only un-delete + no hard delete).

## For the Next Plan

- **05-06 (reading detail screen / reopen):** `GET /api/readings/{id}` returns the SAME `ReadingOut` contract `ResultScreen` renders via `MockReading` — the reopen (D-02 fade-in, no re-ritual) is a mechanical data-source swap; the body is immutable so it can be cached/re-fetched freely.
- **Swipe-to-delete + undo snackbar (D-03):** `DELETE /api/readings/{id}` (204) hides the row; `POST /api/readings/{id}/restore` (204) brings it back within the undo window — both 404 on a non-owned/unknown id.
- **Reversals:** a new reading already honors the persisted `user.reversals_enabled` (set via 05-03 `PATCH /api/me/settings`); the frontend reversals toggle does not need to send `reversals_enabled` in the POST body anymore (it is ignored), though the field stays accepted.

## Self-Check: PASSED

- Created files exist: `05-04-SUMMARY.md`, `deferred-items.md` — FOUND.
- Modified files exist: `backend/app/services/reading.py`, `backend/app/api/readings.py` — FOUND.
- Commits exist: `889630f` (Task 1), `51380e2` (Task 2) — FOUND.
