# Phase 3: The Ritual (mock) - Pattern Map

**Mapped:** 2026-06-11
**Files analyzed:** 17 new/modified
**Analogs found:** 16 / 17 (1 type-only file has no behavioral analog — uses RESEARCH shapes)

> Every analog below was read in full. Excerpts are verbatim from `frontend/src/`. The executor should mirror these patterns rather than invent new ones — the codebase has a tight, consistent house style (deck-var theming, glass surfaces, `motion` micro-interactions, Zustand-for-UI / Query-for-server, in-character RU copy).

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `stores/selection.ts` (MODIFY) | store | event-driven (step machine) | `stores/selection.ts` (self) + `stores/session.ts` | exact (extends existing) |
| `reading/types.ts` (NEW) | type | transform (data contract) | `api/spreads.ts` (interface shapes) | role-match |
| `reading/createReading.ts` (NEW) | util (Phase-4 seam) | request-response (async builder) | `api/decks.ts` `fetchDecks` | role-match (seam shape) |
| `reading/cardPool.fixture.ts` (NEW) | fixture | transform (static data) | `CatalogScreen.tsx` `TOPICS` const | role-match |
| `reading/copy.ts` (NEW) | util (copy module) | transform (static strings) | `CatalogScreen.tsx` `TOPICS` + `AuthGate.tsx` strings | role-match |
| `hooks/useOnboardingSeen.ts` (NEW) | hook | file-I/O (localStorage) | `theme/useDeckTheme.ts` + `lib/telegram.ts` | role-match |
| `lib/telegram.ts` (MODIFY) | util (SDK seam) | request-response (platform reads) | `lib/telegram.ts` (self) | exact (extends existing) |
| `flow/steps.ts` (NEW) | util (step union + helpers) | transform | `stores/session.ts` `AuthStatus` union | role-match |
| `flow/FlowRoot.tsx` (NEW) | component (root switch) | event-driven (AnimatePresence) | `App.tsx` + `AuthGate.tsx` status-switch | partial (new primitive, RESEARCH Pattern 1) |
| `components/onboarding/OnboardingFlow.tsx` (NEW) | component | event-driven (slide index) | `CatalogScreen.tsx` (screen) + `DeckCarousel.tsx` (index map) | role-match |
| `components/CatalogScreen.tsx` (MODIFY) | component | event-driven | `CatalogScreen.tsx` (self) | exact (extends existing) |
| `components/ritual/RitualScreen.tsx` (NEW) | component | streaming (timed beats) | `AuthGate.tsx` (effect + status render) | role-match |
| `components/ritual/Particles.tsx` (NEW) | component | streaming (looping motion) | `DeckCard.tsx` (`motion` + deck vars) | role-match |
| `components/reveal/RevealScreen.tsx` (NEW) | component | event-driven (per-card flip) | `CatalogScreen.tsx` + `DeckCarousel.tsx` | role-match |
| `components/reveal/FlipCard.tsx` (NEW) | component | event-driven (tap → rotateY) | `DeckCard.tsx` (`motion.button` + CardArt) | role-match |
| `components/result/ResultScreen.tsx` (NEW) | component | request-response (renders MockReading) | `CatalogScreen.tsx` + `SpreadCard.tsx` + `AuthGate.tsx` | role-match |
| (tests) `*.test.ts(x)` (NEW) | test | — | `selection.test.ts`, `DeckCarousel.test.tsx`, `CatalogScreen.test.tsx` | exact |

**Match-quality coverage:** exact = 4 · role-match = 11 · partial = 1 · no-analog = 1 (`reading/types.ts` shape only — values come from RESEARCH "mock reading type").

---

## Shared Patterns

> These cross-cutting patterns apply to **every** new component. Apply them before reaching for any per-file detail.

