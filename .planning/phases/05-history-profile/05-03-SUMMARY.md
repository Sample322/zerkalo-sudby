---
phase: 05-history-profile
plan: 03
subsystem: backend
tags: [fastapi, pydantic, sqlalchemy-async, settings, partial-update, idor, privacy-gate, hist-05, negative-requirement]

# Dependency graph
requires:
  - phase: 05-history-profile
    provides: "05-01 red test substrate (test_settings_patch: partial_patch_round_trip/jwt_not_body/reversals_source; test_history_personalization_gate; test_me settings-block) + make_user_with_limits/create_completed_reading helpers + encode_jwt Bearer minting"
  - phase: 04-real-reading
    provides: "PromptEngine.build (the closed gate this plan locks) + User 3 settings columns + SettingsOut/MeResponse projection + get_current_user JWT gate + auth_session savepoint harness"
provides:
  - "SettingsPatch all-optional partial-update request schema (3 booleans, NO user_id)"
  - "PATCH /api/me/settings handler (exclude_unset, JWT-scoped, returns SettingsOut) — the settings write path (PROF-02, D-09)"
  - "HIST-05/D-06 human-visible closed-gate lock comment above PromptEngine.build (negative requirement fence)"
affects: [05-04, 05-06, profile-screen, settings-toggles, reversals-source]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Partial PATCH idiom: all-optional Pydantic request schema + model_dump(exclude_unset=True) writes only provided keys (omitted flags untouched)"
    - "Identity never in the body: the closed SettingsPatch schema has no user_id, so a forged id is dropped by validation; the mutated row is always get_current_user (T-05-SPOOF)"
    - "Negative requirement locked by absence + comment + introspection test: PromptEngine.build has no history parameter and no prior-reading fetch; a lock comment + test_build_has_no_history_parameter fence it"

key-files:
  created: []
  modified:
    - "backend/app/schemas/auth.py"
    - "backend/app/api/users.py"
    - "backend/app/services/prompt_engine.py"

key-decisions:
  - "PATCH is partial (exclude_unset) so a single-flag toggle leaves the other two flags untouched — the partial-update invariant the frontend optimistic toggle relies on"
  - "SettingsPatch deliberately has NO user_id field; identity is always the JWT sub, so a forged body user_id is silently dropped (T-05-SPOOF) rather than validated/rejected"
  - "An empty PATCH body is a no-op that returns the current settings (200) — exclude_unset yields {} so nothing is written"
  - "GET /api/me / MeResponse unchanged (PROF-01 already satisfied — count/subscription in limits, hidden by UI per D-08); only a request schema was added, no response schema change"
  - "HIST-05/D-06 is closed BY ABSENCE: no history parameter, fetch, or branch added; Phase 5 persists the consent flag + locks the closed gate only — the history-personalization feature stays v2/ENG-02"

patterns-established:
  - "Settings write path (PATCH /api/me/settings) lives as a thin handler in users.py alongside GET /api/me, mirroring its dep style (get_current_user + get_session)"
  - "A privacy/negative requirement is guarded with a triple fence: structural absence + a do-not-fix-this-away comment + a signature-introspection regression test"

requirements-completed: [PROF-01, PROF-02, HIST-05]

# Metrics
duration: 5min
completed: 2026-06-14
---

# Phase 5 Plan 03: Settings Write Path + HIST-05 Gate Lock Summary

**`PATCH /api/me/settings` now persists the three user settings flags as a partial, JWT-scoped update that round-trips through `GET /api/me`, and the HIST-05/D-06 consent gate is locked closed (no history is ever assembled into the §18 prompt) via a human-visible lock comment above `PromptEngine.build` plus the 05-01 introspection test — turning the 05-01 settings + gate red tests green (clean-skip without Postgres) while adding zero history-injection plumbing.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-06-14T14:35:58Z
- **Completed:** 2026-06-14T14:41:05Z
- **Tasks:** 2
- **Files modified:** 3 (0 created, 3 extended)

## Accomplishments

