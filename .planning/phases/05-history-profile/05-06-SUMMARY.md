---
phase: 05-history-profile
plan: 06
subsystem: ui
tags: [react, tanstack-query, motion, history, optimistic-update, swipe-delete, brand-voice]

# Dependency graph
requires:
  - phase: 05-history-profile (05-04)
    provides: GET /api/readings/{id} (immutable detail), DELETE /api/readings/{id} (soft-delete), POST /api/readings/{id}/restore (undo)
  - phase: 05-history-profile (05-05)
    provides: HistoryScreen + useReadingsList stable key ["readings","list"], detailReadingId seam, copy strings (HISTORY_DELETED_NOTICE / HISTORY_DELETE_UNDO), api/readings.ts + useReadings.ts
  - phase: 03-the-ritual-mock
    provides: Zustand step-machine (D-02), FlowRoot LazyMotion/AnimatePresence, ResultScreen chrome, copy.ts SAFE-06 module, apiFetch Bearer seam, CardArtFallback
  - phase: 04-real-personal-reading-keystone
    provides: ReadingOut contract / MockReading shape the detail view renders, shared mapReadingOutToMock mapper
provides:
  - useReadingDetail — immutable reading fetch keyed ["readings","detail",id], staleTime Infinity (HIST-03)
  - ResultScreen detail mode — renders the fetched immutable reading with an opacity fade-in + back→History, no live CTAs (HIST-03 / D-11)
  - mapReadingOutToMock — the SINGLE shared ReadingOut→MockReading mapper (createReading imports it; no duplicate)
  - useDeleteReading — optimistic soft-delete mutation (snapshot + setQueryData remove + onError rollback) on ["readings","list"]
  - useRestoreReading — undo that re-inserts the cached item at its original index + invalidates the same key
  - deleteReading / restoreReading — apiFetch wrappers (DELETE /api/readings/{id} + POST /api/readings/{id}/restore)
  - UndoSnackbar — motion AnimatePresence + 5s setTimeout undo affordance (no toast library)
  - HistoryScreen swipe-to-delete — motion drag onDragEnd past threshold + keyboard-reachable delete twin → optimistic remove + snackbar
affects: [05-07 profile-settings (sibling, zero overlap), Phase-6/7 history tier-limits]

# Tech tracking
tech-stack:
  added: []  # zero new dependencies (motion already pinned; NO toast/router lib — RESEARCH Don't-Hand-Roll)
  patterns:
    - "TanStack v5 optimistic mutation (Pattern 3): onMutate cancel+snapshot+setQueryData, onError snapshot rollback, on a single stable key (Pitfall 5)"
    - "Undo via a dedicated restore endpoint that re-inserts the removed item at its original index in the SAME cache key, then invalidates to reconcile"
    - "motion AnimatePresence snackbar (m.div under LazyMotion, AnimatePresence from motion/react) + setTimeout — compositor-only (opacity/translateY), no toast dependency"
    - "Swipe-to-delete = motion drag='x' + dragSnapToOrigin + onDragEnd offset threshold; an accessible delete button is the keyboard-reachable twin calling the same handler"

key-files:
  created:
    - frontend/src/components/history/UndoSnackbar.tsx
    - frontend/src/components/history/HistoryScreen.delete.test.tsx
  modified:
    - frontend/src/api/readings.ts
    - frontend/src/hooks/useReadings.ts
    - frontend/src/components/result/ResultScreen.tsx
    - frontend/src/reading/createReading.ts
    - frontend/src/components/result/ResultScreen.test.tsx
    - frontend/src/components/history/HistoryScreen.tsx

key-decisions:
  - "Optimistic delete + restore both target the SINGLE stable key ['readings','list'] (Pitfall 5 / T-05-STALE) so the optimistic edits are visible to useReadingsList and the rollback restores the exact snapshot"
  - "Undo re-inserts the removed item at its ORIGINAL index (carried in component state + the restore mutation vars), not appended — the list returns to its pre-delete order without a refetch flash; then invalidates to reconcile with the server"
  - "The swipe-to-delete affordance has a keyboard-reachable delete-button twin calling the same handler — keeps the gesture accessible AND gives the headless test a deterministic trigger (assert the cache/DOM outcome, not drag mechanics)"
  - "UndoSnackbar holds its own 5s timer (cleared on unmount/undo via the open-keyed effect) so an undo cancels the pending auto-dismiss — no toast library (motion AnimatePresence only)"
  - "The delete-button aria-label is a local non-visible constant (copy.ts is locked this plan; the user-facing snackbar strings already live there) — brand-safe, no banned token (SAFE-06)"

