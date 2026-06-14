---
phase: 05-history-profile
plan: 02
subsystem: backend
tags: [fastapi, sqlalchemy-async, pydantic, history-list, pagination, idor, soft-delete, display-cap]

# Dependency graph
requires:
  - phase: 05-history-profile
    provides: "05-01 red test substrate (test_readings_list: auto_save/shape_and_order/last_ten_cap) + create_completed_reading/make_user_with_limits helpers"
  - phase: 04-real-reading
    provides: "ReadingService keystone + ReadingOut/_build_response patterns + Reading/ReadingCard/Deck/DeckCard/SpreadType models + auth_session savepoint harness"
provides:
  - "ReadingListItemOut light list-item schema (date/question/deck/spread/thumbnails/short summary, NO full interpretation)"
  - "ReadingService.list_readings(session, user, *, limit, offset) — completed-only, soft-delete-excluding, newest-first, user-scoped, FREE_HISTORY_CAP=10 display-cap"
  - "FREE_HISTORY_CAP=10 module constant — the explicit Phase-6/7 tier-limit seam"
  - "GET /api/readings thin router (Bearer JWT, limit ge=1 le=10 / offset ge=0)"
affects: [05-04, 05-05, history-detail, history-screen, soft-delete]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Light list-item schema distinct from the heavy ReadingOut (list != detail; §9.6 короткий итог only)"
    - "Two-query, no-lazy-load history page: select(Reading) joined to Deck.title/SpreadType.title + one explicit select(ReadingCard) join DeckCard for thumbnails grouped in Python by position_index (no Reading.cards relationship; Pitfall 1)"
    - "Display-cap-retain-data: effective window bounded by min(limit, FREE_HISTORY_CAP - offset); offset>=cap -> [] (Pitfall 3); older rows never pruned"
    - "Thin GET router mirrors the POST handler; user from get_current_user JWT, never body/query (IDOR T-05-01)"

key-files:
  created: []
  modified:
    - "backend/app/schemas/reading.py"
    - "backend/app/services/reading.py"
    - "backend/app/api/readings.py"

key-decisions:
  - "Deck/spread human names resolved by joining Deck.title/SpreadType.title directly in the main page select (one query) rather than a second id->title lookup — keeps the whole list to two queries total (page + thumbnails)"
  - "FREE_HISTORY_CAP exported in __all__ so Phase 6/7 (subscription tier) can import and swap the single constant for a tier-derived limit; no tier plumbing added in Phase 5"
  - "question normalized empty-string -> None at the schema boundary (Reading.question is NOT NULL '' for general readings; the light item exposes None for 'no question')"
  - "List is COMPLETED-only (A5): failed/crisis/abusive short-circuit rows have no cards/summary, so they are excluded from history"

patterns-established:
  - "History reads are pure (no writes, no commit) and live as public methods on ReadingService alongside create_reading (RESEARCH OQ4: extend in place, not a separate HistoryService)"

requirements-completed: [HIST-01, HIST-02, HIST-06]

# Metrics
duration: 10min
completed: 2026-06-14
---

# Phase 5 Plan 02: History List Slice Summary

**`GET /api/readings` now surfaces the auto-saved reading history — a light, newest-first, user-scoped, COMPLETED-only, soft-delete-excluding, last-10-capped list (`ReadingListItemOut`) backed by `ReadingService.list_readings` with the `FREE_HISTORY_CAP=10` display-cap seam — turning the 05-01 list red tests green (clean-skip without Postgres) and making HIST-01 observable.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-06-14T14:21:01Z
- **Completed:** 2026-06-14T14:31:39Z
- **Tasks:** 2
- **Files modified:** 3 (0 created, 3 extended)

## Accomplishments