### Shared 1 — Deck-variable theming (apply to ALL new screens: onboarding, ritual, reveal, result)
**Source:** `components/DeckCard.tsx` (lines 38-48), `components/TopicChip.tsx` (lines 16-28), `theme/deckThemes.css` (lines 6-11)
**Rule (UI-SPEC):** never hardcode a deck hex. Read the 4 vars `--deck-bg / --deck-deep / --deck-accent / --deck-soft`. The glass surface + active-accent recipe is fixed — copy it verbatim:
```tsx
// Glass surface (Secondary 30% — deck tiles, result cards, summary panel, onboarding slide):
style={{
  background:
    "linear-gradient(155deg, color-mix(in srgb, var(--deck-bg) 88%, transparent), color-mix(in srgb, var(--deck-deep) 72%, transparent))",
  borderColor: active
    ? "var(--deck-accent)"
    : "color-mix(in srgb, var(--deck-soft) 22%, transparent)",
  boxShadow: active
    ? "0 0 0 1px var(--deck-accent), 0 14px 44px -18px var(--deck-accent)"
    : "0 12px 32px -22px #000",
}}
```
The root default palette (`:root` in `deckThemes.css` lines 6-11) covers pre-selection onboarding automatically. `--deck-soft` is the primary text ink; titles use it at full opacity, eyebrows at `opacity-70`, tertiary at `opacity-60` (the "opacity ladder").

### Shared 2 — `motion` micro-interaction defaults (apply to every tappable)
**Source:** `components/DeckCard.tsx` (lines 1, 32-37), `components/TopicChip.tsx` (line 16), `components/SpreadCard.tsx` (line 18)
**Rule:** every tappable gets compositor-only feedback. The codebase already imports `motion` from `motion/react` and uses `whileHover` / `whileTap`:
```tsx
import { motion } from "motion/react";
// tiles/buttons:
<motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }} aria-pressed={active} type="button" ... />
// chips (slightly larger pop): hover:scale-[1.05] active:scale-95  (TopicChip uses CSS transition-transform)
```
> **Phase-3 override (RESEARCH Pitfall 5 / D-10):** inside `FlowRoot`'s `<LazyMotion features={domAnimation}>`, new motion code must use `m.*` from `motion/react-m`, NOT `motion.*`. The existing components keep `motion.*` (they render outside the LazyMotion boundary today); when CatalogScreen mounts under FlowRoot it still works, but **new** files added inside the flow should prefer `m.*`. Document this seam clearly in the plan.

### Shared 3 — Zustand selector usage (apply to every component that reads flow state)
**Source:** `components/CatalogScreen.tsx` (lines 26-29), `components/AuthGate.tsx` (lines 20-25)
**Rule:** subscribe with one-field selectors, never destructure the whole store (keeps re-renders minimal):
```tsx
const step = useSelection((s) => s.step);
const goTo = useSelection((s) => s.goTo);
```

### Shared 4 — In-character RU copy + SAFE-06 ban-list (apply to ALL new strings)
**Source:** `components/AuthGate.tsx` (lines 61-66, 71-73), `components/CatalogScreen.tsx` (lines 63-67, 73-76)
**Rule:** mirror the established voice — «Колода…», «Зеркало…», soft and non-fatalistic. The existing error/loading strings are the tone reference ("Колода не узнала тебя.", "Зеркало вглядывается в тебя…", "Колода сейчас молчит."). The test already asserts the ban-list inline (see Shared 6 excerpt) — centralize new copy in `reading/copy.ts` so `reading/copy.test.ts` can scan it.

### Shared 5 — Async/error seam shape (apply to `createReading.ts`)
**Source:** `api/decks.ts` (lines 23-44), `api/spreads.ts` (lines 41-53)
**Rule:** the data-access functions are `async` + return a typed Promise + throw a typed error on failure. `createReading` is the Phase-4 fetch boundary, so shape it like `fetchDecks` so the later swap is mechanical:
```ts
// api/decks.ts — the seam shape createReading() should echo:
export async function fetchDecks(): Promise<Deck[]> {
  const res = await apiFetch("/api/decks");
  if (!res.ok) throw new CatalogError(res.status);
  return (await res.json()) as Deck[];
}
```
Phase 3 body = build from the fixture (no `apiFetch`); Phase 4 body = `POST /api/readings`. **Return type unchanged.** The UI-SPEC error copy ("Колода замолчала на мгновение…") is the future failure-state string.

