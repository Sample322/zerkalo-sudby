---
phase: 05-history-profile
verified: 2026-06-15T00:30:00Z
status: human_needed
score: 27/27 must-haves verified
overrides_applied: 0
mode: mvp
re_verification:
  previous_status: none
  previous_score: none
  note: "Initial verification — no prior VERIFICATION.md."
human_verification:
  - test: "Open the Mini App in Telegram, run a reading, then open History — the new reading appears with date / question / deck / spread / card thumbnails / short summary, newest-first."
    expected: "The just-completed reading is the top list item with all §9.6 fields populated and real card thumbnails."
    why_human: "Requires a live stack (Postgres + ANTHROPIC key + Telegram WebApp) to create a real reading and render the list end-to-end; the integration tests skip without Postgres."
  - test: "In History, reopen a past reading by tapping its card."
    expected: "ResultScreen detail mode renders the immutable stored cards/interpretation/summary with a soft opacity fade-in (no flip/reveal replay); content matches what was originally generated; back returns to History."
    why_human: "Animation feel + the immutable re-render against a real persisted reading need a live device; HIST-03 immutability code is verified by source + a (skipped-without-PG) integration test."
  - test: "In History, swipe a list card left past the threshold (or tap the ✕), then tap «Отменить» within ~5s; repeat and let the snackbar lapse without undoing."
    expected: "Swipe optimistically removes the card and shows the undo snackbar; «Отменить» restores it at its original slot; after ~5s the removal stands (server soft-deleted)."
    why_human: "Touch-gesture + 5s-timer feel and the optimistic delete/restore round-trip against the real DELETE / restore endpoints require a live device + backend."
  - test: "Open Profile; toggle reversals and history-personalization; reload the Mini App; reopen Profile."
    expected: "Profile shows the real Telegram name + photo; NO readings-count/subscription block; both toggles reflect the persisted server state after reload (settings round-trip via PATCH → GET /api/me)."
    why_human: "Real Telegram identity/photo + cross-reload server persistence need a live Telegram session and backend; PROF-01/02 logic is verified by source + the (skipped-without-PG) settings round-trip test."
---

# Phase 5: History & Profile Verification Report

**Phase Goal:** The user can revisit their journey — every reading auto-saves to a browsable, paginated history with detail view and soft delete (reading immutable stored cards, never regenerating) — and can manage their profile and settings, including the explicit opt-in before any history-based personalization.
**Verified:** 2026-06-15T00:30:00Z
**Status:** human_needed
**Mode:** mvp (user-journey phase)
**Re-verification:** No — initial verification.

## Environment Note

Windows dev host, NO Docker/Postgres and NO real Telegram/ANTHROPIC key. Per the established Phase 1-4 convention, DB-touching integration tests SKIP cleanly (verified skip reason: "Postgres unreachable for integration tests"). All code-level must_haves were therefore verified by READING the source (not trusting SUMMARY claims) and confirming the suites are green:

- Backend: **83 passed, 65 skipped** (`uv run pytest -q`) — matches expected baseline.
- Frontend: **101 passed** (`node node_modules/vitest/vitest.mjs run`) — matches expected baseline.

