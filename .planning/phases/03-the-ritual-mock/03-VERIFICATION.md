---
phase: 03-the-ritual-mock
verified: 2026-06-12T15:10:00Z
status: human_needed
score: 5/5 must-haves verified (automated layer); 6 items require human/device confirmation
overrides_applied: 0
mode: mvp
mvp_goal_format: non-user-story  # ROADMAP goal is narrative, not "As a..., I want..., so that..."; verified against the 5 explicit Success Criteria (the roadmap contract) instead
human_verification:
  - test: "Walk onboarding → selection → ritual → reveal → result on a mid/low device in the Telegram client (npm run dev)"
    expected: "Crossfades are continuous, no layout shift, no stutter or abrupt pop-in; load feels fast"
    why_human: "Perceived-quality / 60fps judgment is not assertable from the DOM (UI-01/UI-03/D-01). Automated tests prove state transitions, not animation feel."
  - test: "Tap «Начать расклад», observe the ~3s ritual prep (3 beats + dimming + particles), feel the completion haptic, confirm tap-to-skip works after the first beat"
    expected: "Three beats crossfade over ~3s, the screen dims with a live particle field, a success haptic fires at completion, and tapping after beat 1 skips early"
    why_human: "Timing feel + native HapticFeedback only fire inside a real Telegram client (READ-07/D-08). The test proves the timer→reveal transition and that haptic.notify('success') is called; the felt haptic and 3s pacing need a device."
  - test: "Reveal cards one-by-one, then tap «Раскрыть все»; feel the per-flip light haptic"
    expected: "Each card flips with a 3D turn and a light haptic; «Раскрыть все» staggers the rest so it reads as a ritual, not an abrupt jump"
    why_human: "Flip choreography + per-flip haptic are a visual/feel judgment on-device (READ-08/D-09). The test proves flip state and control presence, not the rendered turn or the haptic pulse."
  - test: "Open in the Telegram WebView on a notched device and toggle the app light/dark theme"
    expected: "Colors adapt to the Telegram theme and content respects the safe-area top/bottom (via SDK insets, not CSS env())"
    why_human: "Requires a real Telegram WebView — SDK safe-area insets and themeParams are null/zero outside Telegram (UI-04). The test proves the insets are read and applied; the rendered adaptation needs a device."
  - test: "Pick different decks and confirm the ritual/reveal/result backgrounds + accents match each deck palette"
    expected: "Per-deck theming carries visually through ritual → reveal → result"
    why_human: "Visual continuity judgment across the per-deck palettes (UI-02 carry / D-08). CSS-var theming is wired but the rendered continuity is a look-and-feel check."
  - test: "Focus the question field on iOS and confirm «Начать расклад» stays reachable above the keyboard"
    expected: "The sticky bottom CTA is not obscured by the iOS keyboard"
    why_human: "Mobile WebView keyboard overlap (research pitfall, UI-01/HOME-07). The CTA is sized against viewportStableHeight + SDK insets in code; the actual keyboard behavior is a device check."
---

# Phase 3: The Ritual (mock) — Verification Report

**Phase Goal:** The user can complete the entire emotional journey — skippable onboarding, the question→topic→deck→spread selection flow, the shuffling-ritual prep screen, and the staggered flip-reveal of cards — end to end against a *mock* reading, locking the UX and animation contract before any LLM is wired in.

**Verified:** 2026-06-12T15:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## MVP-Mode Note

The phase carries `mode: mvp` in ROADMAP.md, but the phase goal is a narrative statement, not a User Story (`user-story.validate` → `valid: false`: missing "As a…", ", I want to…", ", so that…"). Rather than refuse verification, this report verifies against the **5 explicit Success Criteria** in ROADMAP.md (the roadmap contract), which are well-formed and testable, and routes the inherently visual/device-bound items to `human_verification` (the MVP-mode user-flow intent). **Recommendation (non-blocking):** if strict MVP-mode UAT framing is desired for future phases, run `/gsd mvp-phase 03` to reformat the goal into the "As a [user], I want [capability], so that [outcome]." shape.