### Shared 6 — Vitest + RTL test pattern (apply to ALL new tests)
**Source:** `components/CatalogScreen.test.tsx` (full), `stores/selection.test.ts` (full), `components/DeckCarousel.test.tsx` (full)
**Store tests** reset via `setState` in `beforeEach`, drive via `getState()`:
```ts
import { beforeEach, describe, expect, test } from "vitest";
import { useSelection } from "./selection";
beforeEach(() => {
  useSelection.setState({ topic: null, deckSlug: null, spreadSlug: null });
});
test("setDeck updates only deckSlug (no cross-field mutation)", () => {
  useSelection.getState().setDeck("moon_mirror");
  expect(useSelection.getState().deckSlug).toBe("moon_mirror");
});
```
**Component tests** use `@testing-library/react` `render` + `fireEvent` + `getByText`; deck/spread fixtures are built with `Array.from`. The SAFE-06 gate is already modeled inline here — reuse the exact regex:
```ts
expect(/ai|нейросет|модель|сгенерирован/i.test(REASON)).toBe(false);
```
Components needing TanStack Query use `renderWithClient` from `src/test/renderWithClient.tsx` and `vi.stubGlobal("fetch", ...)` (CatalogScreen.test.tsx lines 43-60). Pure presentational components use plain `render` (DeckCarousel.test.tsx). Both assert the empty/nothing-broken path.

---

## Pattern Assignments

### `stores/selection.ts` (MODIFY — store, event-driven step machine)

**Analog:** `stores/selection.ts` (self) + `stores/session.ts`

**Existing store to extend** (selection.ts lines 5-23) — keep the existing fields/setters, add the flow slice:
```ts
import { create } from "zustand";
export interface SelectionState {
  topic: string | null;
  deckSlug: string | null;
  spreadSlug: string | null;
  setTopic: (topic: string | null) => void;
  setDeck: (deckSlug: string | null) => void;
  setSpread: (spreadSlug: string | null) => void;
}
export const useSelection = create<SelectionState>((set) => ({
  topic: null, deckSlug: null, spreadSlug: null,
  setTopic: (topic) => set({ topic }),
  setDeck: (deckSlug) => set({ deckSlug }),
  setSpread: (spreadSlug) => set({ spreadSlug }),
}));
```

**Union-type-in-store pattern** to mirror for `Step` (session.ts lines 9-13):
```ts
export type AuthStatus = "idle" | "authenticating" | "authenticated" | "error";
```

**Derived-value pattern** to mirror for `canStart` / question validity (session.ts lines 30-37 — a pure helper computing derived state, clamped):
```ts
function deriveAvailableReadings(response: AuthResponse): number {
  const { limits } = response;
  const freeRemaining = Math.max(0, limits.free_weekly_limit - limits.free_used_this_week);
  return freeRemaining + Math.max(0, limits.paid_spreads_balance);
}
```

**Action shape** to mirror (session.ts lines 45-57 — actions call `set` with a partial; failure path resets cleanly):
```ts
setAuthenticating: () => set({ status: "authenticating" }),
setError: () => set({ jwt: null, user: null, availableReadings: 0, status: "error" }),
```

**What to add** (from RESEARCH "Extend selection.ts" + UI-SPEC state machine): `question: string`, `reversalsEnabled: boolean`, `step: Step` (`"onboarding"|"selection"|"ritual"|"reveal"|"result"`), `history: Step[]`, and actions `setQuestion`, `toggleReversals`, `goTo`, `back`, `startReadingAgain`. **D-04 contract:** `startReadingAgain` = `goTo("selection")` WITHOUT clearing `question`/`topic`; deck/spread stay re-selectable. **D-13 question rule** as a derived helper: empty → valid (general); 1–9 → hint; 10–500 → valid; >500 → clamp/hint. **HOME-07** `canStart` = `Boolean(topic && deckSlug && spreadSlug)`.

> **Architecture guard (CONTEXT "Established Patterns"):** server lists (decks/spreads) stay in TanStack Query — never mirror them here. The mock reading is ephemeral client state and may live in this store or local component state, but NOT in Query.

---

### `reading/types.ts` (NEW — type, data contract) · NO behavioral analog

**Analog:** shape-only match to `api/spreads.ts` (lines 7-26 — the interface-stacking style).

**Interface style to mirror** (spreads.ts — exported interfaces, nullable fields explicit, nested types named):
```ts
export interface SpreadPosition {
  position_index: number;
  title: string;
  description: string | null;
  prompt_instruction: string | null;
}
export interface Spread {
  slug: string;
  title: string;
  card_count: number;
  positions: SpreadPosition[];
}
```

