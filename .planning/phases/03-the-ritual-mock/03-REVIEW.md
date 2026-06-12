---
phase: 03-the-ritual-mock
reviewed: 2026-06-12T00:00:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - frontend/src/App.tsx
  - frontend/src/components/CatalogScreen.tsx
  - frontend/src/components/onboarding/OnboardingFlow.tsx
  - frontend/src/components/result/ResultScreen.tsx
  - frontend/src/components/reveal/FlipCard.tsx
  - frontend/src/components/reveal/RevealScreen.tsx
  - frontend/src/components/ritual/Particles.tsx
  - frontend/src/components/ritual/RitualScreen.tsx
  - frontend/src/flow/FlowRoot.tsx
  - frontend/src/flow/steps.ts
  - frontend/src/hooks/useOnboardingSeen.ts
  - frontend/src/lib/telegram.ts
  - frontend/src/reading/cardPool.fixture.ts
  - frontend/src/reading/copy.ts
  - frontend/src/reading/createReading.ts
  - frontend/src/reading/types.ts
  - frontend/src/stores/selection.ts
findings:
  critical: 2
  warning: 6
  info: 4
  total: 12
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-06-12
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Reviewed the full Phase-3 reading journey (onboarding → selection → ritual → flip-reveal → result) plus its mock data seam, store, and Telegram bridge. The mock-stays-a-mock architecture is respected (no real POST, no LLM, no client draw beyond the fixture; `createReading` is the single Phase-4 seam), the `reading` slot lives only in Zustand and is never mirrored into TanStack Query, brand voice / SAFE-06 ban-list is centralized and tested, and the untrusted question is consistently a React text node (no `dangerouslySetInnerHTML` anywhere). Compositor-only motion is correct in the reveal/ritual/particles files.

Two BLOCKERs were found:

1. `CatalogScreen.tsx` — a project file modified this phase — imports the full `motion` API and renders `<motion.button>` while it is mounted **inside** `FlowRoot`'s `<LazyMotion features={domAnimation}>`. This is the exact `motion` import-discipline violation the project bans (D-10 / PATTERNS Pitfall 5) and it defeats the LazyMotion bundle-size goal.
2. The in-app back affordance (D-03) on the reveal screen pops history to `ritual`, which re-mounts and re-runs the entire ~3s ritual timeline, then auto-advances forward to a reveal whose flip state has been reset. "Назад" is effectively broken for the reveal→ritual transition.

Plus six warnings (stale/contradictory doc comment that now mis-states an architecture fact, missing `reading` guard in `RitualScreen`, raw slugs shown to users on the result screen, a "without repetition" claim the draw helper does not honor on overflow, an unreset `isStarting` flag, and a one-by-one reveal that skips its enter animation) and four info items.

## Critical Issues

### CR-01: `CatalogScreen` uses the full `motion.*` API inside `LazyMotion` (D-10 / Pitfall 5)

