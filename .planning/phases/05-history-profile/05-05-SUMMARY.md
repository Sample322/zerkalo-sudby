---
phase: 05-history-profile
plan: 05
subsystem: ui
tags: [react, zustand, tanstack-query, motion, history, navigation, brand-voice]

# Dependency graph
requires:
  - phase: 05-history-profile (05-02)
    provides: GET /api/readings + light ReadingListItemOut (7 §9.6 fields) the list consumes
  - phase: 03-the-ritual-mock
    provides: Zustand step-machine (D-02), FlowRoot AnimatePresence switch, copy.ts SAFE-06 module, ResultScreen + its «история» stub, apiFetch Bearer seam, CardArtFallback
  - phase: 04-real-personal-reading-keystone
    provides: ReadingOut contract / MockReading shape the detail view (05-06) will render
provides:
  - Step union extended with off-flow history|profile|readingDetail destinations (D-10/D-11)
  - detailReadingId slot + setDetailReadingId setter (the History→detail writer seam for 05-06)
  - FlowRoot registration of history/profile/readingDetail (readingDetail → ResultScreen)
  - HistoryScreen — load-more-ready list via useReadingsList against GET /api/readings, §9.6 empty state
  - useReadingsList TanStack Query hook (stable key ["readings","list"] — Pitfall 5 delete-mutation seam)
  - fetchReadings + typed ReadingListItem (frontend mirror of backend ReadingListItemOut)
  - Home (CatalogScreen) atmospheric header icons → goTo("history")/goTo("profile") (D-10)
  - Un-stubbed ResultScreen «история» action → goTo("history") (D-10)
  - ProfileScreen stub registered (body lands in 05-07)
  - All new history/profile/settings copy centralized + SAFE-06-clean
affects: [05-06 detail-and-delete, 05-07 profile-settings]

# Tech tracking
tech-stack:
  added: []  # zero new dependencies (RESEARCH Package Legitimacy Audit)
  patterns:
    - "Off-flow step destinations: history/profile/readingDetail reached via goTo/back, NEVER next; excluded from STEP_ORDER"
    - "Foundation plan owns ALL shared FE seams (step union, FlowRoot registry, api/hooks/copy) so 05-06/07 replace only their own screen file — mirrors Phase-3 FlowRoot-stub pattern"
    - "History = server state via TanStack Query single stable key ['readings','list'] (no filters, D-01); never mirrored into Zustand"

key-files:
  created:
    - frontend/src/api/readings.ts
    - frontend/src/hooks/useReadings.ts
    - frontend/src/components/history/HistoryScreen.tsx
    - frontend/src/components/history/HistoryScreen.test.tsx
    - frontend/src/components/profile/ProfileScreen.tsx
  modified:
    - frontend/src/flow/steps.ts
    - frontend/src/stores/selection.ts
    - frontend/src/stores/selection.test.ts
    - frontend/src/flow/FlowRoot.tsx
    - frontend/src/reading/copy.ts
    - frontend/src/components/CatalogScreen.tsx
    - frontend/src/components/result/ResultScreen.tsx
    - frontend/src/components/result/ResultScreen.test.tsx

key-decisions:
  - "History/Profile/detail implemented as new Zustand step values (NOT react-router) — extends the existing D-02 step-machine; off-flow tokens excluded from STEP_ORDER so next('result') stays terminal"
  - "List-item thumbnails reuse CardArtFallback down-scaled into a 44×70 box (overflow-hidden + transform-origin top-left); empty thumbnails fall through to the CSS/SVG fallback (A2)"
  - "Result «история» un-stub (D-10) supersedes the Phase-3 D-12 inert-stub assertion; «сохранить карточку» stays a «скоро» stub (Phase 8)"
  - "Personalization explainer copy (consumed by 05-07) describes «история раскладов»/«колода помнит» + a privacy note, never the mechanism (SAFE-06 / Pitfall 6)"

patterns-established:
  - "Off-flow navigation tokens (goTo/back only) layered onto the linear ritual step-machine"
  - "Light list-item fetch (fetchReadings) is distinct from the heavy detail contract — list carries короткий итог only (§9.6), never per-card interpretation"

requirements-completed: [HIST-01, HIST-02, HIST-06]

# Metrics
duration: 10min
completed: 2026-06-14
---

# Phase 5 Plan 05: FE History/Profile foundation + History list slice Summary

**Extended the Zustand step-machine with off-flow history/profile/readingDetail destinations, shipped the History list screen (load-more-ready TanStack Query list against GET /api/readings with the §9.6 empty state + card thumbnails), wired Home header icons + the un-stubbed result «история» action, and centralized all new brand-safe copy — zero new dependencies.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-06-14T15:00:04Z
- **Completed:** 2026-06-14T15:09:29Z
- **Tasks:** 2
- **Files modified:** 13 (5 created, 8 modified)

## Accomplishments
- Navigation spine: `Step` union now carries `history | profile | readingDetail` (off-flow, goTo/back only), `selection.ts` exposes `detailReadingId` + `setDetailReadingId`, and FlowRoot registers all three screens (`readingDetail` → reused `ResultScreen`).
- History list live end-to-end: Home header icon → `HistoryScreen` (reverse-chronological list of date/question/deck/spread/thumbnails/short summary via `useReadingsList` against `GET /api/readings`), §9.6 empty state, in-app back → Home; result «история» also routes here.
- All shared FE seams (step union, FlowRoot registry, `api/readings.ts`, `useReadings.ts`, copy strings) landed so 05-06 (detail+delete) and 05-07 (profile/settings) touch only their own screen files.
- All new copy is SAFE-06-clean; full frontend suite 87 green (baseline 80 + 7 new), `tsc --noEmit` 0, `vite build` succeeds.

