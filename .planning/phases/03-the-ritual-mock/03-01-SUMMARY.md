---
phase: 03-the-ritual-mock
plan: 01
subsystem: ui
tags: [react, zustand, motion, animate-presence, telegram-webapp, tdd, vitest, mock-reading, brand-voice]

# Dependency graph
requires:
  - phase: 02-deck-spread-catalog
    provides: selection store (topic/deck/spread + setters), CatalogScreen, per-deck CSS-var theming, CardArt fallback, telegram.ts seam, AuthGate
provides:
  - Flow step-machine (Step union + history-backed in-app back, D-03) in the selection store
  - Ephemeral `reading: MockReading | null` slot + `setReading` (the 03-03 writer → 03-04/05/06 reader contract)
  - FlowRoot AnimatePresence switch (MotionConfig reducedMotion=never + LazyMotion domAnimation), wired as the AuthGate child
  - Extended telegram.ts seam (getColorScheme/getThemeParams/getSafeAreaInsets/getContentSafeAreaInsets/haptic, UI-04)
  - MockReading data contract (types.ts) + createReading() Phase-4 async seam + cardPool fixture (D-05/06/07)
  - Centralized brand-safe copy module with the canonical BANNED_BRAND_TOKENS ban-list helper (SAFE-06, incl. the ИИ token / W-1)
  - useOnboardingSeen localStorage flag (ONB-04/D-11)
  - Four screen stub files at their final paths for parallel Wave-2 execution
affects: [03-02-onboarding, 03-03-selection, 03-04-ritual, 03-05-reveal, 03-06-result, phase-04-real-generation]

# Tech tracking
tech-stack:
  added: []  # no new runtime dependency — motion/zustand already in lockfile
  patterns:
    - "FlowRoot: single Zustand `step` field → one <AnimatePresence mode=wait> switch (D-02); m.* from motion/react-m inside LazyMotion (Pitfall 5)"
    - "Stub-at-final-path integration seam: FlowRoot binds real paths now; each Wave-2 plan replaces only its own screen file, never FlowRoot"
    - "createReading() single async seam mirroring fetchSpreads — Phase-4 swaps only the data source, return type unchanged (D-05)"
    - "Canonical SAFE-06 ban-list (BANNED_BRAND_TOKENS) as one reusable source; word-bounded Cyrillic ии branch (W-1)"
    - "Injectable RNG on createReading makes D-07 reversals deterministically testable; Math.random is explicitly non-security"

key-files:
  created:
    - frontend/src/flow/steps.ts
    - frontend/src/flow/FlowRoot.tsx
    - frontend/src/reading/types.ts
    - frontend/src/reading/createReading.ts
    - frontend/src/reading/cardPool.fixture.ts
    - frontend/src/reading/copy.ts
    - frontend/src/hooks/useOnboardingSeen.ts
    - frontend/src/components/onboarding/OnboardingFlow.tsx
    - frontend/src/components/ritual/RitualScreen.tsx
    - frontend/src/components/reveal/RevealScreen.tsx
    - frontend/src/components/result/ResultScreen.tsx
  modified:
    - frontend/src/stores/selection.ts
    - frontend/src/lib/telegram.ts
    - frontend/src/App.tsx

key-decisions:
  - "Initial-step gate done via useSelection.setState (not goTo) so the mount correction never leaves a phantom 'onboarding' on back history"
  - "createReading draws cards with Fisher–Yates using the injected RNG so seeded tests are fully deterministic across both reversal branches"
  - "BANNED_BRAND_TOKENS kept NON-global (stateless) so .test() never advances lastIndex; ии branch anchored to Cyrillic word boundaries"

patterns-established:
  - "Stub-at-final-path: FlowRoot imports the five screen paths from day 1; Wave-2 plans overwrite only their own file (no FlowRoot write-conflict)"
  - "Single Phase-4 seam (createReading) with shape-parity to the existing fetch* functions"
  - "One canonical ban-list helper imported everywhere instead of re-declared ad-hoc regexes"

requirements-completed: [HOME-01, HOME-02, HOME-07, READ-08, READ-09, SAFE-06, UI-03, UI-04, ONB-04]

# Metrics
duration: 10min
completed: 2026-06-11
---