**File:** `frontend/src/components/CatalogScreen.tsx:2,266-282`
**Issue:** `CatalogScreen` is registered in `FlowRoot` as the `selection` screen (`SCREENS.selection = CatalogScreen`) and is therefore rendered **inside** `<LazyMotion features={domAnimation}>` (FlowRoot.tsx:56). It imports the full bundle (`import { motion } from "motion/react"`) and renders `<motion.button …>` for the sticky CTA. The whole point of `LazyMotion` + `m.*` from `motion/react-m` (stated in FlowRoot.tsx:6-9 and every sibling screen) is to ship the ~4.6 kB lazy feature set instead of the full ~34 kB. Mixing a full `motion.*` component under `LazyMotion` is the documented failure mode (Pitfall 5): it re-introduces the full motion runtime into the bundle and motion warns against combining the two APIs in the same tree. Every other Phase-3 screen (Onboarding, Ritual, Particles, Reveal, FlipCard, Result) correctly uses `m.*`; this one regressed. (Note: `DeckCard.tsx` has the same pattern and is also rendered under this `LazyMotion` via `DeckCarousel`, but it is out of this review's file scope — flagging here for awareness.)
**Fix:**
```tsx
// CatalogScreen.tsx — replace the full-API import with the namespace form
import * as m from "motion/react-m";
// ...
// and the element:
<m.button
  type="button"
  whileTap={{ scale: 0.97 }}
  disabled={!ready || isStarting}
  onClick={handleStart}
  aria-disabled={!ready || isStarting}
  className="…"
  style={{ … }}
>
  {START_CTA}
</m.button>
```

### CR-02: In-app back from the reveal screen re-runs the entire ritual (D-03 broken)

**File:** `frontend/src/components/reveal/RevealScreen.tsx:80-87`, `frontend/src/stores/selection.ts:104-113`
**Issue:** Trace the forward path: `selection` → `goTo("ritual")` pushes `selection` onto `history`; `ritual` → `goTo("reveal")` pushes `ritual`. So on the reveal screen `history` ends with `[…, "selection", "ritual"]`. The reveal screen's «Назад» calls `back()`, which restores the **previous** step = `"ritual"`. `RitualScreen` then re-mounts, its `useEffect` timer starts a fresh ~3 s, 3-beat timeline (the `startedRef`/`finishedRef` guards are per-mount, so a fresh mount runs again), and on completion `finish()` calls `goTo("reveal")` — landing the user back on reveal with all `flipped`/`read` state reset to empty `Set`s. The user cannot actually step *back* out of the reveal; "Назад" sends them on a forced loop through the ritual. This violates D-03 (history-backed in-app back should move the user backward, not replay an animation gate). The same trap exists for `result` → back → `reveal` only if reveal is the immediate predecessor, but the ritual replay is the concrete, reproducible defect.
**Fix:** Either skip `ritual` when navigating back into it, or have the ritual treat an already-built reading as "resume" instead of "replay". Minimal correct option — make `back()` skip transient gate steps:
```ts
// selection.ts — back() skips the ritual gate when popping into it
back: () =>
  set((state) => {
    if (state.history.length === 0) return {};
    let history = state.history.slice(0, -1);
    let prev = state.history[state.history.length - 1];
    // The ritual is a forward-only gate; never land on it via back.
    while (prev === "ritual" && history.length > 0) {
      prev = history[history.length - 1];
      history = history.slice(0, -1);
    }
    if (prev === "ritual") return {}; // nothing safe to go back to
    return { step: prev, history };
  }),
```
(Add a store unit test asserting `reveal → back` lands on `selection`, not `ritual`.)

## Warnings

### WR-01: `RitualScreen` advances to `reveal` even when `reading` is `null`

**File:** `frontend/src/components/ritual/RitualScreen.tsx:60-83`
**Issue:** The beat timer runs unconditionally on mount and `finish()` calls `goTo("reveal")` regardless of whether a `reading` exists. The art-preload block is correctly guarded (`reading && reading.cards.length > 0`, line 158), but the *navigation* is not. If the ritual is ever reached without a built reading — e.g. the FlowRoot mount-correction edge, a future refresh-into-step, or a direct `goTo("ritual")` — the timeline still fires and pushes the user into `RevealScreen`/`ResultScreen`, which then render their empty defensive placeholder (`<main … />`). The user sees a blank screen after a 3 s ritual with no recovery path. Today selection is the only caller and always sets the reading first, so this is latent, not live — hence WARNING — but the guard is cheap and the failure mode is a dead-end blank screen.
**Fix:** Bail the ritual back to selection when there is no reading:
```tsx
const reading = useSelection((s) => s.reading);
useEffect(() => {
  if (!reading) {
    useSelection.setState({ step: "selection" });
  }
}, [reading]);
// …and/or guard finish(): if (!useSelection.getState().reading) return goTo("selection");
```

### WR-02: Result screen shows raw machine slugs to the user

**File:** `frontend/src/components/result/ResultScreen.tsx:64-66`
**Issue:** The meta row renders `r.topic`, `r.deckSlug`, and `r.spreadSlug` verbatim as the displayed values. These are slugs (`love`, `moon_mirror`, `three_card`), not human labels. The result screen is the product's payoff surface (READ-09); showing `moon_mirror` / `three_card` instead of «Луна» / «Расклад на три карты» is a visible quality/brand defect and is inconsistent with the rest of the UI, which uses RU labels (e.g. `TOPICS` maps `love → «Любовь»` in CatalogScreen). `topic` can reuse the existing `TOPICS` label map; deck/spread labels are available from the already-loaded catalog queries (deck title / spread title).
**Fix:** Resolve slugs to labels before rendering. At minimum map the topic via the shared `TOPICS` table, and carry the chosen deck/spread *titles* into the reading (or look them up from the catalog) so the row reads «Любовь / Луна / Расклад на три карты». Avoid re-deriving the label list ad hoc — extract the topic map to a shared module both screens import.

### WR-03: `drawCards` claims "without repetition" but silently repeats on overflow

**File:** `frontend/src/reading/createReading.ts:37-46`
**Issue:** The JSDoc says "Pick `count` cards from the pool without repetition (wraps if count exceeds the pool)". The implementation indexes `CARD_POOL[indices[i % indices.length]]`. When `count <= pool.length` (the only case the 22-card fixture + 3–4-card spreads hit today) this is unique and correct. But the `i % indices.length` wrap means if a future spread requests `count > 22`, cards silently repeat — directly contradicting the "without repetition" contract in the same comment, and a repeated card in a single spread is a correctness bug for a tarot draw. It is latent (not reachable with the current fixture), hence WARNING, but the contract and code disagree.
**Fix:** Make the contract explicit and fail loud (or de-dupe) instead of silently wrapping:
```ts
function drawCards(count: number, rng: () => number): PoolCard[] {
  if (count > CARD_POOL.length) {
    throw new Error(`drawCards: requested ${count} > pool ${CARD_POOL.length}`);
  }
  const indices = CARD_POOL.map((_, i) => i);
  for (let i = indices.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rng() * (i + 1));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }
  return indices.slice(0, count).map((idx) => CARD_POOL[idx]);
}
```

### WR-04: Stale comment in `CatalogScreen` now mis-states a live architecture fact

**File:** `frontend/src/components/CatalogScreen.tsx:35`
**Issue:** The header comment ends: "The «Начать расклад» ritual is Phase 3 (not built here)." As of this phase the ritual hand-off **is** built in this exact file — `handleStart` calls `createReading(...)`, `setReading(reading)`, then `goTo("ritual")` (lines 66-96). A comment asserting the opposite of what the code now does is actively misleading for the next reader and contradicts the file's own `handleStart`. Doc drift on the single Phase-4 seam file is worth fixing because this is the one boundary a future engineer will edit.
**Fix:** Update the comment to describe the now-present behavior, e.g. "«Начать расклад» builds the MockReading via the `createReading` seam, deposits it with `setReading`, then advances to `ritual` (D-05)."

### WR-05: `isStarting` is never reset on the success path

**File:** `frontend/src/components/CatalogScreen.tsx:74-95`
**Issue:** `handleStart` sets `setIsStarting(true)` then, on success, calls `setReading` + `goTo("ritual")` without resetting `isStarting`. It is reset only in the `catch`. Today this is benign because `goTo("ritual")` unmounts `CatalogScreen` (AnimatePresence `mode="wait"`), discarding the state. But it couples correctness to "navigation always unmounts this component": if the step switch is ever blocked, deferred, or the user returns to selection via `startReadingAgain` without a remount of fresh state, the CTA stays disabled (`disabled={!ready || isStarting}`) with no way to recover. The error path's `setIsStarting(false)` shows the author intended a symmetric reset.
**Fix:** Reset in a `finally`, or reset right before navigating:
```ts
try {
  const reading = await createReading({ … });
  setReading(reading);
  setIsStarting(false); // symmetric with the catch
  goTo("ritual");
} catch {
  setStartError(true);
  setIsStarting(false);
}
```

### WR-06: One-by-one revealed card details mount with no enter animation

**File:** `frontend/src/components/reveal/RevealScreen.tsx:89-147`
**Issue:** The per-card detail block is an `m.div variants={detailItem}` whose enter/exit is driven by the **parent** container's `animate={anyFlipped ? "reveal" : "rest"}` + `delayChildren: stagger(...)`. The parent flips to `"reveal"` on the *first* flip. Each card's `m.div` is conditionally rendered only `{isFlipped && (…)}`. When the user flips a *later* card after the parent is already in `"reveal"`, the new `m.div` mounts directly into the resolved `reveal` variant — Framer/motion's `variants` propagate the current parent state to a newly-mounted child without replaying the `rest→reveal` transition, so subsequent cards' details pop in with no fade/slide. The intended staggered "gather" only plays for the cards present at the first flip. Cosmetic (atmosphere is a stated product pillar), so WARNING not BLOCKER.
**Fix:** Drive each detail's animation locally instead of via the shared parent state, e.g. give the detail its own `initial="rest" animate="reveal"` (it mounts only when flipped, so it always plays), or wrap the detail in its own `AnimatePresence`. Removes the dependence on parent-state timing.

## Info

### IN-01: `next()` / `STEP_ORDER` / `REVEAL_ENTRY` / `REVEAL_OPEN_CARD` appear unused

**File:** `frontend/src/flow/steps.ts:9-27`, `frontend/src/reading/copy.ts:78,82`
**Issue:** `next()` and `STEP_ORDER` are exported but no non-test caller uses them (navigation goes through `goTo`/`back`). `REVEAL_ENTRY` ("Открой первую карту") and `REVEAL_OPEN_CARD` ("Открыть карту") are exported copy constants with no importer — the reveal screen uses inline `"Открыть карту"` via `FlipCard`'s `aria-label` and never imports these. Dead exports add surface and drift risk (the inline `"Открыть карту"` in FlipCard.tsx:38 duplicates `REVEAL_OPEN_CARD`).
**Fix:** Either wire them (`FlipCard` should use `REVEAL_OPEN_CARD` rather than an inline literal, keeping all copy in `copy.ts` per SAFE-06 centralization) or drop the unused constants. Prefer wiring the FlipCard label.

### IN-02: `FlipCard` hardcodes the "Открыть карту" label instead of sourcing it from `copy.ts`

**File:** `frontend/src/components/reveal/FlipCard.tsx:38`
**Issue:** `aria-label={flipped ? card.name : "Открыть карту"}` inlines a user-facing RU string. The project rule is that all user-facing copy is centralized in `reading/copy.ts` so the SAFE-06 ban-list scan covers it; `REVEAL_OPEN_CARD` already holds exactly this string. An inlined literal is outside the `copy.test.ts` scan net.
**Fix:** `import { REVEAL_OPEN_CARD } from "../../reading/copy"` and use it for the label.

### IN-03: `getColorScheme` / `getThemeParams` exported from telegram.ts but unused in scope

**File:** `frontend/src/lib/telegram.ts:92-99`
**Issue:** Minor — these two helpers have no importer among the reviewed files. Not a defect (they may be consumed by theme code outside scope), noted only for dead-code tracking. The safe-area and haptic helpers are correctly used (CatalogScreen, ResultScreen, FlipCard, RitualScreen). No action required unless confirmed orphaned.
**Fix:** Confirm a consumer exists (theme module) or remove.

### IN-04: `RevealScreen` sticky "Перейти к итогу" bar may overlap the last card

**File:** `frontend/src/components/reveal/RevealScreen.tsx:170-182`
**Issue:** The "Перейти к итогу" button is `fixed inset-x-0 bottom-0`; the scroll container uses `pb-28`. With a fully-expanded last card (flipped + read interpretation), the fixed bar can overlap the final card's text on shorter viewports (360–430 px target). Cosmetic/UX, no functional break. The bar also has no safe-area bottom padding, unlike `ResultScreen` (which adds `insets.bottom`) — on a notched device the CTA can sit under the home indicator.
**Fix:** Add safe-area bottom padding to the fixed bar (`paddingBottom: 12 + getSafeAreaInsets().bottom`) and verify `pb-28` clears the bar height at 360 px.

---

_Reviewed: 2026-06-12_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