**Content (the actual fields)** comes from RESEARCH "The Phase-4 seam — mock reading type" (verbatim target), mirroring future READ-05/06: `Orientation = "upright"|"reversed"`; `MockReadingCard { name, positionTitle, orientation, shortMeaning, interpretation, deckAccent, shortPhrase }`; `MockReadingSummary { linkage, mainFactor, attention, softAdvice, closingPhrase }`; `MockReading { question: string|null, topic, deckSlug, spreadSlug, createdAt, cards[], summary }`. **D-05:** field names must anticipate the backend `response_models` so Phase 4 is a drop-in source swap.

---

### `reading/createReading.ts` (NEW — util, the Phase-4 seam)

**Analog:** `api/decks.ts` `fetchDecks` (lines 34-38) — see **Shared 5** for the seam excerpt.

**Builder logic** (RESEARCH "createReading.ts"): (1) draw `positions.length` cards from `cardPool.fixture`; (2) orientation per card — `reversalsEnabled ? (Math.random() < 0.3 ? "reversed" : "upright") : "upright"` (D-07); (3) assemble deck-tinted brand-safe per-card copy + summary → return `MockReading`. Signature mirrors RESEARCH:
```ts
export async function createReading(params: {
  question: string | null; topic: string; deckSlug: string; spreadSlug: string;
  reversalsEnabled: boolean; positions: { title: string }[];
}): Promise<MockReading> { /* fixture build now; POST /api/readings later */ }
```
> The `positions` come from the chosen spread's `Spread.positions` (`api/spreads.ts` line 20) — already available in the selection screen.

---

### `reading/cardPool.fixture.ts` (NEW — fixture, static data)

**Analog:** `components/CatalogScreen.tsx` `TOPICS` const (lines 10-18) — the established "typed const array of `{slug, label}`" fixture pattern:
```ts
const TOPICS: { slug: string; label: string }[] = [
  { slug: "love", label: "Любовь" },
  { slug: "work", label: "Работа" },
  // ...
];
```
**Content:** a small bundled array of `{ name, shortMeaning }` (D-06). RESEARCH Open Question #1 recommends a curated ~22 Major Arcana subset; if the Phase-1 `cards` seed JSON is readable, transcribe a slice for name/meaning fidelity. Keep it a single typed const — no `/api/cards`.

---

### `reading/copy.ts` (NEW — util, centralized copy module)

**Analog:** `components/AuthGate.tsx` strings (lines 61-66, 72-73) + `CatalogScreen.tsx` `TOPICS` (lines 10-18) for the const-bank shape.

**Voice reference** (AuthGate — copy this register exactly):
```tsx
"Колода не узнала тебя. Открой ритуал из Telegram, чтобы зеркало отразило твой путь."
const greeting = name ? `Колода знает тебя, ${name}.` : "Колода чувствует твоё присутствие.";
```
**Content:** all new user-facing strings (onboarding ×4 + ONB-03 reversed-cards explainer, ritual beats, per-card short phrases, result labels, hints, error state) — verbatim targets are in UI-SPEC "Copywriting Contract". **SAFE-06:** centralize here so `reading/copy.test.ts` can scan the module with the existing regex `/ai|нейросет|модель|сгенерирован/i` (CatalogScreen.test.tsx line 79). ONB-03 framing: «задержка / внутреннее сопротивление / скрытое напряжение», never «плохо/приговор».

---

### `hooks/useOnboardingSeen.ts` (NEW — hook, localStorage)

**Analog:** `theme/useDeckTheme.ts` (lines 8-13 — tiny single-purpose hook with a side effect) + `lib/telegram.ts` (the try/guard-around-a-platform-API pattern, lines 34-47).

**Hook shape to mirror** (useDeckTheme.ts — minimal, one effect, one concern):
```ts
import { useEffect } from "react";
import { useSelection } from "../stores/selection";
export function useDeckTheme(): void {
  const deckSlug = useSelection((s) => s.deckSlug);
  useEffect(() => {
    document.documentElement.dataset.deck = deckSlug ?? "";
  }, [deckSlug]);
}
```
**Guard pattern to mirror** (telegram.ts — wrap the platform read, never throw, fall back gracefully):
```ts
export function getInitData(): string {
  const fromTelegram = window.Telegram?.WebApp?.initData;
  if (fromTelegram) return fromTelegram;
  // ... fallback, returns "" — never throws
}
```
**Content** (RESEARCH "localStorage onboarding flag"): `hasSeenOnboarding(): boolean` / `markOnboardingSeen(): void`, key `"zerkalo.onboarding_completed"`, wrapped in `try/catch` (private-mode safe). FlowRoot initial step = `hasSeenOnboarding() ? "selection" : "onboarding"` (ONB-04 / D-11).