# Phase 3 Plan 01: The Flow Spine Summary

**The Phase-3 contract layer: a Zustand `step` state-machine (history-backed in-app back) driving a single FlowRoot AnimatePresence switch, an extended Telegram theme/safe-area/haptics seam, a schema-faithful MockReading + `createReading()` Phase-4 seam with a bundled card pool and client reversals, a centralized brand-safe copy bank with the canonical `BANNED_BRAND_TOKENS` (incl. the `ИИ` token), the onboarding localStorage flag, and four screen stubs at their final paths for parallel Wave-2 execution.**

## Performance

- **Duration:** 10 min
- **Started:** 2026-06-11T21:50:10Z
- **Completed:** 2026-06-11T22:00:01Z
- **Tasks:** 3
- **Files modified:** 16 (13 created, 3 modified)

## Accomplishments
- Extended the selection store into the full flow machine: `question`, `reversalsEnabled`, `step`, `history` (D-03 in-app back), the ephemeral `reading` slot + `setReading` (the cross-plan writer→reader contract), and pure `questionValidity`/`canStart` helpers — all under test (18 store tests).
- Built FlowRoot as the AuthGate child: `MotionConfig reducedMotion="never"` + `LazyMotion domAnimation` + `AnimatePresence mode="wait"` switching on `step`, importing all five real screen paths (CatalogScreen + four stubs) so Wave-2 plans each replace only their own file.
- Extended `telegram.ts` with theme / safe-area-insets / haptics readers, every method an optional-chained no-op outside Telegram (UI-04), plus the `useOnboardingSeen` localStorage flag (ONB-04).
- Delivered the reading data contract: `MockReading` type (mirrors READ-05/06), the `createReading()` async Phase-4 seam (D-05) with a 22-card Major-Arcana fixture (D-06) and deterministic client reversals (D-07), and the centralized brand-safe copy bank with the canonical `BANNED_BRAND_TOKENS` helper (SAFE-06, now detecting the standalone `ИИ` token / W-1 without false-positiving benign Cyrillic words).

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend selection store into the flow state-machine + reading slot** - `41bd054` (feat)
2. **Task 2: Extend telegram.ts + FlowRoot + screen stubs + wire App** - `d9e5aae` (feat)
3. **Task 3: MockReading contract + card-pool fixture + createReading seam + copy module** - `639bd92` (feat)

**Plan metadata:** (final docs commit — see below)

_Note: Tasks 1 and 3 are `tdd="true"`. Because both EXTEND existing modules (the store) or define a data contract whose tests cannot import non-existent symbols, the new tests and their implementation were committed together as a single `feat` per task rather than a separate RED `test(...)` commit — the test suite is the behavior gate and was run red→green during execution (the SAFE-06 over-strict assertion was caught and corrected before commit)._

## Files Created/Modified
- `frontend/src/flow/steps.ts` - `Step` string-literal union (5 steps) + pure `next()` helper
- `frontend/src/flow/FlowRoot.tsx` - MotionConfig+LazyMotion+AnimatePresence root switch on `step`; initial-step onboarding gate
- `frontend/src/stores/selection.ts` - Extended with the flow slice + ephemeral `reading` slot + `setReading`; pure `questionValidity`/`canStart`
- `frontend/src/stores/selection.test.ts` - 18 tests (question validity, canStart, goTo/back/history, startReadingAgain D-04, reading slot)
- `frontend/src/lib/telegram.ts` - Added getColorScheme/getThemeParams/getSafeAreaInsets/getContentSafeAreaInsets + `haptic`
- `frontend/src/lib/telegram.test.ts` - 7 new cases for the readers + haptic (defaults absent, forwarding present)
- `frontend/src/hooks/useOnboardingSeen.ts` - localStorage onboarding flag, private-mode safe
- `frontend/src/hooks/useOnboardingSeen.test.ts` - false→true after mark; never-throws
- `frontend/src/reading/types.ts` - MockReading / MockReadingCard / MockReadingSummary / Orientation
- `frontend/src/reading/createReading.ts` - the Phase-4 async seam; injectable RNG for D-07
- `frontend/src/reading/cardPool.fixture.ts` - 22 Major-Arcana entries (D-06)
- `frontend/src/reading/copy.ts` - centralized brand-safe copy + canonical `BANNED_BRAND_TOKENS`/`containsBannedBrandToken`
- `frontend/src/reading/copy.test.ts` - ban-list coverage (ИИ match + benign-Cyrillic non-match) + module scan
- `frontend/src/reading/createReading.test.ts` - full-shape MockReading + reversals (both branches) + positionTitle spread-driven
- `frontend/src/components/{onboarding,ritual,reveal,result}/*.tsx` - four brand-safe screen stubs with `TODO(plan 03-0X)` markers
- `frontend/src/App.tsx` - renders `<FlowRoot/>` inside `<AuthGate>`

