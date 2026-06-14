---
phase: 05-history-profile
plan: 01
subsystem: testing
tags: [pytest, integration-tests, xfail, fakes, idor, soft-delete, consent-gate, settings, history]

# Dependency graph
requires:
  - phase: 04-real-reading
    provides: "ReadingService keystone + FakeSafety/FakeLLM + seeded_catalog + auth_session savepoint harness + ReadingOut/ReadingCreate contracts"
provides:
  - "create_completed_reading + make_user_with_limits shared integration helpers (FakeSafety+FakeLLM, no Anthropic)"
  - "Red test substrate for the GET/DELETE/restore /api/readings list+detail+delete endpoints (xfail until 05-02/05-04)"
  - "Red test substrate for PATCH /api/me/settings (xfail until 05-03)"
  - "HIST-05 closed-consent-gate regression lock (passes today)"
  - "Cross-user IDOR 404 lock + the 4 load-bearing invariants as named tests"
affects: [05-02, 05-03, 05-04, history-list, history-detail, soft-delete, profile-settings]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Wave-0 interface-first red tests: xfail(strict=False) per missing endpoint -> xpass on implementation; DB-touching tests skip cleanly without Postgres"
    - "Shared create_completed_reading helper drives the real ReadingService keystone with fakes injected (no inline POST re-drive, no Anthropic)"
    - "Bearer minted directly via encode_jwt(sub, telegram_id) for a make_user_with_limits user when the test needs a specific quota or a second (IDOR victim) account"
    - "Negative-requirement lock by signature introspection: assert PromptEngine.build has no history/history_context/prior_readings parameter (gate closed by absence)"

key-files:
  created:
    - "backend/tests/integration/_history_helpers.py"
    - "backend/tests/integration/test_readings_list.py"
    - "backend/tests/integration/test_readings_detail.py"
    - "backend/tests/integration/test_readings_delete.py"
    - "backend/tests/integration/test_history_personalization_gate.py"
    - "backend/tests/integration/test_settings_patch.py"
  modified:
    - "backend/tests/integration/test_readings_auth.py"
    - "backend/tests/integration/test_me.py"

key-decisions:
  - "Last-10-cap + IDOR tests mint a Bearer directly via encode_jwt for a make_user_with_limits user (rather than the /api/auth/telegram upsert) so the seeded readings and the JWT identity are guaranteed the same user / a distinct victim"
  - "HIST-05 gate is locked with a non-xfail signature-introspection test (build has no history param) + an xfail-free prompt-content assertion: the gate is 'closed by absence', so the lock passes today and stays green as a regression fence"
  - "reversals_source (D-09) asserts on the persisted reading_cards orientations (authoritative server-side draw state), sourcing reversals from the persisted user flag"

patterns-established:
  - "Wave-0 red substrate mirrors the Phase-4 04-01 pattern: every later endpoint slice has a precise xfail->xpass target before it is built"
  - "Non-test_-prefixed helper module (_history_helpers.py) so pytest does not collect it as tests"

requirements-completed: [HIST-01, HIST-02, HIST-03, HIST-04, HIST-05, HIST-06, PROF-01, PROF-02]

# Metrics
duration: 8min
completed: 2026-06-14
---

# Phase 5 Plan 01: Wave-0 Test Substrate Summary

**Shared `create_completed_reading` helper (FakeSafety+FakeLLM, no Anthropic) plus 5 new red backend test files + 2 extended files that lock the history list/detail/soft-delete, the closed consent gate, the settings round-trip, and cross-user IDOR as named xfail->xpass targets before any Phase-5 endpoint exists.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-06-14T14:11:23Z
- **Completed:** 2026-06-14T14:19:25Z
- **Tasks:** 3
- **Files modified:** 8 (6 created, 2 extended)

## Accomplishments