---

### `lib/telegram.ts` (MODIFY — util, SDK seam)

**Analog:** `lib/telegram.ts` (self) — extend, don't replace. Keep `getInitData` / `telegramReady`.

**Existing seam pattern to extend** (telegram.ts lines 6-14, 53-57 — typed `TelegramWebApp` interface + optional-chained no-op methods):
```ts
interface TelegramWebApp {
  initData?: string;
  ready?: () => void;
  expand?: () => void;
}
export function telegramReady(): void {
  const webApp = window.Telegram?.WebApp;
  webApp?.ready?.();   // optional-chained: no-op outside Telegram
  webApp?.expand?.();
}
```
**What to add** (RESEARCH "Extend telegram.ts", UI-04): widen the `TelegramWebApp` interface with `colorScheme`, `themeParams`, `safeAreaInset`, `contentSafeAreaInset`, `HapticFeedback`; export `getColorScheme()` (default `"dark"`), `getThemeParams()`, `getSafeAreaInsets()` / `getContentSafeAreaInsets()` (default zeros), and a `haptic = { impact, notify, selection }` object — every method optional-chained exactly like `telegramReady` so it no-ops outside Telegram. Used by RitualScreen (`haptic.notify("success")`) and FlipCard (`haptic.impact("light")`).

> **Test analog:** `lib/telegram.test.ts` exists — extend it for the new readers (mock `window.Telegram.WebApp`, assert defaults when absent).

---

### `flow/steps.ts` (NEW — util, step union + transition helpers)

**Analog:** `stores/session.ts` `AuthStatus` union (lines 9-13) — the string-literal-union-as-state-token pattern. Mirror for the `Step` union and any `next/back` helper. (Per TS coding-style: prefer string-literal unions over `enum`.)

---

### `flow/FlowRoot.tsx` (NEW — component, AnimatePresence root switch) · PARTIAL analog

**Analog:** `App.tsx` (lines 6-12 — the root composition) + `AuthGate.tsx` (lines 52-108 — the status-driven render switch). The `AnimatePresence` mechanism itself is new (RESEARCH Pattern 1, verbatim target).

**Root composition to replace** (App.tsx — FlowRoot becomes the child of AuthGate):
```tsx
function App() {
  return (
    <AuthGate>
      <CatalogScreen />   {/* Phase 3: replace with <FlowRoot /> */}
    </AuthGate>
  );
}
```

**Render-switch pattern to mirror** (AuthGate.tsx lines 52-95 — pick the view by a state token; AuthGate switches on `status`, FlowRoot switches on `step`):
```tsx
if (status === "error") { return (/* ... */); }
if (status === "authenticated") { return (/* ... */); }
// idle | authenticating — neutral loader
return (/* ... */);
```

**The new primitive** (RESEARCH Pattern 1 — copy structure exactly): wrap once in `<MotionConfig reducedMotion="never">` (D-10) → `<LazyMotion features={domAnimation}>` (D-01 bundle) → `<AnimatePresence mode="wait" initial={false}>` with a single `m.div key={step}` direct child; map `step` → screen component via a `SCREENS` record. Enter/exit tokens from UI-SPEC: `initial {opacity:0,y:8}` → `animate {opacity:1,y:0}` → `exit {opacity:0,y:-8}`, `duration 0.28`, `ease [0.16,1,0.3,1]`. **Pitfall 4:** `key`/`exit` on the immediate child only.

---

### `components/onboarding/OnboardingFlow.tsx` (NEW — component, slide index)

**Analog:** `components/CatalogScreen.tsx` (screen-level `<main>` + sections) + `components/DeckCarousel.tsx` (lines 12-30 — the index-map-over-array pattern) + `components/AuthGate.tsx` (lines 76-91 — the centered hero layout).

**Centered-hero layout to mirror** (AuthGate.tsx — onboarding slides are vertically-centered Display title + Body subtitle):
```tsx
<main className="flex min-h-full flex-col items-center justify-center gap-6 px-6 text-center">
  <h1 className="text-3xl font-semibold tracking-wide" style={{ color: "var(--color-glow)" }}>…</h1>
  <p className="max-w-xs text-lg opacity-80">…</p>
</main>
```
> Note: use the **deck vars** (`--deck-accent`/`--deck-soft`) for new screens per UI-SPEC, not the legacy `--color-glow` (AuthGate predates the deck-var spine). The layout/spacing classes are the reusable part.