## Task Commits

Each task was committed atomically:

1. **Task 1: Nav spine — Step union, selection store, FlowRoot registration, screen stubs, copy** - `e069538` (feat)
2. **Task 2: useReadingsList + fetchReadings + History list screen + Home/Result entry points** - `3cbb427` (feat)

**Plan metadata:** (this commit — docs: complete plan)

## Files Created/Modified
- `frontend/src/flow/steps.ts` - extended `Step` union with off-flow `history|profile|readingDetail` (excluded from `STEP_ORDER`)
- `frontend/src/stores/selection.ts` - added `detailReadingId` slot + `setDetailReadingId` setter (the History→detail writer seam)
- `frontend/src/stores/selection.test.ts` - added off-flow-destinations + `detailReadingId` seam tests (21 green)
- `frontend/src/flow/FlowRoot.tsx` - registered `history`/`profile`/`readingDetail` (→`ResultScreen`) in `SCREENS`
- `frontend/src/reading/copy.ts` - new history/profile/settings section (§9.6 empty state, header/back/note, profile + settings + personalization explainer), all SAFE-06-clean
- `frontend/src/components/history/HistoryScreen.tsx` - the History list (list-item cards + thumbnails + empty/loading/error states + back→Home + tap→detail seam)
- `frontend/src/components/history/HistoryScreen.test.tsx` - list render + §9.6 empty state + SAFE-06 (3 tests)
- `frontend/src/components/profile/ProfileScreen.tsx` - brand-safe Profile stub (body in 05-07) with back→Home
- `frontend/src/api/readings.ts` - typed `ReadingListItem` + `fetchReadings` (GET /api/readings?limit=10, ok-check throw)
- `frontend/src/hooks/useReadings.ts` - `useReadingsList` with the stable key `["readings","list"]` (Pitfall 5)
- `frontend/src/components/CatalogScreen.tsx` - atmospheric header nav row with History/Profile icons → `goTo` (D-10)
- `frontend/src/components/result/ResultScreen.tsx` - un-stubbed «история» → `goTo("history")`; «сохранить карточку» stays «скоро»
- `frontend/src/components/result/ResultScreen.test.tsx` - updated the result-action assertions for the D-10 un-stub

## Decisions Made
- **History/Profile/detail are new Zustand `step` values, not a router** (Claude's discretion per CONTEXT, constrained by D-02/D-10/D-11). The off-flow tokens are deliberately excluded from `STEP_ORDER` so `next("result")` stays the terminal ritual step; they are only ever reached via `goTo` (Home icons / result «история» / list-item tap) and left via `back`.
- **List-item thumbnails reuse `CardArtFallback`** (the fixed 120×192 art down-scaled by 0.3667 into a 44×70 overflow-hidden box). Empty `thumbnail_url`s fall through to the CSS/SVG fallback (A2), so the list always renders.
- **`detailReadingId` + navigation is set now even though 05-06 wires the actual detail render** — setting the id and navigating to `readingDetail` (which currently lands on `ResultScreen`'s defensive empty guard until 05-06 reads `detailReadingId`) is the correct foundation seam.

## Deviations from Plan

None - plan executed exactly as written.

The only behavioral change to an existing test (`ResultScreen.test.tsx`) was explicitly mandated by the plan (Task 2e: un-stub the «история» action, D-10): the Phase-3 D-12 "«История» is disabled and inert" assertion was replaced by two assertions — «Сохранить карточку» stays a disabled `«скоро»` stub, and «История» is now enabled and routes to the `history` step. This is in-scope plan work, not an auto-fix.

## Issues Encountered
None. The `CardArt` thumbnail needed an explicit 44×70 overflow-hidden box (a bare `width` left the scaled child without reserved height); caught and fixed before the Task 2 commit while writing the list body.

## User Setup Required
None - no external service configuration required. (Deploy-time HUMAN-UAT note carried in the plan: the live History list feel — touch, atmospheric header icons, fade — is a deploy-time smoke like Phases 2–4 against a running stack + Telegram; the automated component test runs headless and the plan stays autonomous.)

## Next Phase Readiness
- **05-06 (detail + delete):** `detailReadingId` + `goTo("readingDetail")` (→ `ResultScreen`) are wired; the stable list key `["readings","list"]` is in place for the optimistic delete/restore mutations; `HISTORY_DELETED_NOTICE` / `HISTORY_DELETE_UNDO` copy is already centralized. 05-06 extends only `ResultScreen` (to read `detailReadingId`) + adds delete/restore hooks.
- **05-07 (profile + settings):** `ProfileScreen` stub is registered; `PROFILE_HEADER` / `SETTINGS_*` copy (incl. the SAFE-06 personalization explainer) is already in `copy.ts`. 05-07 replaces only `ProfileScreen.tsx` + adds the settings hooks.
- No blockers. Zero new dependencies added.

## Self-Check: PASSED

- All 5 created files verified on disk (api/readings.ts, hooks/useReadings.ts, HistoryScreen.tsx, HistoryScreen.test.tsx, ProfileScreen.tsx) + SUMMARY.md.
- Both task commits verified in git log (`e069538`, `3cbb427`).
- Full frontend suite 87 passed (16 files); `tsc --noEmit` exit 0; `vite build` succeeded (517 modules).

---
*Phase: 05-history-profile*
*Completed: 2026-06-14*