## Goal Achievement

### Observable Truths (the 5 ROADMAP Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|---------------------------|--------|----------|
| 1 | First-launch 3–4 screen onboarding incl. a non-scary reversed-cards explainer, skippable, not re-shown once completed | ✓ VERIFIED (automated); feel → human | `OnboardingFlow.tsx` renders 3 intro slides (`ONBOARDING_SLIDES`) + the reversed-cards explainer (`REVERSED_EXPLAINER`) as a 4th slide; persistent «Пропустить» on every slide (line 76); skip+final CTA call `markOnboardingSeen()`+`goTo("selection")` (lines 56-59); `FlowRoot.tsx:45-50` skips onboarding for returning users via `hasSeenOnboarding()`. `OnboardingFlow.test.tsx` (4 tests) proves skip→flag+selection, finish→flag+selection, explainer brand-safe & non-fatalistic. |
| 2 | Free-text question (10–500 / empty-valid), pick 1 of 7 topics + deck + spread, gentle prompts when missing/too-short | ✓ VERIFIED (automated) | `selection.ts` `questionValidity` (empty→valid, 1-9→tooShort, ≥10→valid) + `setQuestion` clamps to 500; `CatalogScreen.tsx` textarea (controlled), 7 `TOPICS` chips→`setTopic`, `DeckCarousel`→`setDeck`, `SpreadCard`→`setSpread`, recommendation banner, `START_GATE_HINT` when `!canStart`. `CatalogScreen.test.tsx` (5 tests) proves empty/too-short/valid hint states, gate-disabled+hint, and the recommendation surfaces. `selection.test.ts` (18 tests, incl. validity + canStart). |
| 3 | «Начать расклад» plays ritual prep (3 beats, dimming, particles, completion haptic), then reveals cards one-by-one with flip + «open all» after the first | ✓ VERIFIED (automated state/wiring); timing+haptic feel → human | `RitualScreen.tsx`: 3 `RITUAL_BEATS` × `BEAT_MS`(1000)≈3s, opacity-animated dimming overlay, `<Particles/>` (compositor-only), `haptic.notify("success")`→`goTo("reveal")` on finish, tap-to-skip after `SKIP_UNLOCK_BEAT`(1). `RevealScreen.tsx`: one `FlipCard` per position (3D `rotateY`), «Раскрыть все» appears after first flip & staggers the rest, name+orientation+`shortPhrase` before interpretation; `FlipCard.tsx` fires `haptic.impact("light")` on flip-settle. `RitualScreen.test.tsx` (5) proves beat0+skip-lock, timer→reveal, skip→reveal, `notify('success')` called. `RevealScreen.test.tsx` (4) proves face-down→flip→«open all»→all names, phrase-before-interpretation. |
| 4 | Result screen shows question/topic/deck/spread/date, card cards, overall summary, and save/another/history actions — from a mock result | ✓ VERIFIED (automated) | `ResultScreen.tsx`: `RESULT_HEADER`, meta row (question/topic/deck/spread/date via `formatDate`), one glass `<article>` per `r.cards` (name, positionTitle, orientation, shortMeaning, interpretation, deckAccent), summary panel (5 `SUMMARY_LABELS` fields, staggered), «Ещё расклад»→`startReadingAgain` (D-04), «Сохранить карточку»/«История» `disabled` with «скоро» badge. `ResultScreen.test.tsx` (4) proves all fields render, «Ещё расклад» preserves question+topic, stubs disabled+inert, brand-safe. |
| 5 | Premium-dark mobile-first (360–430) sticky CTA adapts to Telegram light/dark + safe-area (SDK insets), no UI string contains AI/нейросеть/модель/сгенерировано ИИ | ✓ VERIFIED (SAFE-06 + wiring); rendered theme/insets → human | SAFE-06: full-source grep found banned tokens ONLY in comments/tests/the regex definition — zero in user-facing copy; standalone Cyrillic `ИИ` only in the regex. `copy.test.ts` scans every export against `BANNED_BRAND_TOKENS` (incl. `ИИ`, with benign-bigram non-match guards). Insets: `telegram.ts` `getSafeAreaInsets`/`getContentSafeAreaInsets` (SDK, not `env()`); CTAs in CatalogScreen/Result/Reveal add `insets.bottom`; CTA sized against `--tg-viewport-stable-height`. Rendered light/dark adaptation + safe-area on a notched device → human. |