**Content** (UI-SPEC Screen 1 + RESEARCH onboarding copy): 3–4 slides, «Пропустить» on every slide (ONB-02 → `markOnboardingSeen()` + `goTo("selection")`), final CTA «Сделать первый расклад», ONB-03 reversed-cards explainer folded in. Slide nav = a local `index` + the same `AnimatePresence` primitive (RESEARCH "Don't Hand-Roll": no carousel lib). **Test analog:** `DeckCarousel.test.tsx` (forwards-selection + nothing-broken assertions) for the skip/advance interaction test.

---

### `components/CatalogScreen.tsx` (MODIFY — component, selection screen)

**Analog:** `components/CatalogScreen.tsx` (self) — extend in place. The screen scaffold, section rhythm, and Query wiring stay; add the question input + sticky CTA.

**Existing scaffold to extend** (CatalogScreen.tsx lines 23-39 — `useDeckTheme()` + one-field selectors + `gap-6 px-4 pb-24` main):
```tsx
export function CatalogScreen() {
  useDeckTheme();
  const topic = useSelection((s) => s.topic);
  const deckSlug = useSelection((s) => s.deckSlug);
  const setTopic = useSelection((s) => s.setTopic);
  const setDeck = useSelection((s) => s.setDeck);
  const decksQuery = useDecks();
  const spreadsQuery = useSpreads(topic, deckSlug);
  const recommendation = useRecommendation(topic, deckSlug);
  return (
    <main className="flex flex-1 flex-col gap-6 px-4 pb-24" style={{ background: "var(--deck-bg)" }}>
```
> `pb-24` (line 37) is the documented 96px sticky-CTA reserve (UI-SPEC Spacing exception) — the new «Начать расклад» CTA lands in that band.

**Section + loading/error pattern to mirror for new sections** (CatalogScreen.tsx lines 71-86 — the `isPending`/`isError`/data/empty four-way with in-character copy):
```tsx
<section aria-label="Колоды" className="flex flex-col gap-3">
  <h2 className="px-1 text-sm uppercase tracking-wide opacity-70">Колоды</h2>
  {decksQuery.isPending ? (<p className="px-1 opacity-70">Колода раскладывается…</p>)
    : decksQuery.isError ? (<p className="px-1 opacity-70">Колода сейчас молчит. Загляни чуть позже.</p>)
    : decksQuery.data && decksQuery.data.length > 0 ? (<DeckCarousel … />)
    : (<p className="px-1 opacity-60">Колоды ещё в тишине.</p>)}
</section>
```

**Wire the existing `SpreadCard.onSelect`** (currently unwired — SpreadCard.tsx line 6 already accepts `onSelect`): pass `setSpread` (HOME-06). Reuse `TopicChip`/`DeckCarousel`/`SpreadCard`/recommendation banner verbatim.

**What to add** (UI-SPEC Screen 2): question `<textarea>` (placeholder «О чём спросим колоду?», glass surface, accent focus ring, render as React text node — V5 no `dangerouslySetInnerHTML`); sticky «Начать расклад» (HOME-07 gate via `canStart`, padded above `--tg-safe-area-inset-bottom`, sized vs `viewportStableHeight` — UI-04 keyboard pitfall); on tap → `createReading(...)` → `goTo("ritual")`. **Test analog:** `CatalogScreen.test.tsx` (full — `renderWithClient` + `vi.stubGlobal("fetch")`).

---

### `components/ritual/RitualScreen.tsx` (NEW — component, timed beats)

**Analog:** `components/AuthGate.tsx` (lines 30-50 — the `useEffect` lifecycle with cleanup + StrictMode guard; the timed beat-advance mirrors this effect discipline) + `CatalogScreen.tsx` for the screen shell.

**Effect-with-cleanup pattern to mirror** (AuthGate.tsx lines 30-50 — guard, `active` flag, return cleanup):
```tsx
const startedRef = useRef(false);
useEffect(() => {
  if (startedRef.current) return;
  startedRef.current = true;
  let active = true;
  // … kick off async work …
  return () => { active = false; };
}, [/* stable deps */]);
```
**Content** (RESEARCH Pattern 4 / UI-SPEC Screen 3): `setInterval` advancing 3 beats over ~3s, nested `AnimatePresence` keyed on beat index for the crossfade, dimming overlay (`opacity`), `<Particles/>` underneath. On final beat → `haptic.notify("success")` then `goTo("reveal")`; tap-to-skip enabled only when `beat >= 1` (D-08). Preload reveal/result art here (D-10 / Pitfall 6). Every timer/effect cleaned up like AuthGate.

