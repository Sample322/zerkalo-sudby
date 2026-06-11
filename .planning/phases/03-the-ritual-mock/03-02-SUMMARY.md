---
phase: 03-the-ritual-mock
plan: 02
subsystem: ui
tags: [react, motion, animate-presence, lazy-motion, onboarding, localStorage, brand-voice, vitest, rtl]

# Dependency graph
requires:
  - phase: 03-the-ritual-mock
    plan: 01
    provides: "FlowRoot AnimatePresence step-switch (routes step==='onboarding' here), useOnboardingSeen (markOnboardingSeen/hasSeenOnboarding), selection store goTo, reading/copy.ts onboarding copy bank + canonical BANNED_BRAND_TOKENS"
provides:
  - "Real OnboardingFlow screen (replaces the 03-01 stub) — 3 intro slides + ONB-03 reversed-cards explainer (4 slides total), persistent «Пропустить», final «Сделать первый расклад» CTA"
  - "First end-to-end vertical slice for a first-launch user: read → skip/finish → persist localStorage flag → advance to selection (ONB-01..04)"
  - "ONBOARDING_NEXT («Далее») added to the centralized copy bank so 100% of onboarding copy stays SAFE-06-scannable"
affects: [03-03-selection, phase-04-real-generation]

# Tech tracking
tech-stack:
  added: []  # no new dependency — motion/zustand already in lockfile
  patterns:
    - "Slide sequence = local useState index + AnimatePresence mode='wait' (the same primitive FlowRoot uses) — no carousel library (RESEARCH Don't Hand-Roll)"
    - "Component renders inside FlowRoot's LazyMotion, so all motion uses m.* from motion/react-m (never a stray motion.*); tests wrap the component in <LazyMotion features={domAnimation}> so m.* mounts"
    - "Persistent controls (skip + primary CTA) live OUTSIDE AnimatePresence; only slide CONTENT crossfades — so navigation is testable synchronously and only content assertions need a waitFor"
    - "SAFE-06 component test imports the canonical BANNED_BRAND_TOKENS helper instead of re-declaring the ad-hoc /ai|нейросет|модель|сгенерирован/i regex"

key-files:
  created:
    - frontend/src/components/onboarding/OnboardingFlow.test.tsx
  modified:
    - frontend/src/components/onboarding/OnboardingFlow.tsx
    - frontend/src/reading/copy.ts

key-decisions:
  - "Reversed-cards explainer (ONB-03) folded as a DEDICATED 4th slide (after «Это не приговор, а подсказка»), not crammed into slide 3 — gives the plain-language framing its own breathing room and a title-less, copy-focused slide"
  - "ONBOARDING_NEXT («Далее») added to reading/copy.ts rather than inlined, so zero user-facing onboarding strings live in the component and the ban-list test scans every label"
  - "afterEach(cleanup) added to the test: the vitest config registers no global RTL auto-cleanup (no setupFiles), so renders must be unmounted explicitly to avoid cross-test DOM leakage"

patterns-established:
  - "Stub-at-final-path swap honored: only OnboardingFlow.tsx (+ its test + a copy-bank addition) changed; FlowRoot.tsx is NOT in the diff (zero Wave-2 write conflict)"
  - "Async RTL handling for AnimatePresence mode='wait': await waitFor(...) until the entering slide's content lands, because the exit animation does not settle synchronously under jsdom"

requirements-completed: [ONB-01, ONB-02, ONB-03, ONB-04, SAFE-06]

# Metrics
duration: 5min
completed: 2026-06-11
---

# Phase 3 Plan 02: Onboarding Summary