patterns-established:
  - "Optimistic remove + undo over soft-delete/restore endpoints with a single-key TanStack cache (snapshot rollback on error, re-insert on undo)"
  - "AnimatePresence-driven transient UI (snackbar): assert dismissal with waitFor (let the exit animation drain the DOM), not a synchronous query"

requirements-completed: [HIST-03, HIST-04]

# Metrics
duration: 40min
completed: 2026-06-14
---

# Phase 5 Plan 06: Immutable reopen + swipe-to-delete & undo Summary

**Made history readings reopenable (ResultScreen detail mode renders the immutable `GET /api/readings/{id}` with a light opacity fade-in + back→History, reusing the single shared ReadingOut→MockReading mapper) and deletable (swipe-to-delete on the list card → optimistic remove + a motion AnimatePresence undo snackbar over the soft-delete/restore endpoints, with a single-key TanStack optimistic cache update) — zero new dependencies.**

## Performance

- **Duration:** ~40 min (Task 1 prior run + Task 2 this run; a prior Task-2 partial was reverted to a clean HEAD before this run)
- **Completed:** 2026-06-14
- **Tasks:** 2 (Task 1 was already committed at run start; this run executed Task 2)
- **Files modified:** 8 (2 created, 6 modified)

## Accomplishments
- **Task 1 (already committed `104d9b7`):** `useReadingDetail` (immutable fetch keyed `["readings","detail",id]`, `staleTime: Infinity`); `ResultScreen` detail mode renders the fetched reading with the opacity fade-in + a single back→History affordance and NONE of the live CTAs; the `ReadingOut→MockReading` mapping was extracted into one shared `mapReadingOutToMock` that `createReading.ts` now imports (no duplicate mapper).
- **Task 2 (this run, `c1cbf54`):** swipe-to-delete + undo end-to-end —
  - `deleteReading` / `restoreReading` apiFetch wrappers (`DELETE /api/readings/{id}` + `POST /api/readings/{id}/restore`, throw on non-2xx).
  - `useDeleteReading` — the canonical TanStack v5 optimistic mutation: `onMutate` cancels in-flight list fetches, snapshots `["readings","list"]`, removes the item by `reading_id` (keeping it + its index), `onError` rolls back to the snapshot.
  - `useRestoreReading` — re-inserts the cached item at its original index in the same key, then invalidates to reconcile.
  - `UndoSnackbar` — a `motion` `AnimatePresence` element with a self-contained 5s `setTimeout` and an «Отменить» action; **no toast library**.
  - `HistoryScreen` — each card is a `motion` horizontal drag surface (`drag="x"` + `dragSnapToOrigin`, `onDragEnd` past a 96px leftward threshold commits the delete) with the tap-to-open body preserved and a keyboard-reachable delete-button twin; one snackbar at a time, undo restores, 5s lapse finalizes.
- Full frontend suite **95 passed** (17 files; baseline 92 + 3 new delete/undo tests), `tsc --noEmit` exit 0, `vite build` succeeds (518 modules, no new dependency).

## Task Commits

Each task was committed atomically:

1. **Task 1: useReadingDetail + ResultScreen detail mode (immutable reopen, fade-in)** - `104d9b7` (feat) — committed in a prior run
2. **Task 2: Swipe-to-delete + UndoSnackbar (optimistic delete + restore)** - `c1cbf54` (feat) — this run

**Plan metadata:** (the following commit — docs: complete plan)