---

### `components/ritual/Particles.tsx` (NEW — component, looping motion field)

**Analog:** `components/DeckCard.tsx` (lines 1, 32-48 — `motion` element tinted with `var(--deck-accent)`).

**Deck-tinted motion element to mirror** (DeckCard.tsx — `motion.*` + accent var via `color-mix`):
```tsx
import { motion } from "motion/react";   // inside FlowRoot, prefer m.* from "motion/react-m"
<motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
  style={{ /* … color-mix(in srgb, var(--deck-accent) …) … */ }} />
```
**Content** (RESEARCH Pattern 5 / UI-SPEC): a fixed ~12–16 count of `m.div` dots, each looping a small `y` drift + `opacity` pulse with a per-particle delay; tint with `var(--deck-accent)`. **Compositor-only** — `transform`/`opacity` only, never `top`/`left`/`box-shadow` (D-10 / Pitfall 2). Cap count rather than adding a reduced-motion path (D-10 forbids the downgrade).

---

### `components/reveal/FlipCard.tsx` (NEW — component, tap → rotateY)

**Analog:** `components/DeckCard.tsx` (lines 25-68 — `motion.button` + `CardArt` + deck-var glass) + `components/CardArtFallback.tsx` (full — the card face).

**Card-face source to reuse verbatim** (CardArtFallback.tsx lines 21-35 — `CardArt` is the face for reveal & result, no art seeded so the fallback always renders; 120×192, radius 12):
```tsx
export function CardArt({ src, alt, glyph }: CardArtProps) {
  if (src) { return (<img … width={120} height={192} loading="lazy" … />); }
  const sigil = glyph ?? (alt.trim().charAt(0).toUpperCase() || "✦");
  return (<div role="img" aria-label={alt} style={{ width:120, height:192, borderRadius:12, … }}>…</div>);
}
```
**`motion.button` + accent-glow shape to mirror** (DeckCard.tsx lines 32-48 — selection glow via `boxShadow` is the *static* edge-glow; the *animated* edge-glow must be `opacity` of an accent layer, not shadow blur — Pitfall 2).

**The new flip primitive** (RESEARCH Pattern 2 — copy structure): `perspective:1000` on parent; `m.div animate={{ rotateY: flipped ? 180 : 0 }}` spring `stiffness 260, damping 26`; both faces absolutely stacked with `backfaceVisibility:"hidden"` (face at `rotateY(180deg)`); `onAnimationComplete={() => flipped && haptic.impact("light")}` (per-flip haptic, UI-03). Frame 120×192 matches `CardArt`/UI-SPEC.

---

### `components/reveal/RevealScreen.tsx` (NEW — component, per-card flip orchestration)

**Analog:** `components/CatalogScreen.tsx` (screen shell + `.map` over a collection, lines 95-105) + `components/DeckCarousel.tsx` (lines 12-30 — map-with-stable-key).

**Map-with-stable-key to mirror** (DeckCarousel.tsx — one child per item, keyed by a stable id, never index):
```tsx
{decks.map((deck) => (
  <div role="listitem" key={deck.slug}>
    <DeckCard deck={deck} active={deck.slug === selectedSlug} onSelect={onSelect} />
  </div>
))}
```
**Content** (UI-SPEC Screen 4 / RESEARCH Pattern 3): one `<FlipCard/>` per spread position; tap-to-flip individually; after the **first** flip render «Раскрыть все» which staggers the rest via `delayChildren: stagger(0.12)` (RESEARCH Pattern 3, `stagger` from `motion/react`). Short in-character phrase precedes each interpretation; «Прочитать значение» reveals the interpretation block with staggered text (`opacity`+`y`). Key flip children on a stable card id (Pitfall: never index — `AnimatePresence` exit detection). **Test analog:** `CatalogScreen.test.tsx` interaction style (first flip → «Раскрыть все» appears → tapping flips remaining).

---

### `components/result/ResultScreen.tsx` (NEW — component, renders MockReading)