The four live-device behaviors (real identity/photo, settings persistence across reloads, history list/detail/swipe-delete feel) require a live stack → routed to human verification, NOT counted as gaps. This mirrors Phases 1-4 (status human_needed → user approves; live items listed).

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | A completed reading appears in `GET /api/readings` (HIST-01) | ✓ VERIFIED | `reading.py:list_readings` (L279-348) queries `Reading` scoped to user, COMPLETED, not-deleted, newest-first; route mounted `GET /api/readings`. Test `test_auto_save` + `test_last_ten_cap` (skip-w/o-PG). |
| 2  | List returns light items (date/question/deck/spread/thumbnails/short summary), newest-first, NO full interpretation (HIST-02) | ✓ VERIFIED | `ReadingListItemOut` (schemas/reading.py L285+) has only the 7 light fields, NO `interpretation`/`cards`; `order_by(created_at.desc())` L319; two-query thumbnail join (no lazy load). |
| 3  | Free user with 12 readings sees last 10; older RETAINED in DB (HIST-06) | ✓ VERIFIED | `FREE_HISTORY_CAP=10` (L117); `eff = min(limit, FREE_HISTORY_CAP - offset)` (L304) bounds window, no prune. `test_last_ten_cap` asserts 12→10 returned + oldest 2 still fetchable by id, `deleted_at IS NULL`. |
| 4  | Soft-deleted + non-COMPLETED rows excluded from list | ✓ VERIFIED | `where(deleted_at.is_(None), status == COMPLETED)` (L316-317). `test_excluded_from_list` (load-bearing invariant #1). |
| 5  | List scoped to JWT user, never the body (IDOR) | ✓ VERIFIED | `where(Reading.user_id == user.id)` (L315); router `user = Depends(get_current_user)`, no body user_id field. `test_cross_user_detail_and_delete_404`. |
| 6  | `GET /api/readings/{id}` returns the immutable stored reading; a 2nd call identical, no regen (HIST-03) | ✓ VERIFIED | `get_reading_detail` (L381-436) reuses `_build_response` over persisted `reading_cards` + `summary_full`; NO LLM/redraw. `staleTime: Infinity` on FE `useReadingDetail`. |
| 7  | Cross-user / deleted id → 404 (not 403, not 200) — IDOR closed (the HIGH threat) | ✓ VERIFIED | detail/delete/restore all `where(user_id == user.id, deleted_at.is_(None))` → `ReadingInputError` → router maps to 404 (readings.py L107-149). `test_cross_user_detail_and_delete_404`. |
| 8  | `DELETE /api/readings/{id}` soft-deletes (sets `deleted_at`); disappears from list AND GET/{id} 404s (HIST-04) | ✓ VERIFIED | `soft_delete` (L457-478) sets `deleted_at`, never hard-delete; already-deleted → 404. `test_excluded_from_list` + delete tests. |
| 9  | `POST /api/readings/{id}/restore` unsets `deleted_at`; reading reappears (D-03) | ✓ VERIFIED | `restore` (L480-500) nulls `deleted_at`, user-scoped → 404 on non-owned. `test_restore_unsets_deleted_at`. |
| 10 | HIST-05 closed gate: `PromptEngine.build` has NO history param; create_reading loads no prior readings even with flag ON | ✓ VERIFIED | Signature introspection (runtime): build params = `[deck, draw_records, question, safety_action, self, session, spread, topic]` — no history/history_context/prior_readings. Human-visible lock comment prompt_engine.py L337-353. `test_build_has_no_history_parameter` PASSES (no-DB regression fence). `test_prompt_has_no_history_even_with_flag_on` (invariant #4). |
| 11 | `PATCH /api/me/settings` partial (only provided flags change), JWT-scoped (body user_id ignored) | ✓ VERIFIED | `patch_settings` (users.py L36-53) `model_dump(exclude_unset=True)` → setattr on `current_user`; `SettingsPatch` all-optional, NO user_id field. `test_partial_patch_round_trip` (invariant #3). |
| 12 | Settings round-trip: `GET /api/me` reflects the change (PROF-02) | ✓ VERIFIED | PATCH commits + returns `SettingsOut`; GET /api/me returns `settings=current_user`. `test_partial_patch_round_trip`. |
| 13 | `GET /api/me` returns `{user, limits, settings}` unchanged (PROF-01) | ✓ VERIFIED | `MeResponse` = `{user, limits, settings}`, no schema change (auth.py L102-107); route mounted. |
| 14 | New reading's `reversals_enabled` sourced from persisted user flag, not body (D-09/PROF-02) | ✓ VERIFIED | `create_reading`: `reversals_enabled = user.reversals_enabled` (reading.py L225), recorded on the row; backend authoritative even if client sends a value. |
| 15 | Profile shows Telegram name + photo + reversals & personalization toggles (PROF-01/D-07) | ✓ VERIFIED | `ProfileScreen.tsx` renders `data.user.photo_url`/name (L162-187) + two `SettingRow` toggles (L193-205) from `useMe()`. |
| 16 | Toggling optimistically updates + calls PATCH (PROF-02) | ✓ VERIFIED | `usePatchSettings` optimistic onMutate/onError/onSettled on `["me"]` (useMe.ts L37-62); `toggle()` mutates only the changed key (ProfileScreen L143-145). |
| 17 | Readings-count + subscription block NOT rendered in Profile (D-08) | ✓ VERIFIED | ProfileScreen renders ONLY identity + toggles, no `limits` use (explicit D-08 comment L8-10). Test `D-08: ...weekly-limit value is absent` mocks limit=37 and asserts it never appears in DOM. |
| 18 | D-09 onboarding server-primary (FlowRoot reads GET /api/me; OnboardingFlow PATCHes; localStorage boot fallback) | ✓ VERIFIED | FlowRoot.tsx: `useMe()` drives decision (L55,80), localStorage only while query in flight (L65-71), one-time reconcile PATCH (L88-90). OnboardingFlow PATCHes `onboarding_completed:true` on completion (L64-65). |
| 19 | Home header has History + Profile icon entry points; result «история» routes to History (D-10) | ✓ VERIFIED | CatalogScreen `goTo("history")` (L152) + `goTo("profile")` (L168); ResultScreen live-mode «История» → list (L234). |
| 20 | Reopen detail uses fade-in, no reveal chrome; back → History (D-11) | ✓ VERIFIED | ResultScreen `isDetail` branch (L210-220) renders `ReadingBody fadeCards` + `DetailHeader onBack={back}`; `fadeContainer`/`fadeItem` opacity-only (L49-55); no flip/reveal. |
| 21 | Swipe optimistically removes + DELETEs; undo snackbar (~5s) restores via restore endpoint (HIST-04/D-03) | ✓ VERIFIED | HistoryScreen `drag="x"` threshold 96px → `handleDelete` → `useDeleteReading` optimistic + `UndoSnackbar`; `handleUndo` → `useRestoreReading` re-insert at index. `HistoryScreen.delete.test.tsx` (3 green). |
| 22 | Undo not tapped within ~5s → removal stands | ✓ VERIFIED | `UndoSnackbar` `UNDO_WINDOW_MS=5000` setTimeout→`onDismiss` (L32-36); server already soft-deleted. |
| 23 | Empty history shows §9.6 «Пока здесь тихо…» copy | ✓ VERIFIED | HistoryScreen `items.length === 0` → `HISTORY_EMPTY` (L140-142). `HistoryScreen.test.tsx`. |
| 24 | All new history/profile/settings copy passes BANNED_BRAND_TOKENS scan (SAFE-06) | ✓ VERIFIED | `copy.test.ts` `collectStrings(copy)` scans EVERY export against `BANNED_BRAND_TOKENS` (AI/нейросеть/модель/сгенерировано/ИИ) → false; covers new HISTORY_*/SETTINGS_* strings. 7 green. |
| 25 | History list as server state (Query, never Zustand); stable key | ✓ VERIFIED | `useReadingsList`/`useReadingDetail`/delete/restore all key `["readings","list"]`/`["readings","detail",id]` (useReadings.ts). |
| 26 | API client routes through Bearer apiFetch seam (no body user_id) | ✓ VERIFIED | api/readings.ts + api/me.ts: all calls via `apiFetch`, server scopes by JWT. |
| 27 | The 4 load-bearing invariants + IDOR each have a NAMED test | ✓ VERIFIED | `test_excluded_from_list`, `test_last_ten_cap`, `test_partial_patch_round_trip`, `test_prompt_has_no_history_even_with_flag_on` (+`test_build_has_no_history_parameter`), `test_cross_user_detail_and_delete_404` — all present (grep-confirmed). |

**Score:** 27/27 truths verified at the code level.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/reading.py` | list/detail/soft_delete/restore + FREE_HISTORY_CAP + reversals-from-user | ✓ VERIFIED | All four methods substantive + correctly scoped; `FREE_HISTORY_CAP=10`; `_build_response` reused for immutable detail. |
| `backend/app/api/readings.py` | GET list + GET/{id} + DELETE + POST restore, JWT-scoped, IDOR→404 | ✓ VERIFIED | All 4 routes; list declared before `/{reading_id}`; UUID path typing; `ReadingInputError`→404. |
| `backend/app/api/users.py` | PATCH /me/settings partial + JWT-scoped; GET /me | ✓ VERIFIED | `exclude_unset` partial; `current_user` target; `SettingsOut` return. |
| `backend/app/services/prompt_engine.py` | HIST-05 lock comment; no history param | ✓ VERIFIED | Lock comment L337-353; build() has no history seam (introspection-confirmed). |
| `backend/app/schemas/auth.py` | SettingsPatch all-optional, no user_id; SettingsOut; MeResponse | ✓ VERIFIED | All three flags `bool\|None=None`; no user_id field. |
| `backend/app/schemas/reading.py` | ReadingListItemOut light schema | ✓ VERIFIED | 7 light fields, no interpretation/cards. |
| `frontend/src/components/profile/ProfileScreen.tsx` | identity + toggles, no count (D-08) | ✓ VERIFIED | Identity + 2 toggles; D-08 count hidden. |
| `frontend/src/components/history/HistoryScreen.tsx` | list + swipe-delete + empty state + back | ✓ VERIFIED | Full list-item card, swipe + undo, §9.6 empty, back→Home. |
| `frontend/src/components/history/UndoSnackbar.tsx` | 5s motion snackbar, no toast lib | ✓ VERIFIED | AnimatePresence, 5000ms timer, motion-only. |
| `frontend/src/hooks/useReadings.ts` | list/detail/delete/restore hooks, stable key | ✓ VERIFIED | Optimistic delete/restore on `["readings","list"]`. |
| `frontend/src/hooks/useMe.ts` | useMe + usePatchSettings optimistic | ✓ VERIFIED | Optimistic on `["me"]`. |
| `frontend/src/api/readings.ts` + `api/me.ts` | Bearer apiFetch calls | ✓ VERIFIED | All endpoints wired, data flows from real backend. |
| `frontend/src/flow/FlowRoot.tsx` | server-primary onboarding + SCREENS registry | ✓ VERIFIED | useMe-driven gate; history/profile/readingDetail mapped. |
| `frontend/src/components/CatalogScreen.tsx` | header icons (D-10) + reversals from useMe (D-09) | ✓ VERIFIED | goTo history/profile; reversals from persisted flag. |
| `frontend/src/components/result/ResultScreen.tsx` | detail mode fade-in, back→History | ✓ VERIFIED | `isDetail` branch, useReadingDetail, opacity fade. |
| `frontend/src/components/onboarding/OnboardingFlow.tsx` | PATCH onboarding_completed on completion | ✓ VERIFIED | markOnboardingSeen + patchSettings.mutate. |

### Key Link Verification

| From | To | Via | Status |
|------|-----|-----|--------|
| `readings.py` GET list | `ReadingService.list_readings` | thin router, user from JWT | ✓ WIRED |
| `reading.py` list query | `Reading` (user_id, deleted_at, status) | `where(user_id==, deleted_at.is_(None), status==COMPLETED).order_by(created_at desc)` | ✓ WIRED |
| `readings.py` GET/{id} | `get_reading_detail` → `_build_response` | immutable mapper reuse | ✓ WIRED |
| `users.py` PATCH | `current_user` (JWT) | `setattr` over `model_dump(exclude_unset=True)` | ✓ WIRED |
| `create_reading` | `User.reversals_enabled` | draw uses persisted flag (D-09) | ✓ WIRED |
| `ProfileScreen` | GET /api/me + PATCH /api/me/settings | `useMe` + `usePatchSettings` optimistic | ✓ WIRED |
| `HistoryScreen` | DELETE + restore | `useDeleteReading`/`useRestoreReading` on `["readings","list"]` | ✓ WIRED |
| `FlowRoot` | GET /api/me onboarding_completed | server-primary gate + reconcile PATCH | ✓ WIRED |
| `CatalogScreen` | goTo history/profile + reversals from useMe | header icons + persisted flag | ✓ WIRED |
| App router | readings.router + users.router | `app.include_router(..., prefix="/api")` | ✓ WIRED (7 routes mounted, confirmed in-process) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| HistoryScreen | `data` (list) | `useReadingsList` → `fetchReadings` → `GET /api/readings` → `list_readings` DB query | Yes — real `select(Reading...)` join, not static | ✓ FLOWING |
| ResultScreen detail | `detail` | `useReadingDetail` → `fetchReadingDetail` → `GET /{id}` → `get_reading_detail` reads persisted rows + `summary_full` | Yes — immutable persisted read | ✓ FLOWING |
| ProfileScreen | `data.user`/`data.settings` | `useMe` → `fetchMe` → `GET /api/me` → `current_user` + `get_user_limits` | Yes — JWT user row | ✓ FLOWING |
| ProfileScreen toggles | `settings.*` | `usePatchSettings` → `PATCH /api/me/settings` → `setattr` + commit | Yes — partial DB write, round-trips | ✓ FLOWING |
| CatalogScreen reversals | `reversals_enabled` | `useMe().data.settings.reversals_enabled ?? localReversals` | Yes — persisted flag primary | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| HIST-05 gate closed (no history param) | `inspect.signature(PromptEngine.build)` | params = `[deck, draw_records, question, safety_action, self, session, spread, topic]` — no history seam | ✓ PASS |
| FREE_HISTORY_CAP constant | import `FREE_HISTORY_CAP` | `10` | ✓ PASS |
| ReadingService history surface | `hasattr` for list/detail/soft_delete/restore | all present | ✓ PASS |
| Routes mounted in app | `app.routes` filter (env-stubbed in-process) | GET/PATCH /api/me(+settings); GET/POST/DELETE /api/readings(+/{id}/restore) all present | ✓ PASS |
| Backend suite | `uv run pytest -q` | 83 passed, 65 skipped (PG-absent) | ✓ PASS |
| Frontend suite | `node node_modules/vitest/vitest.mjs run` | 101 passed | ✓ PASS |
| Live identity/photo, persistence, swipe/animation feel | n/a (needs live Telegram + Postgres) | — | ? SKIP → human_needed |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| HIST-01 | 05-01/02/05 | Расклад автоматически сохраняется в историю | ✓ SATISFIED | `list_readings` surfaces COMPLETED readings; auto-save via Phase-4 create. Truth #1. |
| HIST-02 | 05-01/02/05 | История: дата/вопрос/колода/расклад/миниатюры/итог (GET /api/readings пагинация) | ✓ SATISFIED | `ReadingListItemOut` light shape + thumbnails join + limit/offset. Truths #2,#23. |
| HIST-03 | 05-01/04/06 | Повторное открытие (GET /api/readings/{id}) | ✓ SATISFIED | `get_reading_detail` immutable reuse; FE detail mode fade-in. Truths #6,#20. |
| HIST-04 | 05-01/04/06 | Удаление (DELETE, soft `deleted_at`) | ✓ SATISFIED | `soft_delete`/`restore` + FE swipe/undo. Truths #4,#8,#9,#21,#22. |
| HIST-05 | 05-01/03 | История не для персонализации без согласия (`allow_history_personalization`) | ✓ SATISFIED | Closed gate by absence (consent flag persisted, no history channel into prompt). Truth #10. |
| HIST-06 | 05-01/02 | Бесплатно последние 10 раскладов | ✓ SATISFIED | `FREE_HISTORY_CAP=10` display cap, older retained. Truth #3. |
| PROF-01 | 05-01/03/05/07 | Профиль (GET /api/me): имя/кол-во/подписка/настройки | ✓ SATISFIED | `MeResponse` unchanged; FE renders name/photo (count hidden D-08). Truths #13,#15,#17. |
| PROF-02 | 05-01/03/04/07 | Настройки (PATCH /api/me/settings): reversals/personalization/onboarding | ✓ SATISFIED | Partial JWT-scoped PATCH + round-trip + reversals-source. Truths #11,#12,#14,#16. |

All 8 phase requirement IDs map to verified truths and artifacts. No orphaned requirements (REQUIREMENTS.md maps exactly HIST-01..06 + PROF-01/02 to Phase 5; all claimed by plans). All 8 already marked Complete in REQUIREMENTS.md traceability table.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | No TBD/FIXME/XXX in any Phase-5 file | — | Clean — completion is auditable. |
| CatalogScreen.tsx | 13,200 | `QUESTION_PLACEHOLDER` | ℹ️ Info | Legitimate HTML input `placeholder` attribute (Phase-3, not a stub). Not a debt marker. |
| copy.ts | 4,18,136 | ban-list regex `/ai\|нейросет\|.../i` + comments | ℹ️ Info | The brand-guard definition itself + documentation, not banned copy. Verified by `copy.test.ts`. |

No stubs, no empty handlers, no hardcoded-empty data that flows to render, no `return null` placeholders, no banned brand tokens in user-facing copy. Debt-marker gate: PASS (zero markers).

### Human Verification Required

4 items need live-stack testing (see frontmatter `human_verification`):

1. **History list end-to-end** — run a reading in Telegram, confirm it appears in History with all §9.6 fields + thumbnails.
2. **Reopen immutable detail** — tap a past reading; confirm fade-in, immutable content, back→History.
3. **Swipe-delete + undo feel** — swipe/✕ to remove, «Отменить» within ~5s restores; lapse finalizes.
4. **Profile identity + settings persistence** — real Telegram name/photo, no count block, toggles persist across reload.

These are the exact Manual-Only Verifications listed in 05-VALIDATION.md (touch/animation feel + real Telegram identity + cross-reload server persistence). All underlying code/logic is verified by source + (PG-skipped) integration tests.

### Gaps Summary

**No gaps.** Every code-level must_have (27/27) is verified directly from source — not from SUMMARY claims:

- The list query enforces the cap, user-scoping, soft-delete + COMPLETED-only exclusion, and newest-first ordering.
- Detail/delete/restore are user-scoped with IDOR closed (the HIGH threat) via 404-not-403.
- The immutable detail reuses `_build_response` with no LLM/redraw.
- The HIST-05 consent gate is closed by absence — confirmed by runtime signature introspection that `PromptEngine.build` has no history parameter (a PASSING regression fence, not a skip), plus `create_reading` loads no prior readings.
- `PATCH /api/me/settings` is partial + JWT-scoped and round-trips.
- The Profile hides the count (D-08), onboarding is server-primary (D-09), and all new copy is brand-safe (SAFE-06, module-wide scan).
- All 4 load-bearing invariant tests + the cross-user IDOR test exist by name; both suites are green at the expected baselines (backend 83 pass/65 skip, frontend 101 pass).
- All 7 Phase-5 routes are mounted in the FastAPI app (confirmed in-process).

The skips are exclusively the DB-touching integration tests with the confirmed reason "Postgres unreachable" — the established Phase 1-4 convention, not failures. The only unverifiable items are the live-device UAT behaviors, which are routed to human verification per the Phase 1-4 pattern.

**Status: human_needed** — automated code verification complete and fully passing; awaiting live-stack UAT.

---

_Verified: 2026-06-15T00:30:00Z_
_Verifier: Claude (gsd-verifier)_