- **Shared integration helpers** (`_history_helpers.py`): `create_completed_reading` persists a COMPLETED reading + immutable `reading_cards` for a user by driving the real `ReadingService` keystone with `FakeSafety`/`FakeLLM` injected (no Anthropic, fake output matched to the seeded spread's `position_index` values), and `make_user_with_limits` inserts a User + UserLimits with a configurable high `free_weekly_limit` so the last-10-cap test can create 12 completed readings without tripping the Phase-4 quota gate. Reuses `_output_for_indices`/`_spread_position_indices` + `FakeLLM`/`FakeSafety` (single source of truth, no re-declaration).
- **The 4 load-bearing invariants each exist as a named test:** soft-delete-excluded-from-list (`test_excluded_from_list`), last-10-cap-retains-data (`test_last_ten_cap`), settings-round-trip (`test_partial_patch_round_trip`), consent-gate-keeps-history-out-of-prompt (`test_prompt_has_no_history_even_with_flag_on`).
- **Cross-user IDOR lock** (`test_cross_user_detail_and_delete_404`): user B's GET and DELETE on user A's reading id are each 404 (not 403, not 200) — the executable lock for the 05-02/05-04 endpoints (threat T-05-IDOR).
- **HIST-05 closed-gate regression fence:** `test_build_has_no_history_parameter` PASSES today (signature introspection — `PromptEngine.build` has no `history`/`history_context`/`prior_readings` param), and the prompt-content assertion proves no prior-reading text leaks even with `allow_history_personalization=True`.
- **PROF-01 settings block** (`test_me_returns_settings_block`, NOT xfail): asserts the live `GET /api/me` already returns `{user, limits, settings}` with all three flags + name/photo — no schema change required.
- **Full backend suite stays green:** `uv run pytest -q` -> 83 passed, 65 skipped, 0 collection errors, 0 failures (baseline was 82 pass / 49 skip; +1 pass from the gate-signature lock, +16 clean DB-dependent skips). `ruff check` clean on all 8 files.

## Task Commits

Each task was committed atomically:

1. **Task 1: Shared create_completed_reading helper** - `2ce4d53` (test)
2. **Task 2: List + last-10 cap + cross-user (IDOR) red tests** - `93ad048` (test)
3. **Task 3: Detail, delete/restore, consent-gate, settings, /me red tests** - `66889fc` (test)

**Plan metadata:** (this SUMMARY + STATE/ROADMAP/REQUIREMENTS) committed separately.

## Files Created/Modified

- `backend/tests/integration/_history_helpers.py` (created) - `create_completed_reading` + `make_user_with_limits`; not `test_`-prefixed so pytest does not collect it.
- `backend/tests/integration/test_readings_list.py` (created) - HIST-01/02/06: `test_auto_save_appears_in_list`, `test_shape_and_order`, `test_last_ten_cap` (all xfail until 05-02).
- `backend/tests/integration/test_readings_detail.py` (created) - HIST-03/04: `test_detail_immutable`, `test_detail_deleted_404`, `test_detail_unknown_id_404`, `test_detail_completed_status` (xfail until 05-02).
- `backend/tests/integration/test_readings_delete.py` (created) - HIST-04: `test_soft_delete_sets_deleted_at`, `test_excluded_from_list`, `test_restore_unsets_deleted_at` (xfail until 05-04).
- `backend/tests/integration/test_history_personalization_gate.py` (created) - HIST-05: `test_build_has_no_history_parameter` (passes today) + `test_prompt_has_no_history_even_with_flag_on`.
- `backend/tests/integration/test_settings_patch.py` (created) - PROF-02: `test_partial_patch_round_trip`, `test_patch_user_from_jwt_not_body`, `test_reversals_source` (xfail until 05-03).
- `backend/tests/integration/test_readings_auth.py` (modified) - added `test_cross_user_detail_and_delete_404` (IDOR, xfail).
- `backend/tests/integration/test_me.py` (modified) - added `test_me_returns_settings_block` (PROF-01, NOT xfail).

## Decisions Made

- **Direct-Bearer for quota-sensitive + IDOR tests:** `test_last_ten_cap` and `test_cross_user_detail_and_delete_404` mint a Bearer with `encode_jwt(sub=str(user.id), telegram_id=...)` for a `make_user_with_limits` user instead of authenticating through `/api/auth/telegram`. This guarantees the seeded readings belong to the JWT identity (cap test) and gives a distinct, untouched victim account (IDOR test) — both are impossible to express cleanly through the upsert-only auth path.
- **HIST-05 locked at the seam, not just the output:** the strongest fence against a future v2 silently wiring history in is `test_build_has_no_history_parameter` (signature introspection), which passes today and needs no DB. The prompt-content assertion is the behavioral backup.
- **reversals_source asserts persisted draw state:** `test_reversals_source` checks the persisted `reading_cards.orientation` values are all `upright` after opting out, since the orientation is authoritative server-side.

## Deviations from Plan

None - plan executed exactly as written.

(Note: during drafting, `test_last_ten_cap` was first sketched with a stray `make_user_with_limits.__wrapped__` line and an inline limits-bump; this was corrected to the plan-specified `make_user_with_limits(free_weekly_limit=100)` + direct Bearer before the first commit of Task 2. No committed code deviated from the plan.)

## Issues Encountered

- A bare `python -c "import ..."` of the helper fails because the test env vars (`BOT_TOKEN`/`DATABASE_URL`/etc.) are set by the root `tests/conftest.py` (`os.environ.setdefault`) before `app.*` is imported — not present under a raw interpreter. This is expected harness behavior; the authoritative check is `uv run pytest --collect-only`, which loads the root conftest first and collects cleanly. Not a code issue.
- Postgres/Docker is absent in the dev sandbox, so all DB-touching tests SKIP cleanly (the established Phase 1-4 convention). They run (xfail->xpass for endpoint-dependent ones; the gate prompt test PASS) on a live stack.

## User Setup Required

None - no external service configuration required. No new dependencies (RESEARCH Package Legitimacy Audit: Phase 5 installs zero new packages).

## Next Phase Readiness

- **05-02 (history list + detail):** precise red targets ready — `test_readings_list.py` (list shape/order + last-10 cap) and `test_readings_detail.py` (immutability + deleted-404) flip xfail->xpass when `GET /api/readings` + `GET /api/readings/{id}` land.
- **05-03 (profile settings):** `test_settings_patch.py` + `test_me_returns_settings_block` are the contract for `PATCH /api/me/settings`.
- **05-04 (soft delete + restore):** `test_readings_delete.py` + the IDOR test in `test_readings_auth.py` lock the delete/restore/exclusion/404 behavior.
- No blockers. The shared helper means the later slices do not re-drive `POST /api/readings` to seed history.

## Self-Check: PASSED

All 6 created files + 2 extended files verified present on disk; all 3 task commits (`2ce4d53`, `93ad048`, `66889fc`) verified in git history. Full suite green (83 passed, 65 skipped, 0 collection errors); ruff clean on all 8 files.

---
*Phase: 05-history-profile*
*Completed: 2026-06-14*