**Analog:** `components/CatalogScreen.tsx` (screen shell + sections) + `components/SpreadCard.tsx` (lines 11-46 — the glass info-card with title/meta/positions) + `components/AuthGate.tsx` (header block).

**Glass info-card to mirror for each result card** (SpreadCard.tsx lines 14-44 — title (Heading) + accent badge + meta rows on a deck-var glass surface):
```tsx
<button … className="flex w-full flex-col gap-2 rounded-xl border p-4 text-left …"
  style={{ borderColor: recommended ? "var(--deck-accent)" : "color-mix(in srgb, var(--deck-soft) 18%, transparent)",
           background: "color-mix(in srgb, var(--deck-bg) 70%, transparent)" }}>
  <span className="flex items-center justify-between gap-2">
    <span className="text-base font-semibold" style={{ color: "var(--deck-soft)" }}>{spread.title}</span>
    {recommended && (<span className="rounded-full px-2 py-0.5 text-xs" style={{ … var(--deck-accent) … }}>рекомендуем</span>)}
  </span>
  <span className="text-xs opacity-70">{spread.card_count} карты</span>
  {positions && <span className="text-xs opacity-60">{positions}</span>}
</button>
```
**Recommendation-banner / meta style to mirror** (CatalogScreen.tsx lines 54-68 — eyebrow Label + Display value + body, for the meta row тема/колода/дата and summary panel):
```tsx
<p className="text-xs uppercase tracking-wide opacity-70">Колода советует</p>
<p className="text-lg font-semibold" style={{ color: "var(--deck-soft)" }}>{…title}</p>
<p className="mt-1 text-sm opacity-80">{…reason}</p>
```
**Content** (UI-SPEC Screen 5 / READ-09): header «Расклад готов»; meta row (вопрос/тема/колода/расклад/дата); one glass card per `MockReading.cards[]` (name/position/orientation/shortMeaning/interpretation/deckAccent italic); summary panel (связка/главный фактор/внимание/совет/завершающая фраза) revealed as staggered blocks (the "final gather"); sticky actions — «Ещё расклад» accent + wired → `startReadingAgain()` (D-04), «Сохранить карточку» + «История» visible-but-disabled «скоро» (D-12). Render `MockReading.question` as text node (V5). **Test analog:** `CatalogScreen.test.tsx` (renders all fields; «Ещё расклад» wired; save/история stubbed).

---

## No Analog Found

| File | Role | Data Flow | Reason / Source instead |
|------|------|-----------|-------------------------|
| `reading/types.ts` | type | transform | No behavioral analog (it's a pure data contract). Shape style copies `api/spreads.ts` interfaces; field set is the verbatim target in RESEARCH "The Phase-4 seam — mock reading type" (mirrors future READ-05/06). |

**Partial-only (new primitive, structure from RESEARCH not codebase):**
- `flow/FlowRoot.tsx` — the `MotionConfig + LazyMotion + AnimatePresence` switch has no codebase precedent (Phase 3 introduces `AnimatePresence`). Composition/render-switch borrowed from `App.tsx` + `AuthGate.tsx`; the motion primitive is RESEARCH Pattern 1 (verbatim, with locked UI-SPEC duration/easing tokens).
- The flip / stagger / ritual-timeline / particle *mechanics* (RESEARCH Patterns 2–5) are new to the codebase; their **styling/theming/copy** still come from the analogs above (DeckCard, CardArtFallback, deck vars, AuthGate voice).

---

## Metadata

**Analog search scope:** `frontend/src/{stores,components,theme,lib,api,hooks,test}/`
**Files scanned:** 19 read in full (selection.ts, session.ts, telegram.ts, telegram.test.ts, App.tsx, CatalogScreen.tsx, CatalogScreen.test.tsx, DeckCard.tsx, DeckCarousel.tsx, DeckCarousel.test.tsx, SpreadCard.tsx, TopicChip.tsx, CardArtFallback.tsx, useDeckTheme.ts, decks.ts, useDecks.ts, spreads.ts, client.ts, AuthGate.tsx, index.css, deckThemes.css)
**Pattern extraction date:** 2026-06-11
**Stack confirmed:** React 19 + TS + Vite + Tailwind v4 (`@theme` in index.css) + Zustand 5 + TanStack Query 5 + `motion` (imported `motion/react`) + Vitest + RTL (jsdom). No new dependency this phase.