**The onboarding vertical slice (ONB-01..04): the 03-01 stub is replaced by a real 4-slide, full-bleed, vertically-centered onboarding — three atmosphere slides plus a plain-language reversed-cards explainer (ONB-03: «задержка / внутреннее сопротивление / скрытое напряжение», never «плохо») — with a persistent «Пропустить» on every slide and a final «Сделать первый расклад» CTA, where both finishing and skipping persist the localStorage flag (ONB-04/D-11) and advance the flow to selection, all driven by a local index + the locked AnimatePresence motion primitive with deck-var theming and zero FlowRoot edit.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-11T22:05:24Z
- **Completed:** 2026-06-11T22:10:28Z
- **Tasks:** 2
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Replaced the Wave-1 onboarding stub with the real screen, keeping the exact exported name (`OnboardingFlow`) FlowRoot already imports — so FlowRoot needed (and got) no change. The component is a 4-slide sequence: the three `ONBOARDING_SLIDES` from the copy bank plus a dedicated `REVERSED_EXPLAINER` slide (ONB-03), navigated by a local `index` + `AnimatePresence mode="wait"` (no carousel library).
- A persistent «Пропустить» (ONB-02) sits top-right on every slide; the bottom primary control reads «Далее» until the last slide, where it becomes «Сделать первый расклад». Both «Пропустить» and the final CTA call `markOnboardingSeen()` then `goTo("selection")` — satisfying ONB-04/D-11 (persisted, advances, not re-shown; FlowRoot's initial-step gate then keeps returning users on selection).
- All motion uses `m.*` from `motion/react-m` (the component renders inside FlowRoot's `LazyMotion`), with compositor-only `opacity`/`y` slide crossfades on the locked UI-SPEC tokens (280ms, ease-out-expo); atmosphere color reads the deck vars (`--deck-accent` sigil + CTA fill, `--deck-soft` text), with the root default palette applying pre-selection. Touch targets are ≥44px; all copy renders as React text nodes (no `dangerouslySetInnerHTML`).
- Centralized the one remaining label by adding `ONBOARDING_NEXT` («Далее») to `reading/copy.ts`, so the component introduces **zero** user-facing string literals and the SAFE-06 module scan covers every onboarding word.
- Wrote a 4-case interaction test (mirrors `DeckCarousel.test.tsx`'s plain render + `fireEvent`): skip persists+advances, full-advance-to-CTA persists+advances, the on-screen reversed-cards explainer is brand-safe (scanned with the **canonical `BANNED_BRAND_TOKENS`** helper, plus no «плохо/приговор/беда/негатив», and still carries the approved «задержк/сопротивлен/напряжен» framing), and a nothing-broken first-slide assertion.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build the real OnboardingFlow (replaces the stub)** — `570c49a` (feat)
2. **Task 2: Skip/advance interaction test + brand-safe explainer assertion** — `f08ea15` (test)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified
- `frontend/src/components/onboarding/OnboardingFlow.tsx` (MODIFIED — full stub replacement) — the real 4-slide onboarding: local-index + `AnimatePresence` slide sequence, persistent skip, deck-var-tinted centered hero, slide-progress dots, primary «Далее»/CTA button; `markOnboardingSeen()` + `goTo("selection")` on skip and on finish; `m.*` motion only; copy entirely from `reading/copy.ts`.
- `frontend/src/components/onboarding/OnboardingFlow.test.tsx` (CREATED) — 4 cases (skip, finish, SAFE-06 explainer, nothing-broken); wraps the component in `LazyMotion`; `beforeEach` resets store step + clears localStorage; `afterEach(cleanup)`; `await waitFor` for the `mode="wait"` slide swap.
- `frontend/src/reading/copy.ts` (MODIFIED — 1 line) — added `ONBOARDING_NEXT = "Далее"` so the component carries no inline copy and the ban-list test scans it.

## Decisions Made
- **ONB-03 explainer as a dedicated 4th slide:** the reversed-cards explainer gets its own title-less, copy-focused slide immediately after «Это не приговор, а подсказка», rather than being crammed into slide 3. Plainer pacing, and the explainer's plain-language framing reads as its own beat.
- **`ONBOARDING_NEXT` centralized, not inlined:** keeps the component at zero user-facing string literals so the `copy.test.ts` module scan (and the new component-level SAFE-06 assertion) covers 100% of onboarding copy.
- **Persistent controls outside `AnimatePresence`:** the skip control and the primary button are not part of the crossfading slide, so they are always present and synchronously testable; only the slide *content* (the explainer text) needs an async `waitFor`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added `afterEach(cleanup)` to the onboarding test to stop cross-test DOM leakage**
- **Found during:** Task 2 (first test run — 3 of 4 cases failed with "Found multiple elements")
- **Issue:** The project's `vite.config.ts` registers **no** `setupFiles` and does not enable `globals`, so `@testing-library/react` never auto-registers its global `cleanup`. Across this file's four `render()` calls, each render's DOM leaked into `document.body` for the next test, so queries like `getByText("Добро пожаловать…")`/`getByText("Далее")` matched multiple leaked instances. (Existing tests avoid this by rendering once or using per-render-unique text.)
- **Fix:** Imported `cleanup` from `@testing-library/react` and added `afterEach(() => cleanup())` in the test file. Scoped to this test file only — no shared config/setup change.
- **Files modified:** frontend/src/components/onboarding/OnboardingFlow.test.tsx
- **Verification:** the 3 leakage failures cleared; suite went 4/4 green.
- **Committed in:** f08ea15 (Task 2 commit)

**2. [Rule 1 - Bug] Made the SAFE-06 explainer assertion async (`await waitFor`) for the `AnimatePresence mode="wait"` slide swap**
- **Found during:** Task 2 (after fix #1 — the SAFE-06 case still failed: `задержк|сопротивлен|напряжен` not found)
- **Issue:** Under `mode="wait"`, AnimatePresence unmounts the exiting slide and mounts the entering slide only after the exit animation settles — which does **not** happen synchronously in jsdom. So immediately after the final «Далее» click, the reversed-cards explainer content was not yet in the DOM, and a synchronous `container.textContent` scan saw no explainer text. (This is a test-timing correctness issue, not a component bug — the navigation itself works; the skip/finish cases pass synchronously because the persistent controls live outside AnimatePresence.)
- **Fix:** Wrapped the "explainer is present" check in `await waitFor(...)` (made the test `async`) so the assertion runs once motion has flushed the entering slide; the ban-list + non-fatalistic scans then run on the settled DOM.
- **Files modified:** frontend/src/components/onboarding/OnboardingFlow.test.tsx
- **Verification:** SAFE-06 case green; full suite 60/60 green.
- **Committed in:** f08ea15 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking test-infra gap, 1 test-timing bug — both in the new test, not shipped component code)
**Impact on plan:** No scope change, no new dependency. Both fixes were in the test harness; the shipped `OnboardingFlow.tsx` matches the plan exactly. The plan's acceptance criteria (skip + finish persist the flag and advance; explainer brand-safe; copy sourced from `copy.ts`; FlowRoot untouched) are all met.

## Issues Encountered
- None beyond the two self-caught test fixes above. Baseline suite was 56 tests green; the final suite is 60 tests green (+4 onboarding), and `npm run build` (tsc + vite) type-checks and bundles cleanly.

## Threat Surface
- No new trust boundary or surface beyond the plan's `<threat_model>`. The localStorage flag (`zerkalo.onboarding_completed`, T-3-02 accept) and the static onboarding copy → DOM (T-3-04 mitigate / T-3-05 mitigate) are unchanged: all copy is `copy.ts`-sourced (ban-list-gated) and rendered as React text nodes only — no `dangerouslySetInnerHTML`, no user input on this screen. The new component test additionally asserts the rendered explainer is free of banned tokens and fatalistic framing (T-3-04 mitigation now has a runtime guard at the screen level, not just the module level).

## Known Stubs
- None. The 03-01 onboarding stub is fully replaced by the real screen. (The other three Wave-2 screen stubs — ritual/reveal/result — remain as their own plans' scope and are untouched here.)

## User Setup Required
None — no external service configuration. The localStorage flag is client-only and private-mode-safe (worst case: onboarding re-shows).

## Next Phase Readiness
- **Wave-2 sibling plans unaffected:** this plan touched only `onboarding/OnboardingFlow.tsx` (+ its test) and a single additive line in `reading/copy.ts` — no FlowRoot edit, no store/seam change, so 03-03 (selection), 03-04/05 (ritual/reveal), 03-06 (result) have no new contract to discover.
- **Manual acceptance (HUMAN-UAT, end-of-phase per config `human_verify_mode: end-of-phase`):** on-device confirmation that the slide crossfades are smooth (D-01) and the «Пропустить» control is reachable on every slide — a real-device check that belongs to the phase `ui_safety_gate`, not a unit test.

## Self-Check: PASSED

- `frontend/src/components/onboarding/OnboardingFlow.tsx` — FOUND (real screen, stub replaced)
- `frontend/src/components/onboarding/OnboardingFlow.test.tsx` — FOUND
- `frontend/src/reading/copy.ts` — FOUND (ONBOARDING_NEXT added)
- Commit `570c49a` (Task 1, feat) — present in git history
- Commit `f08ea15` (Task 2, test) — present in git history
- Onboarding suite 4/4 green; full Vitest suite 60/60 green; `npm run build` type-checks + bundles
- FlowRoot.tsx NOT in this plan's diff (confirmed via `git status`)

---
*Phase: 03-the-ritual-mock*
*Completed: 2026-06-11*