## Decisions Made
- **Initial-step gate via `setState`, not `goTo`:** the FlowRoot mount correction (skip onboarding for returning users) must not record history, so it writes `step` directly. Prevents a phantom "onboarding" on the back stack.
- **Fisher–Yates draw with the injected RNG:** makes both the card selection and the D-07 reversal branches deterministic under a seeded RNG, so the reversals-on/off tests assert exact orientations.
- **`BANNED_BRAND_TOKENS` is non-global + Cyrillic-word-bounded `ии`:** stateless `.test()` reuse, and the `ИИ` token is detected without flagging «гармонии»/«линии»/«версии»/«комиссии» (the W-1 regression guard).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected an over-strict SAFE-06 test assertion that flagged the approved «не приговор» copy**
- **Found during:** Task 3 (copy module + tests)
- **Issue:** My first `copy.test.ts` blanket-banned the literal substring «приговор», but the canonical UI-SPEC/TZ onboarding line is «Это **не приговор**, а подсказка» — a deliberate negation that is brand-correct. The test failed red against legitimate copy.
- **Fix:** Refined the assertion to ban only genuine doom phrasing («узнай правду пока не поздно») and to require that every literal «приговор» occurrence be the negated «не приговор». The real SAFE-06 gate (`BANNED_BRAND_TOKENS`, which does not include «приговор») was unaffected and stays green.
- **Files modified:** frontend/src/reading/copy.test.ts
- **Verification:** copy.test.ts (7 tests) green; full suite green (56)
- **Committed in:** 639bd92 (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug — in my own test, not shipped code)
**Impact on plan:** No scope change. The fix corrected a test that would have wrongly rejected approved brand copy; the canonical ban-list and all shipped strings are unchanged. No new dependency added (verification criterion met).

## Issues Encountered
- None beyond the self-caught test assertion above. The baseline suite (12 tests) was green before changes; the final suite is 56 tests green and `npm run build` type-checks with FlowRoot importing all five screen paths.

## User Setup Required
None - no external service configuration required. (The Telegram WebApp object is runtime-injected and every new reader/haptic no-ops outside Telegram.)

## Next Phase Readiness
- **Wave-2 slice plans can run in parallel with zero contract discovery and no FlowRoot edits.** They import: store actions (`goTo`/`back`/`startReadingAgain`/`setQuestion`/`toggleReversals`/`canStart`/`questionValidity`/`reading` slot + `setReading`), `MockReading`/`createReading`, `haptic`/inset helpers, `hasSeenOnboarding`/`markOnboardingSeen`, the copy bank, and the `BANNED_BRAND_TOKENS` helper. Each replaces ONLY its own stub file.
- **Phase 4 seam ready:** `createReading()` is a single async function with shape-parity to `fetchSpreads` — Phase 4 swaps the body to `POST /api/readings` keeping the return type.
- **Manual acceptance (D-01, deferred to end-of-phase human-verify):** 60fps smoothness, haptic feel, crossfade quality, and particle density are real-device checks, not unit-testable — they belong to the `ui_safety_gate` after the Wave-2 screens land.

## Self-Check: PASSED

All 11 created source files + the SUMMARY exist on disk; all three task commits (`41bd054`, `d9e5aae`, `639bd92`) are present in git history. Full Vitest suite green (56 tests, up from a 12-test baseline); `npm run build` type-checks. No new runtime dependency added to `frontend/package.json`.

---
*Phase: 03-the-ritual-mock*
*Completed: 2026-06-11*