## Files Created/Modified
- `frontend/src/api/readings.ts` (modified) - added `fetchReadingDetail` (Task 1) + `deleteReading` / `restoreReading` wrappers (Task 2), all ok-check-throw
- `frontend/src/hooks/useReadings.ts` (modified) - added `useReadingDetail` (Task 1) + `useDeleteReading` / `useRestoreReading` optimistic mutations on the stable `["readings","list"]` key (Task 2)
- `frontend/src/components/result/ResultScreen.tsx` (modified, Task 1) - detail mode reads `detailReadingId`, fetches via `useReadingDetail`, renders the immutable reading with the opacity fade-in + back→History, no live CTAs
- `frontend/src/reading/createReading.ts` (modified, Task 1) - extracted/exports the shared `mapReadingOutToMock` (single mapping)
- `frontend/src/components/result/ResultScreen.test.tsx` (modified, Task 1) - extended with the detail-mode render test
- `frontend/src/components/history/HistoryScreen.tsx` (modified, Task 2) - swipe-to-delete (drag + accessible delete twin), pending-delete state, `UndoSnackbar` mount; extracted a `HistoryCard` for the draggable card
- `frontend/src/components/history/UndoSnackbar.tsx` (created, Task 2) - motion AnimatePresence + 5s setTimeout undo snackbar (no toast lib)
- `frontend/src/components/history/HistoryScreen.delete.test.tsx` (created, Task 2) - optimistic remove + snackbar, undo restores the cached item + POSTs restore, 5s auto-dismiss leaves the removal (3 tests)

## Decisions Made
- **Both mutations target the single stable key `["readings","list"]`** (Pitfall 5 / T-05-STALE). The optimistic remove edits exactly the cache `useReadingsList` reads; `onError` restores the pre-mutation snapshot. This is the RESEARCH Pattern 3 recipe.
- **Undo re-inserts at the original index.** The removed item + its index are carried in `HistoryScreen` `pending` state and passed to `useRestoreReading`'s vars; on restore success the item is spliced back at its original slot (then the key is invalidated). The list returns to its pre-delete order without a refetch flash.
- **The swipe has an accessible keyboard-reachable twin.** A small delete button (`aria-label`) on each card calls the same `onDelete` handler as `onDragEnd`. This keeps the delete affordance accessible (the swipe is touch-only) and gives the headless test a deterministic trigger — the test asserts the cache/DOM outcome, not motion's drag physics (which jsdom cannot faithfully simulate).
- **The delete-button `aria-label` is a local non-visible constant** (`"Убрать расклад из истории"`). `copy.ts` is locked for this plan (the user-facing snackbar strings `HISTORY_DELETED_NOTICE` / `HISTORY_DELETE_UNDO` already live there from 05-05); the aria-label is not visible chrome (never in `textContent`) and is brand-safe (no banned token — SAFE-06 holds).

## Deviations from Plan

None — Task 2 executed exactly as written. No deviation rules (1–4) triggered; no auto-fixes were needed.

## Issues Encountered
One self-inflicted test assertion fix while writing `HistoryScreen.delete.test.tsx`: the undo test initially asserted the snackbar text was gone with a synchronous `queryByText(...).toBeNull()` immediately after «Отменить», but `AnimatePresence` runs an exit animation so the snackbar DOM lingers briefly. Changed to `await waitFor(() => expect(...).toBeNull())` so the exit drains the DOM first. Caught and fixed before the Task-2 commit; the auto-dismiss test (fake timers) already waited correctly.

## User Setup Required
None — no external service configuration. **Deploy-time HUMAN-UAT note** (carried from the plan): the swipe-delete/undo + reopen-fade FEEL needs a live device + Telegram (touch + animation), a deploy-time smoke like Phases 2–4. The automated component tests run headless; `autonomous` stayed true.

## Next Phase Readiness
- **05-07 (profile + settings):** sibling plan, zero overlap with this one — it replaces only `ProfileScreen.tsx` + adds the settings hooks; the `PROFILE_HEADER` / `SETTINGS_*` copy is already centralized (05-05). The history experience (browse → reopen → delete/undo) is now complete.
- **Phase 6/7 (tier limits):** the history list/detail/delete surface is established; the free-tier cap is the server `FREE_HISTORY_CAP` seam (05-02).
- No blockers. Zero new dependencies added.

## Self-Check: PASSED

- All 8 files verified on disk: created `UndoSnackbar.tsx` + `HistoryScreen.delete.test.tsx`; modified `api/readings.ts`, `hooks/useReadings.ts`, `result/ResultScreen.tsx`, `reading/createReading.ts`, `result/ResultScreen.test.tsx`, `history/HistoryScreen.tsx`.
- Both task commits verified in git log (`104d9b7` Task 1, `c1cbf54` Task 2).
- Full frontend suite 95 passed (17 files; cwd-at-frontend-root run); `tsc --noEmit` exit 0; `vite build` succeeded (518 modules); `package.json` unchanged (no toast/router dependency — T-05-SC holds).

---
*Phase: 05-history-profile*
*Completed: 2026-06-14*