**Score:** 5/5 truths verified at the automated (state/wiring/data) layer. All 5 also carry visual/device-bound aspects that require human confirmation (see Human Verification).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/stores/selection.ts` | Flow step-machine + `reading` slot + `setReading` + gating helpers | ✓ VERIFIED | step/history/question/reversals/reading + actions; `questionValidity`/`canStart` pure helpers; 18 tests green |
| `frontend/src/flow/FlowRoot.tsx` | MotionConfig+LazyMotion+AnimatePresence switch on `step` | ✓ VERIFIED | `reducedMotion="never"`, `LazyMotion domAnimation`, `m.div key={step}`; imports all 5 screens; ONB-04 mount gate |
| `frontend/src/flow/steps.ts` | `Step` union (5 steps) | ✓ VERIFIED | Exactly the 5 steps; `next`/`STEP_ORDER` present (unused — IN-01 advisory) |
| `frontend/src/reading/types.ts` | MockReading/Card/Summary mirroring READ-05/06 | ✓ VERIFIED | All fields present; pure type module |
| `frontend/src/reading/createReading.ts` | Async Phase-4 seam → MockReading | ✓ VERIFIED | `async`, returns Promise<MockReading>, D-07 reversals, injectable RNG; 11 tests green |
| `frontend/src/reading/cardPool.fixture.ts` | Bundled card pool (D-06) | ✓ VERIFIED | Present; drawn by createReading |
| `frontend/src/reading/copy.ts` | Centralized brand-safe copy + canonical `BANNED_BRAND_TOKENS` | ✓ VERIFIED | All copy centralized; ban-list incl. `ИИ` branch; 7 tests green |
| `frontend/src/lib/telegram.ts` | theme/insets/haptics, no-op outside Telegram | ✓ VERIFIED | All optional-chained; 10 tests green |
| `frontend/src/hooks/useOnboardingSeen.ts` | localStorage onboarding flag (ONB-04) | ✓ VERIFIED | try/catch-guarded; 3 tests green |
| `frontend/src/components/onboarding/OnboardingFlow.tsx` | Real 3–4 slide onboarding (replaces stub) | ✓ VERIFIED | 155 lines; no stub TODO remains |
| `frontend/src/components/ritual/RitualScreen.tsx` + `Particles.tsx` | ~3s 3-beat ritual + compositor particles | ✓ VERIFIED | 173 + 92 lines; compositor-only |
| `frontend/src/components/reveal/FlipCard.tsx` + `RevealScreen.tsx` | 3D flip + «Раскрыть все» stagger | ✓ VERIFIED | 103 + 176 lines; per-flip haptic |
| `frontend/src/components/result/ResultScreen.tsx` | Full result from MockReading | ✓ VERIFIED | 187 lines; meta+cards+summary+actions |
| `frontend/src/App.tsx` | Renders `<FlowRoot/>` in `<AuthGate>` | ✓ VERIFIED | Confirmed |

### Key Link Verification

| From | To | Via | Status |
|------|----|----|--------|
| App.tsx | FlowRoot.tsx | AuthGate child | ✓ WIRED |
| FlowRoot.tsx | selection.ts | `useSelection((s)=>s.step)` drives AnimatePresence key | ✓ WIRED |
| createReading.ts | cardPool.fixture.ts | draws positions.length cards | ✓ WIRED |
| OnboardingFlow.tsx | useOnboardingSeen.ts | `markOnboardingSeen()` on skip+CTA | ✓ WIRED |
| OnboardingFlow.tsx | selection.ts | `goTo('selection')` after seen | ✓ WIRED |
| CatalogScreen.tsx | createReading.ts | «Начать расклад» builds the reading | ✓ WIRED |
| CatalogScreen.tsx | selection.ts | `setReading(reading)` then `goTo('ritual')` (ordering proven: setReading BEFORE step change) | ✓ WIRED |
| CatalogScreen.tsx | SpreadCard.tsx | `onSelect → setSpread` (HOME-06, previously unwired) | ✓ WIRED |
| RitualScreen.tsx | telegram.ts | `haptic.notify('success')` on completion | ✓ WIRED |
| RitualScreen.tsx | selection.ts | `goTo('reveal')` after final beat | ✓ WIRED |
| RitualScreen.tsx | Particles.tsx | renders particle field | ✓ WIRED |
| FlipCard.tsx | telegram.ts | `haptic.impact('light')` on flip completion | ✓ WIRED |
| RevealScreen.tsx | selection.ts | reads `reading` slot + `goTo('result')` | ✓ WIRED |
| ResultScreen.tsx | selection.ts | «Ещё расклад» → `startReadingAgain()` (D-04) | ✓ WIRED |
| ResultScreen.tsx | copy.ts | labels + «скоро» from copy bank | ✓ WIRED |

### Data-Flow Trace (Level 4)

The single dynamic data source is the `reading` slot, populated by `createReading()` (the Phase-4 seam) at selection and consumed by ritual/reveal/result. This is the intended mock data flow (NOT a stub — Phase 4 swaps only the seam body for `POST /api/readings`).

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| ResultScreen.tsx | `reading` (useSelection) | `setReading(createReading(...))` at CatalogScreen | Yes — fully-populated MockReading (all READ-05/06 fields, asserted) | ✓ FLOWING (mock) |
| RevealScreen.tsx | `reading.cards[]` | same seam | Yes — one card per spread position | ✓ FLOWING (mock) |
| RitualScreen.tsx | `reading` (preload guard) | same seam | Yes (preload branch guarded; nav not guarded — WR-01 advisory) | ✓ FLOWING (mock) |

Note: result meta row renders raw slugs (`moon_mirror`/`three_card`) rather than RU labels (WR-02) — data flows correctly, but the displayed value is a slug not a label. Cosmetic for a mock; advisory, not a gap.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full frontend test suite | `cd frontend && npm run test -- --run` | 14 files / **77 tests passed** | ✓ PASS |
| Production build (tsc + vite) | `cd frontend && npm run build` | Green; `index.js 343.60 kB / gzip 110.14 kB` (LazyMotion budget held post-CR-01) | ✓ PASS |
| No stray full `motion.*` under LazyMotion (CR-01 class) | grep `import {…motion…} from "motion/react"` + `<motion.` | Zero matches (incl. DeckCard now `m.*`) | ✓ PASS |
| SAFE-06: banned tokens in user-facing copy | grep `нейросет\|сгенерирован\|модель` + standalone `ИИ` + `\bAI\b` | Only in comments/tests/regex def — **zero in copy** | ✓ PASS |
| No debt markers / unreplaced stubs | grep `TODO\|FIXME\|XXX\|TODO(plan 03-0X)` | None in source (placeholder hits are legit input/CSS/query) | ✓ PASS |

### Probe Execution

Not applicable — Phase 3 is a frontend mock with no `scripts/*/tests/probe-*.sh` and no probe declarations in PLAN/SUMMARY. The Vitest suite + build are the runnable verification surface (executed above).

### Requirements Coverage

All 18 declared phase requirement IDs accounted for. (Note: REQUIREMENTS.md Traceability table still shows HOME-03/04/05/06, READ-07, UI-01 as "Pending" — that column was last updated 2026-06-09, BEFORE Phase 3 execution, and is stale. The code evidence below supersedes it.)

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ONB-01 | 03-02 | 3–4 onboarding screens | ✓ SATISFIED | OnboardingFlow 3 slides + explainer + CTA |
| ONB-02 | 03-02 | Skippable | ✓ SATISFIED | Persistent «Пропустить»; test asserts skip→selection |
| ONB-03 | 03-02 | Plain reversed-cards explainer | ✓ SATISFIED | `REVERSED_EXPLAINER` (задержка/сопротивление/напряжение, never «плохо»); test-guarded |
| ONB-04 | 03-01/02 | Persisted, not re-shown | ✓ SATISFIED | `useOnboardingSeen` + FlowRoot mount gate; tested |
| HOME-01 | 03-01/03 | Question 10–500 + too-short hint | ✓ SATISFIED | `questionValidity` + CatalogScreen hint; tested |
| HOME-02 | 03-01/03 | Empty question valid (general) | ✓ SATISFIED | empty→valid; `RESULT_GENERAL` fallback; tested |
| HOME-03 | 03-03 | Pick 1 of 7 topics | ✓ SATISFIED | 7 `TOPICS` chips → setTopic |
| HOME-04 | 03-03 | Recommendation by topic (with reason) | ✓ SATISFIED | recommendation banner (title+reason); tested |
| HOME-05 | 03-03 | Deck carousel | ✓ SATISFIED | `DeckCarousel`→setDeck (re-themes); tested |
| HOME-06 | 03-03 | Spread selection | ✓ SATISFIED | `SpreadCard.onSelect`→setSpread (this phase wired the previously-dead link) |
| HOME-07 | 03-01/03 | Start gate on topic+deck+spread | ✓ SATISFIED | `canStart`; CTA disabled+hint until all set; tested |
| READ-07 | 03-04 | Ritual prep (beats/dim/particles/haptic) | ✓ SATISFIED (state/wiring; feel→human) | RitualScreen 3 beats + dimming + Particles + notify('success'); tested |
| READ-08 | 03-05 | Flip reveal + phrase + «open all» after first | ✓ SATISFIED (state; feel→human) | RevealScreen/FlipCard; tested |
| READ-09 | 03-06 | Result screen (meta/cards/summary/actions) | ✓ SATISFIED | ResultScreen; all fields + actions; tested |
| SAFE-06 | 03-01..06 | No AI/нейросеть/модель/сгенерировано ИИ in UI | ✓ SATISFIED | Centralized copy + `BANNED_BRAND_TOKENS` (incl. ИИ); full-source grep clean; tested |
| UI-01 | 03-03/04/05/06 | Premium-dark mobile-first + sticky CTA | ✓ SATISFIED (structure; render→human) | Glass surfaces, deck vars, sticky CTAs with insets |
| UI-03 | 03-01/04/05/06 | Microanimations via `motion` | ✓ SATISFIED (wiring; feel→human) | LazyMotion `m.*` flip/particles/stagger/haptic |
| UI-04 | 03-01/03 | Telegram theme + safe-area via SDK insets | ✓ SATISFIED (wiring; render→human) | `telegram.ts` SDK insets (not env()); applied in CTAs |

**Orphaned requirements:** None. Every ID mapped to Phase 3 in REQUIREMENTS.md (ONB-01..04, HOME-01..07, READ-07/08/09, SAFE-06, UI-01/03/04) is claimed by at least one plan's `requirements` field and verified above.

### Anti-Patterns Found

The 2 code-review BLOCKERs were confirmed FIXED in the codebase:

| Item | File | Status | Evidence |
|------|------|--------|----------|
| CR-01 (full `motion.*` under LazyMotion) | CatalogScreen.tsx | ✓ FIXED | Now `import * as m from "motion/react-m"` (line 2) + `<m.button>` (line 266); zero `<motion.` anywhere; bundle 110kb gzip |
| CR-02 (reveal→ritual back replays ritual) | RevealScreen.tsx | ✓ FIXED | The broken «Назад»/back-to-ritual affordance was removed; RevealScreen has only «Раскрыть все» + «Перейти к итогу» (goTo("result")) |

Advisory items (WARNING/INFO) — do NOT fail the phase:

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| ritual/RitualScreen.tsx | 60-83 | WR-01: nav to reveal not guarded by `reading` (only preload is) | ⚠️ Warning (latent) | Selection always sets reading first; latent blank-screen only on a hypothetical direct `goTo('ritual')` |
| result/ResultScreen.tsx | 63-65 | WR-02: meta row shows raw slugs (`moon_mirror`/`three_card`) | ⚠️ Warning (cosmetic) | Payoff surface shows slugs not RU labels; cosmetic for a mock |
| reading/createReading.ts | 37-46 | WR-03: JSDoc "without repetition" but `i % len` wraps on overflow | ⚠️ Warning (latent) | Unreachable with 22-card pool + 3–4-card spreads |
| components/CatalogScreen.tsx | 35 | WR-04: stale comment ("ritual is Phase 3, not built here") | ⚠️ Warning (doc drift) | Misleading next reader; handleStart now does build it |
| components/CatalogScreen.tsx | 74-95 | WR-05: `isStarting` not reset on success path | ⚠️ Warning (latent) | Benign — `goTo('ritual')` unmounts the screen |
| reveal/RevealScreen.tsx | 89-147 | WR-06: later-flipped cards' detail mounts with no enter animation | ⚠️ Warning (cosmetic) | Stagger "gather" only plays for cards present at first flip |
| flow/steps.ts, reading/copy.ts | — | IN-01: `next`/`STEP_ORDER`/`REVEAL_ENTRY`/`REVEAL_OPEN_CARD` unused | ℹ️ Info | Dead exports; drift risk |
| reveal/FlipCard.tsx | 38 | IN-02: hardcoded "Открыть карту" (not from copy.ts) | ℹ️ Info | Outside the copy.test.ts scan net (still brand-safe) |
| lib/telegram.ts | 92-99 | IN-03: `getColorScheme`/`getThemeParams` unused in scope | ℹ️ Info | Theme consumer is future work; not orphaned-confirmed |
| reveal/RevealScreen.tsx | 159-171 | IN-04: sticky "Перейти к итогу" bar lacks safe-area bottom padding | ℹ️ Info | May sit under home indicator; the other two screens add insets.bottom |

### Human Verification Required

Six items require on-device / in-Telegram confirmation (the automated tests prove state/wiring/data; the rendered feel does not). These are carried in the frontmatter `human_verification` block and mirror the 03-VALIDATION "Manual-Only" rows. Summary:

1. **End-to-end transition smoothness** — onboarding→result, no jank/pop-in (UI-01/UI-03/D-01).
2. **Ritual prep ~3s + completion haptic + tap-to-skip** — timing feel + native haptic (READ-07/D-08).
3. **Flip reveal + «раскрыть все» + per-flip haptic** — flip choreography feel (READ-08/D-09).
4. **Telegram light/dark theme + safe-area on a notched device** — SDK insets render (UI-04).
5. **Per-deck theme carries into ritual/reveal/result** — visual continuity (UI-02 carry).
6. **Sticky CTA above the iOS keyboard** — keyboard overlap (UI-01/HOME-07).

### Gaps Summary

**No gaps.** Every observable truth is verified at the automated (state/wiring/data) layer, all 18 requirement IDs are accounted for, both code-review BLOCKERs are confirmed fixed in code, the 77-test suite and production build are green, and the SAFE-06 brand-voice gate is clean across the entire frontend source. The mock-stays-a-mock architecture is respected (single `createReading()` seam, `reading` only in Zustand, no real POST/LLM/client draw) — the absence of real generation/limits/payments/history is by design (Phase 4+), not a gap.

Status is **human_needed** (not `passed`) strictly because the phase's success criteria are inherently visual/haptic/Telegram-client-bound: the automated layer proves the contract is wired and the state machine is correct, but animation feel, native haptics, and real-device theme/safe-area/keyboard behavior can only be confirmed by a human in the Telegram client. This is the expected terminal state for a UI/MVP-mode mock phase per 03-VALIDATION.

The 6 warnings + 4 info from the code review are advisory and tracked above; none blocks the phase goal. Recommend addressing WR-02 (raw slugs on the result screen) and WR-01 (ritual nav guard) opportunistically before or during Phase 4, since Phase 4 edits the same seam.

---

_Verified: 2026-06-12T15:10:00Z_
_Verifier: Claude (gsd-verifier)_