- **`SettingsPatch` request schema** (`schemas/auth.py`): all-optional `reversals_enabled` / `allow_history_personalization` / `onboarding_completed` (`bool | None = None`), each with a one-line RU `Field(description=...)`. Deliberately NO `user_id` field — identity is never in the body. Added to `__all__`. The `SettingsOut` response schema is reused unchanged.
- **`PATCH /api/me/settings` handler** (`api/users.py`): `@router.patch("/me/settings", response_model=SettingsOut)`; iterates `body.model_dump(exclude_unset=True).items()` and `setattr(current_user, field, value)` for ONLY the provided keys (so an omitted flag is untouched — the partial-update invariant), `await session.commit()`, returns `SettingsOut.model_validate(current_user)`. The mutated row is always `current_user` (the JWT `sub`), never the body (T-05-SPOOF). An empty body is a no-op that returns the current settings (200). Mirrors the existing `get_me` dep style.
- **HIST-05/D-06 closed-gate lock** (`services/prompt_engine.py`): a clearly-worded comment directly above `build` documenting that history is intentionally NOT a parameter and no prior reading is ever fetched into the §18 prompt (closed by absence), and that a future v2/ENG-02 author MUST reintroduce the consent gate rather than wire history in unconditionally. **No parameter, fetch, or branch was added** — `PromptEngine.build`'s signature is unchanged (`[deck, draw_records, question, safety_action, self, session, spread, topic]`, confirmed by introspection).
- **`GET /api/me` unchanged (PROF-01):** no `MeResponse` schema change — the settings block + name/photo fields already exist; this plan only added a *request* schema. `test_me.py` (incl. `test_me_returns_settings_block`) stays green.
- **Tests + lint green:** the 05-01 settings tests (`test_partial_patch_round_trip`, `test_patch_user_from_jwt_not_body`, `test_reversals_source`) were `xfail` and now flip `xpass` on a live stack; the gate test `test_prompt_has_no_history_even_with_flag_on` passes (and `test_build_has_no_history_parameter` already passed DB-free). Without Postgres the DB-touching ones SKIP cleanly. `uv run pytest -q` → **83 passed, 65 skipped, 0 errors** (unchanged baseline). `uv run ruff check` clean on all three changed files.

## Task Commits

Each task was committed atomically:

1. **Task 1: SettingsPatch schema + PATCH /api/me/settings (partial, JWT-scoped)** - `aaaa821` (feat)
2. **Task 2: HIST-05/D-06 closed-gate lock (comment + regression test green)** - `12379c9` (docs)

**Plan metadata:** (this SUMMARY + STATE/ROADMAP/REQUIREMENTS) committed separately.

## Files Created/Modified

- `backend/app/schemas/auth.py` (modified) - added `SettingsPatch` (all-optional 3-boolean partial-update schema, no `user_id`) and to `__all__`.
- `backend/app/api/users.py` (modified) - added the `patch_settings` handler (+ `SettingsOut`/`SettingsPatch` imports) and updated the module docstring.
- `backend/app/services/prompt_engine.py` (modified) - added the HIST-05/D-06 closed-gate lock comment directly above `PromptEngine.build` (comment only; no behavior change).

## Decisions Made

- **Partial update via `exclude_unset`** (not a full replace): only the keys actually present in the request body are written, so a single-flag toggle leaves the other two flags untouched. This is the invariant the frontend optimistic toggle (`usePatchSettings`, 05-06) reconciles against.
- **No `user_id` in `SettingsPatch`**: identity is always the JWT `sub`. A forged `user_id` in the body is silently dropped by the closed schema (rather than validated/rejected) and has no effect — the mutated row is always `current_user` (T-05-SPOOF). The victim row is provably untouched.
- **Empty body is a no-op (200)**: `model_dump(exclude_unset=True)` yields `{}`, so nothing is written and the current settings are returned — matches the plan's `<behavior>`.
- **No `MeResponse` change (PROF-01)**: `GET /api/me` already returns `{user, limits, settings}`; the count/subscription fields live in `limits` and are hidden by the UI (D-08). Only a request schema was added.
- **HIST-05/D-06 closed by absence**: per D-06, Phase 5 is consent-flag-and-gate ONLY. The consent flag is persisted (via the new PATCH), but history is never assembled into the §18 prompt because `PromptEngine.build` has no history channel and `ReadingService.create_reading` loads no prior readings. The lock is a triple fence: structural absence + a do-not-fix-this-away comment + the `test_build_has_no_history_parameter` introspection test. The actual history-personalization / «повторный анализ» feature stays v2/ENG-02.