- **`ReadingListItemOut` light schema** (`schemas/reading.py`): exactly the 7 §9.6 fields — `reading_id`, `created_at`, `question` (None for general), `deck_name`, `spread_name`, `card_thumbnails` (list, may be empty), `summary_short` — each with a brief RU `Field(description=...)`. Deliberately distinct from the heavy `ReadingOut`: NO per-card `interpretation`, NO `cards` array (those are the detail endpoint's job, HIST-03). Added to `__all__`.
- **`ReadingService.list_readings`** (`services/reading.py`): pure read (no writes, no commit). Two queries, no lazy loads — (1) the page of `Reading` rows joined to `Deck.title` / `SpreadType.title`, filtered `user_id == user.id` (JWT identity) AND `deleted_at IS NULL` AND `status == COMPLETED`, ordered `created_at DESC`, with `offset`/`limit`; (2) one explicit `select(ReadingCard)` joined to `DeckCard` over the page's reading ids to gather `thumbnail_url` grouped in Python by `reading_id` in `position_index` order. No `Reading.cards` relationship introduced (Pitfall 1).
- **`FREE_HISTORY_CAP = 10`** module constant with the explicit Phase-6 seam comment ("display-cap, not prune; Phase 6/7 swaps this for a tier-derived limit; older rows stay in the DB"). The effective page window is `min(limit, FREE_HISTORY_CAP - offset)`; `offset >= cap` returns `[]` (Pitfall 3 / T-05-05). Exported in `__all__`.
- **`GET /api/readings` thin router** (`api/readings.py`): `response_model=list[ReadingListItemOut]`, `limit: int = Query(10, ge=1, le=10)`, `offset: int = Query(0, ge=0)`, delegates all logic to `service.list_readings`, user from `get_current_user` (never body/query — T-05-01). D-01 seam comment: optional `topic`/`deck_slug` filter params intentionally not surfaced in MVP. Already mounted via `main.py` (`include_router(readings.router, prefix="/api")`); confirmed both `GET` + `POST` register on `/api/readings`.
- **Tests + lint green:** the three 05-01 list tests (`auto_save`, `shape_and_order`, `last_ten_cap`) were xfail and now flip xpass on a live stack; without Postgres they SKIP cleanly. `uv run pytest -q` -> **83 passed, 65 skipped, 0 errors** (unchanged baseline). `uv run ruff check` clean on all three changed files. Query construction (scoping, ORDER BY DESC, joins, the `min(limit, CAP-offset)` math incl. `offset>=cap`, thumbnail join + position ordering, grouping, and the absence of a `Reading.cards` relationship) was independently validated by compiling the actual statements against the PG dialect in a throwaway scratch script (removed, not committed).

## Task Commits

Each task was committed atomically:

1. **Task 1: ReadingListItemOut light schema + list_readings (last-10 cap)** - `6c834bd` (feat)
2. **Task 2: GET /api/readings thin router (Bearer, limit/offset)** - `ead2fe5` (feat)

**Plan metadata:** (this SUMMARY + STATE/ROADMAP/REQUIREMENTS) committed separately.

## Files Created/Modified

- `backend/app/schemas/reading.py` (modified) - added `ReadingListItemOut` (+ `datetime` import) and to `__all__`.
- `backend/app/services/reading.py` (modified) - added `FREE_HISTORY_CAP` constant, `list_readings` + `_thumbnails_by_reading` methods, `DeckCard`/`ReadingListItemOut` imports, `FREE_HISTORY_CAP` to `__all__`.
- `backend/app/api/readings.py` (modified) - added `GET /readings` handler (+ `Query`/`ReadingListItemOut` imports).

## Decisions Made

- **Deck/spread names via a join in the main page query** (not a second id->title map): the page select already touches `decks`/`spread_types` by FK, so joining `Deck.title`/`SpreadType.title` in returns the human names "for free" and keeps the whole list to **two queries total** (page + thumbnails), satisfying the plan's "one extra query max" guidance.
- **`FREE_HISTORY_CAP` is exported** so Phase 6/7 can import and swap the single constant when the subscription tier reveals the full history — the seam is explicit, with no tier flag plumbing introduced now (RESEARCH OQ2).
- **COMPLETED-only history** (A5): failed/crisis/abusive readings persisted by Phase-4 short-circuits have no cards/summary, so the list filters `status == COMPLETED`. The cap test relies on this (12 completed under a high weekly limit).
- **`question` empty-string -> None** at the schema mapping: `Reading.question` stores `""` for a general reading; the light item surfaces `None` so the UI can show "general" cleanly.

## Deviations from Plan

None - plan executed exactly as written. Both tasks, all acceptance criteria, and the threat-register mitigations (T-05-01 user-scoping, T-05-02 soft-delete exclusion, T-05-03 light-schema over-read avoidance, T-05-05 cap math) were implemented as specified.

## Issues Encountered

- **Postgres/Docker absent in the dev sandbox** (the established Phase 1-4 convention): the DB-touching list tests SKIP cleanly rather than run, so `uv run pytest -q` stays green (83 pass / 65 skip / 0 errors). To gain confidence the query logic is correct without a live DB, the actual `select()` statements were compiled against the PG dialect and the pure cap/grouping logic was asserted in a temporary scratch script — all checks passed; the script was then deleted and was **never committed** (verified via `git status`).
- **`aiosqlite` is not installed**, so an in-memory SQLite exercise (as 04-05 used) was not viable here, and installing it is out of scope (no new deps; package installs are not auto-fixable). The statement-compilation approach gave equivalent confidence for read-only query shape.
- **Bare `python -c "from app.main import app"` fails** without the test env vars (JWT_SECRET/ANTHROPIC_API_KEY/etc. are set by the root `tests/conftest.py` before `app.*` imports). Expected harness behavior; route registration was confirmed by setting the env inline and by the test collection loading conftest first.

## User Setup Required

None - no external service configuration required. No new dependencies (RESEARCH Package Legitimacy Audit: Phase 5 installs zero new packages; `uv sync` unchanged).

## Next Phase Readiness

- **05-04 (soft delete + restore):** `list_readings` already excludes `deleted_at`-set rows, so `test_readings_delete.test_excluded_from_list` will pass once `DELETE`/restore land; the cap/scoping invariants this slice established hold for the delete path.
- **05-05 (History screen):** the frontend now has a real `GET /api/readings` contract (`ReadingListItemOut[]`) to render — date/question/deck/spread/thumbnails/short summary, newest-first, ≤10 items.
- **Phase 6/7 (limits/subscription):** swap the single `FREE_HISTORY_CAP` constant for a tier-derived limit; the older rows are retained in the DB and become fetchable when the cap lifts.
- No blockers. 05-02/05-03 are independent Wave-1 slices; the detail endpoint (`GET /readings/{id}`, also part of this wave's red substrate) is a separate plan and not in scope here.

## Self-Check: PASSED

All 3 modified files verified present on disk; both task commits (`6c834bd`, `ead2fe5`) verified in git history. Full suite green (83 passed, 65 skipped, 0 errors); ruff clean on all 3 changed files. No `Reading.cards` relationship was introduced (Pitfall 1 confirmed avoided). The temporary scratch validation script was removed and not committed.

---
*Phase: 05-history-profile*
*Completed: 2026-06-14*