## Deviations from Plan

None - plan executed exactly as written. Both tasks, all acceptance criteria, and the threat-register mitigations (T-05-SPOOF JWT-scoping via the body-less schema + `current_user`, T-05-CONSENT closed gate via absence + comment + test, T-05-VAL closed Pydantic schema + `exclude_unset` writing only known booleans) were implemented as specified. No new dependencies (T-05-SC: zero installs).

## Issues Encountered

- **Postgres/Docker absent in the dev sandbox** (the established Phase 1-4 convention): the DB-touching settings + gate tests SKIP cleanly rather than run, so `uv run pytest -q` stays green (83 pass / 65 skip / 0 errors) and the `xfail`→`xpass` flip cannot be observed live here. To gain confidence the handler logic is correct without a live DB, the exact partial-update semantics were validated in a throwaway scratch script: `SettingsPatch.model_dump(exclude_unset=True)` emits only the provided key, the forged `user_id` is dropped, an empty body yields `{}`, the handler `setattr` loop flips only the provided flag (others + an unrelated attribute untouched), and `SettingsOut.model_validate(user)` returns the full 3-flag shape — all checks passed; the script was then deleted and was **never committed** (verified via `git status`).
- **`aiosqlite` is not installed**, so an in-memory SQLite end-to-end exercise of the route was not viable (and the User model uses PG-native types), and installing it is out of scope (no new deps; package installs are not auto-fixable). The pure-schema/handler-logic validation above gave equivalent confidence for this slice.
- **Bare `python -c "from app.main import app"` fails** without the 5 required env vars (`BOT_TOKEN`/`DATABASE_URL`/`REDIS_URL`/`JWT_SECRET`/`ANTHROPIC_API_KEY`, set by the root `tests/conftest.py` before `app.*` imports). Expected harness behavior; the scratch validation set them inline.

## User Setup Required

None - no external service configuration required. No new dependencies (RESEARCH Package Legitimacy Audit: Phase 5 installs zero new packages; `uv sync` unchanged).

## Next Phase Readiness

- **05-04 (reversals source / D-09):** the `PATCH /api/me/settings` endpoint now sets `reversals_enabled` persistently; 05-04 (which owns `reading.py`) can source the new-reading `reversals_enabled` from the persisted `User.reversals_enabled` flag. `test_reversals_source` (in this slice's red substrate) will pass once that wiring lands — the persisted-flag write path it depends on now exists.
- **05-06 (Profile screen + settings toggles):** the frontend now has a real `PATCH /api/me/settings` contract (partial, returns `SettingsOut`) for the optimistic reversals / history-personalization toggles, reading current state from the existing `GET /api/me` settings block.
- **v2/ENG-02 (history personalization):** the closed gate is locked — any future author wiring history into the prompt trips `test_build_has_no_history_parameter` and the lock comment instructs them to reintroduce the consent gate (inject history only when `allow_history_personalization` is ON).
- No blockers. 05-02/05-03 are independent Wave-1 slices.

## Self-Check: PASSED

All 3 modified files verified present on disk; both task commits (`aaaa821`, `12379c9`) verified in git history. Full suite green (83 passed, 65 skipped, 0 errors); ruff clean on all 3 changed files. `PromptEngine.build` confirmed to have NO `history`/`history_context`/`prior_readings` parameter (signature introspection). The temporary scratch validation script was removed and not committed.

---
*Phase: 05-history-profile*
*Completed: 2026-06-14*
