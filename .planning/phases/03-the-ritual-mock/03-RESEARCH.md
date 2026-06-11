# Phase 3: The Ritual (mock) - Research

**Researched:** 2026-06-11
**Domain:** Telegram Mini App front-end — `motion` (ex-framer-motion) animation choreography, Zustand step-machine navigation, Telegram WebApp SDK (theme / safe-area / haptics), schema-faithful mock data contract
**Confidence:** HIGH (every external claim verified against official docs or the npm registry; the few `[ASSUMED]` items are copy/UX choices delegated to Claude's discretion)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01 (governing NFR):** transitions and animations must feel very smooth, no jank, no abrupt "just appearing", while loading fast. Perceived smoothness/performance is a **first-class acceptance criterion**, not polish.
- **D-02:** Screen navigation = state-machine in the existing Zustand store (a `step` field) with `motion` `AnimatePresence` for enter/exit. **No react-router.**
- **D-03:** "Back" = in-app back buttons per screen (not the Telegram native BackButton).
- **D-04:** Result-screen «ещё расклад» returns to the selection screen **with question + topic preserved** (deck/spread re-selectable). Not a full reset, not a same-config re-ritual.
- **D-05:** Mock result is **schema-faithful to the FUTURE real contract** (READ-05 per-card + READ-06 summary). Define the reading TS type now; keep the "build mock reading" call behind **one function** (the future fetch seam) so Phase 4 swaps only the data source.
- **D-06:** Mock card pool = a small **bundled client-side fixture**. No `GET /api/cards` this phase.
- **D-07:** Reversals = local toggle: on → ~70% upright / 30% reversed (`Math.random` fine for mock), off → all upright.
- **D-08:** Ritual prep (READ-07) = **auto-advancing ~3s timeline** across three beats («слышит вопрос → перемешиваются → рядом») with crossfade, dimming + particles (transform/opacity only), **completion haptic**; **tap-to-skip after the first beat**.
- **D-09:** Card reveal (READ-08) = **tap-to-flip each card one by one**; after the first flip an **«раскрыть все»** control staggers the rest. Short in-character phrase precedes each card's interpretation.
- **D-10:** **Full animations always — NO `prefers-reduced-motion` downgrade path.** Engineering consequence: animations MUST be **compositor-only** (`transform`/`opacity`), hold a **60fps budget**, lazy-load heavy `motion` features, and **preload next-step art**.
- **D-11:** `onboarding_completed` persists to **localStorage** this phase (`PATCH /api/me/settings` is Phase 5).
- **D-12:** Result-screen «сохранить карточку» and «история» are **present but stubbed**; «ещё расклад» is **fully wired** (D-04).
- **D-13:** Empty question valid → general reading (HOME-02). 10–500 chars with a gentle "уточни" hint when too short (HOME-01); empty explicitly allowed (no hint).
- **D-14:** Limits, paywall, real draw, safety classifier, analytics — **NOT in this phase**. The mock flow never calls a generation endpoint.

### Claude's Discretion

- Exact onboarding screen copy/order (3–4 screens incl. the ONB-03 reversed-cards explainer in plain, non-scary language — *delay / inner resistance / hidden tension*, never "bad/плохо"); swipe vs button nav — constrained by D-01.
- Particle style/density, exact beat durations inside the ~3s ritual, easing curves — constrained by D-10 (compositor-only) and per-deck theme vars.
- Result-screen layout composition (premium-dark glass, large cards, sticky bottom CTA) per UI-01.

### Deferred Ideas (OUT OF SCOPE)

- `prefers-reduced-motion` / vestibular accessibility fallback — user chose full animations always (D-10).
- Real reading generation, safety classifier, CSPRNG card draw, `generation_logs` — Phase 4.
- History list / detail / soft-delete, profile & settings persistence (`PATCH /api/me`) — Phase 5.
- Share-card / real «сохранить карточку» export — later phase.
- Limits, weekly reset, paywall, Telegram Stars — Phase 4+.
- Telegram native BackButton integration — user chose in-app back buttons.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ONB-01 | Onboarding 3–4 screens (welcome, choose atmosphere, "подсказка не приговор", first-reading CTA) | §9.1 TZ copy verbatim below; lightweight step-index pattern (no carousel lib) — "Onboarding Pattern" |
| ONB-02 | User can skip onboarding | Skip button sets `onboardingDone` + jumps to selection step — "Onboarding Pattern" |
| ONB-03 | Reversed-cards explained in plain language (delay / inner resistance / hidden tension, never "bad") | Copy guidance in "Onboarding Pattern"; SAFE-06 voice gate |
| ONB-04 | `onboarding_completed` persisted, not re-shown | localStorage gate (D-11) — "localStorage onboarding flag" |
| HOME-01 | Free-text question 10–500 chars; gentle hint when too short | Controlled input + derived validation — "Question Input UX" |
| HOME-02 | General reading allowed without a question (empty valid) | Empty bypasses the hint (D-13) — "Question Input UX" |
| HOME-03 | Pick topic from 7 | Already built (`TopicChip` + `TOPICS` in CatalogScreen) — reuse |
| HOME-04 | App recommends a spread by topic (with reason); user can change | Already built (`useRecommendation` banner) — reuse |
| HOME-05 | Deck carousel (title, atmosphere, for-which-questions, preview, tone) | Already built (`DeckCarousel`/`DeckCard`) — reuse |
| HOME-06 | Pick spread (cards with count) | Already built (`SpreadCard`) — wire `onSelect` to `setSpread` |
| HOME-07 | «Начать расклад» enabled when topic+deck+spread chosen (or defaults); else gentle hint | Derived gate in selection store — "Selection gating & the Phase-4 seam" |
| READ-07 | Ritual prep: «слышит вопрос / перемешиваются / рядом», dimming, particles, completion haptic | "Ritual prep timeline" + Telegram `HapticFeedback.notificationOccurred('success')` |
| READ-08 | Staggered flip-reveal; short phrase before interpretation; «Открыть карту»/«раскрыть все» | "Card flip (3D)" + "Staggered reveal" + haptic per flip |
| READ-09 | Result screen: question/topic/deck/spread/date, card cards, summary, action buttons | "Result screen" + the mock reading type |
| SAFE-06 | No "AI/нейросеть/модель/сгенерировано ИИ" in UI | "Brand-voice leakage" pitfall + ban-list check |
| UI-01 | Premium-dark UI (glass, glow, gradients, large cards); mobile-first 360–430px; sticky bottom CTA | Existing token system + "Sticky bottom CTA + safe area" |
| UI-03 | Micro-animations (shuffle, breathing, flip, edge-glow, staggered text, haptic, final gather) via `motion` | All "Architecture Patterns" |
| UI-04 | Telegram dark/light theme + safe-area via **SDK insets, not CSS env()** | "Telegram WebApp surface" — `themeParams`/`colorScheme` + `--tg-safe-area-inset-*` |
</phase_requirements>

## Summary

Phase 3 is a **front-end-only choreography phase**: ~80% of the data plumbing (auth, deck/spread catalog, per-deck theming, card-art fallback, the selection store) already exists and is reused verbatim. The genuinely new work is (1) a **Zustand `step` state-machine** wrapping the existing `CatalogScreen` plus four new screens (onboarding, ritual, reveal, result), (2) a **`motion` animation contract** — `AnimatePresence` screen transitions, a 3D card flip, a staggered reveal, an auto-advancing ritual timeline with particles — engineered to a **60fps compositor-only budget** because the user made smoothness a hard acceptance criterion (D-01/D-10), and (3) a **schema-faithful mock reading type + single fetch-seam function** so Phase 4's `POST /api/readings` is a drop-in (D-05).

The stack is settled and current: `motion@12.40.0` (peer-supports React 19, package renamed from `framer-motion`, imports from `motion/react`), Zustand 5, Tailwind v4, raw `window.Telegram.WebApp`. **No new runtime dependency is required.** The one optional package considered — `@telegram-apps/sdk-react@3.3.9` — is legitimate but unnecessary: the project already owns a `telegram.ts` seam and only needs to extend it with theme params, safe-area insets, and haptics, all of which are three thin reads off `window.Telegram.WebApp`.

The single largest engineering risk is **animation jank**. Three findings drive the plan: motion **does not auto-downgrade** animations (so D-10 is satisfiable, but should be *locked* with `<MotionConfig reducedMotion="never">`); `AnimatePresence mode="wait"` serializes screen swaps (no stacking, but a true crossfade needs `position:absolute` on the wrapper); and **Telegram's iOS keyboard overlaps bottom-fixed inputs** — a real, documented quirk that affects the question field and the sticky «Начать расклад» CTA.

**Primary recommendation:** Build a `useFlow` Zustand slice (`step` + history) driving a single `<AnimatePresence mode="wait">` switch; implement all motion via **`transform`/`opacity` only**, wrapped once in `<MotionConfig reducedMotion="never">` and `<LazyMotion features={domAnimation}>` with `m.*` components to keep first load light; define `MockReading`/`MockReadingCard` types mirroring READ-05/06 and expose a single `createReading(params): Promise<MockReading>` seam; extend `telegram.ts` with `getThemeParams()`, `getSafeAreaInsets()`, and `haptic` helpers. Treat the question field and sticky CTA against `viewportStableHeight` + `--tg-safe-area-inset-bottom`, never `100vh`/`env()`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Screen navigation / step machine | Client (Zustand) | — | D-02: ephemeral UI state, no URL/history; lives in the existing selection store |
| Screen enter/exit transitions | Client (`motion` AnimatePresence) | — | D-02; pure presentation |
| Mock reading construction | Client (fixture + `createReading` seam) | — | D-05/D-06: no backend this phase; the seam is the Phase-4 boundary |
| Reversals simulation | Client (`Math.random`) | — | D-07: mock only; real CSPRNG draw is a Phase-4 *backend* concern |
| Onboarding-seen flag | Client (localStorage) | — | D-11: `PATCH /api/me/settings` deferred to Phase 5 |
| Per-deck theming | Client (CSS vars via `data-deck`) | — | Already built (UI-02); flows into all new screens for free |
| Theme (light/dark) + safe-area + haptics | Telegram WebApp SDK (via `telegram.ts`) | Client (CSS vars) | UI-04: insets/theme are platform-owned; `telegram.ts` is the seam |
| Deck / spread / recommendation catalog | API (TanStack Query) | — | Already built (Phase 2); this phase only consumes it, never mirrors it |
| **Real reading generation, card draw, limits, safety** | **API (Phase 4) — NOT this phase** | — | D-14: the mock flow never calls a generation endpoint |

## Standard Stack

No new runtime dependency is needed. Everything below is already in `frontend/package.json` (verified).

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `motion` (ex-`framer-motion`) | `12.40.0` (installed `^12`) | AnimatePresence screen transitions, 3D flip, stagger, particles, ritual timeline | The animation engine the whole phase is built on; peer-supports React 19; compositor-friendly props. `[VERIFIED: npm registry]` |
| `zustand` | `5.x` (installed `^5`) | The `step` state-machine + `question`/`reversalsEnabled` (extends existing `selection.ts`) | D-02; client UI state already lives here |
| `react` / `react-dom` | `19.2.x` | UI runtime | Existing |
| `tailwindcss` + `@tailwindcss/vite` | `4.3.x` | Premium-dark UI tokens, per-deck CSS vars, glass/glow (UI-01) | Existing; `@theme` + CSS vars already wired |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| raw `window.Telegram.WebApp` | — (CDN-injected) | Theme params, safe-area insets, HapticFeedback (UI-04, READ-07/08) | Extend the existing `frontend/src/lib/telegram.ts`; **no install** |
| `@tanstack/react-query` | `5.x` (installed) | Deck/spread/recommendation catalog (already wired) | Consume only — the mock reading is **client state, NOT Query** |
| `vitest` + `@testing-library/react` | installed | Unit/component tests for store logic, validation, the reading-fixture builder | Existing test infra (jsdom, colocated `*.test.tsx`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| raw `window.Telegram.WebApp` | `@telegram-apps/sdk-react@3.3.9` | A maintained typed wrapper with reactive signals + `bindCssVars()`. **Rejected:** the project already owns a `telegram.ts` seam; adding a wrapper duplicates the boundary, pulls a ~3.3.x dep (42K wk downloads, last publish Dec 2025 — fine, but unnecessary), and CLAUDE.md/STACK already mark it "Optional." Three thin reads beat a new dependency. |
| Zustand `step` machine | `react-router` | D-02 explicitly forbids it — browser history causes jank inside a Mini App. |
| `motion` particles | `tsparticles` / canvas confetti libs | Heavy bundle, often animates non-compositor props → violates D-10. A handful of `m.div`s on `transform`/`opacity` is lighter and on-budget. |
| `motion` flip | CSS-only `@keyframes` flip | Viable and cheap, but the reveal needs orchestrated stagger + per-card state + haptic callbacks → `motion` is already in-bundle and gives `onAnimationComplete`. |

**Installation:**
```bash
# Nothing to install — all dependencies already present.
# (If LazyMotion is adopted, no new package: `m` ships inside `motion` at motion/react-m.)
```

**Version verification (run 2026-06-11):**
```
npm view motion version          -> 12.40.0   (published 2026-05-21)
npm view motion peerDependencies -> react ^18 || ^19, react-dom ^18 || ^19   (React 19 OK)
npm view motion exports          -> "./react", "./react-m", "./react-client" all present
npm view @telegram-apps/sdk-react version -> 3.3.9 (published 2025-12-05)  [optional, not adopted]
```

## Package Legitimacy Audit

> No package is being **installed** this phase. `motion`, `zustand`, etc. are already in the lockfile. `@telegram-apps/sdk-react` was *evaluated and rejected*. Audited for completeness.

| Package | Registry | Age / Publish | Downloads | Source Repo | slopcheck (npm) | Disposition |
|---------|----------|---------------|-----------|-------------|-----------------|-------------|
| `motion` | npm | latest 12.40.0, 2026-05-21 | ~13.0M/wk | github.com/motiondivision/motion | `[OK]` | Already installed — Approved |
| `@telegram-apps/sdk-react` | npm | 3.3.9, 2025-12-05 | ~42K/wk | github.com/telegram-mini-apps-dev/telegram-apps | `[OK]` | Legitimate but **NOT adopted** (raw SDK seam preferred) |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

> **Ecosystem-mismatch note (important for the planner/reviewer):** running `slopcheck install motion` and `slopcheck install @telegram-apps/sdk-react` resolves against **PyPI** by default and produces misleading results — `motion` maps to an *unrelated* Python package (`motion 0.2.0` + `kinesis-python`), and `@telegram-apps/sdk-react` is reported `[SLOP]` because it does not exist on PyPI. Both are **npm** packages. Re-running with the correct ecosystem (`slopcheck scan --pkg npm <name>`) returns `[OK]` for both. This is the documented cross-ecosystem confusion vector; npm-registry verification is authoritative here.

## Architecture Patterns

### System Architecture Diagram

Data + control flow through the Phase-3 front end (everything inside `AuthGate`):

```
                         ┌─────────────────────────────────────────────┐
   Telegram WebView ───► │  window.Telegram.WebApp                      │
   (initData, theme,     │  (initData • themeParams • colorScheme •     │
    insets, haptics)     │   safeAreaInset • HapticFeedback)            │
                         └───────────────┬─────────────────────────────┘
                                         │  read-only, via the seam
                                         ▼
                         ┌─────────────────────────────────────────────┐
                         │  frontend/src/lib/telegram.ts  (EXTEND)      │
                         │  getInitData() [exists] • getThemeParams()   │
                         │  getSafeAreaInsets() • haptic.{impact,notify}│
                         └───────────────┬─────────────────────────────┘
                                         │
   ┌─────────────────────────────┐      │      ┌──────────────────────────────┐
   │ TanStack Query (Phase 2)    │      │      │ Zustand selection store       │
   │ decks • spreads • recommend │      │      │ (EXTEND): topic • deckSlug •  │
   │  (server state — consume)   │      │      │ spreadSlug • question •       │
   └──────────────┬──────────────┘      │      │ reversalsEnabled • step •     │
                  │                      │      │ history[]  (client UI state)  │
                  │ feeds selection      │      └───────────────┬───────────────┘
                  ▼                      ▼                      │ drives `step`
   ┌────────────────────────────────────────────────────────────▼──────────────┐
   │  FlowRoot  =  <MotionConfig reducedMotion="never">                          │
   │                 <LazyMotion features={domAnimation}>                        │
   │                   <AnimatePresence mode="wait">                             │
   │                                                                             │
   │   step="onboarding" → step="selection" → step="ritual" → step="reveal" →    │
   │                            step="result"                                    │
   │   (each is the keyed direct child; enter/exit on opacity+transform)         │
   └───────────────────────────────────────┬─────────────────────────────────────┘
                                            │ on «Начать расклад» (HOME-07)
                                            ▼
                         ┌─────────────────────────────────────────────┐
                         │  createReading(params): Promise<MockReading> │  ◄── THE PHASE-4 SEAM (D-05)
                         │  Phase 3: build from bundled fixture + D-07   │
                         │           reversal toggle (Math.random)       │
                         │  Phase 4: POST /api/readings (same return type)│
                         └───────────────┬─────────────────────────────┘
                                         ▼
                              MockReading  →  reveal screen (flip + stagger)
                                           →  result screen (cards + summary)
```

File-to-responsibility mapping is in the table below — **not** in the diagram.

### Recommended Project Structure
```
frontend/src/
├── flow/
│   ├── FlowRoot.tsx              # MotionConfig + LazyMotion + AnimatePresence switch on `step`
│   └── steps.ts                  # Step union type + transition helpers (next/back)
├── stores/
│   └── selection.ts              # EXTEND: + question, reversalsEnabled, step, history, gates
├── reading/
│   ├── types.ts                  # MockReading / MockReadingCard (mirror READ-05/06)
│   ├── createReading.ts          # THE SEAM — fixture build now, POST later (D-05)
│   └── cardPool.fixture.ts       # bundled card names + rough meanings (D-06)
├── components/
│   ├── onboarding/OnboardingFlow.tsx   # 3–4 screens, skippable (ONB-01..04)
│   ├── CatalogScreen.tsx               # EXTEND: + question input + «Начать расклад» gate
│   ├── ritual/RitualScreen.tsx         # ~3s timeline, particles, haptic (READ-07/D-08)
│   ├── ritual/Particles.tsx            # compositor-only m.div field
│   ├── reveal/RevealScreen.tsx         # tap-to-flip + «раскрыть все» stagger (READ-08/D-09)
│   ├── reveal/FlipCard.tsx             # 3D rotateY flip (one card)
│   └── result/ResultScreen.tsx         # READ-09; «ещё расклад» wired, others stubbed (D-12)
├── lib/
│   └── telegram.ts               # EXTEND: theme params, safe-area insets, haptics
└── hooks/
    └── useOnboardingSeen.ts      # localStorage flag (ONB-04 / D-11)
```

### Pattern 1: Zustand step state-machine + AnimatePresence
**What:** A single `step` field drives a `<AnimatePresence mode="wait">` whose direct child is keyed by `step`. Changing `step` exits the old screen, then enters the new one — no react-router, no layout stacking.
**When to use:** All Phase-3 navigation (D-02). `history[]` in the store backs the in-app back buttons (D-03) and lets «ещё расклад» preserve question+topic (D-04 = pop back to `selection` without clearing those fields).
**Example:**
```tsx
// Source: motion.dev/docs/react-animate-presence (mode="wait", keyed direct child)
// FlowRoot.tsx
import { AnimatePresence, MotionConfig, LazyMotion, domAnimation } from "motion/react";
import * as m from "motion/react-m";
import { useSelection } from "../stores/selection";

const SCREENS = {
  onboarding: OnboardingFlow,
  selection: CatalogScreen,
  ritual: RitualScreen,
  reveal: RevealScreen,
  result: ResultScreen,
} as const;

export function FlowRoot() {
  const step = useSelection((s) => s.step);
  const Screen = SCREENS[step];
  return (
    <MotionConfig reducedMotion="never">           {/* D-10: lock full animations */}
      <LazyMotion features={domAnimation}>          {/* D-01: ship ~4.6kb, not ~34kb */}
        <AnimatePresence mode="wait" initial={false}>
          <m.div
            key={step}                              {/* key MUST be on the direct child */}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          >
            <Screen />
          </m.div>
        </AnimatePresence>
      </LazyMotion>
    </MotionConfig>
  );
}
```
> Note: `mode="wait"` **serializes** the swap (the exiting screen finishes before the new one mounts), so there is no overlap and `position:absolute` is **not required**. If you want a true overlapping *crossfade* between two screens, give the animating wrapper `position:absolute; inset:0` so both occupy the same box during the overlap.

### Pattern 2: 3D card flip (compositor-only)
**What:** A two-faced card that rotates on `rotateY` between 0° (back/рубашка) and 180° (face). Both faces are absolutely stacked; the off-side is hidden via `backfaceVisibility`. `rotateY` is a transform → GPU-composited → on-budget for D-10.
**When to use:** READ-08 reveal, one instance per card; tap flips it, `onAnimationComplete` fires the per-flip haptic and reveals the short phrase (D-09).
**Example:**
```tsx
// Source: motion.dev (transform animation) + CSS 3D transforms (desandro card-flip)
// FlipCard.tsx
import * as m from "motion/react-m";
import { haptic } from "../../lib/telegram";

export function FlipCard({ card, flipped, onFlip }: FlipCardProps) {
  return (
    <div style={{ perspective: 1000 }}>                          {/* depth on the parent */}
      <m.div
        onClick={onFlip}
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 26 }}
        onAnimationComplete={() => flipped && haptic.impact("light")}  // UI-03 per-flip
        style={{ transformStyle: "preserve-3d", position: "relative", width: 120, height: 192 }}
      >
        <div style={{ position: "absolute", inset: 0, backfaceVisibility: "hidden" }}>
          {/* card back / рубашка */}
        </div>
        <div style={{ position: "absolute", inset: 0, backfaceVisibility: "hidden",
                      transform: "rotateY(180deg)" }}>
          {/* card face — CardArt fallback (no art seeded) */}
        </div>
      </m.div>
    </div>
  );
}
```

### Pattern 3: Staggered reveal of remaining cards
**What:** «раскрыть все» (shown after the first flip, D-09) flips the rest with a stagger so they cascade rather than pop simultaneously. In `motion` v12, `delayChildren: stagger(...)` on a parent variant is the current idiom (the older standalone `staggerChildren` still works).
**When to use:** READ-08, the "open all" action.
**Example:**
```tsx
// Source: motion.dev/docs/react-transitions (stagger() inside delayChildren)
import { stagger } from "motion/react";
const container = {
  open: { transition: { delayChildren: stagger(0.12) } },  // cascade, not a pop
};
const cardVar = {
  closed: { rotateY: 0 },
  open:   { rotateY: 180, transition: { type: "spring", stiffness: 260, damping: 26 } },
};
// <m.div variants={container} animate="open"> {cards.map(c => <m.div variants={cardVar}/>)} </m.div>
```

### Pattern 4: Ritual prep — auto-advancing ~3s timeline (D-08)
**What:** Three beats («слышит вопрос → перемешиваются → рядом»), each ~1s, auto-advanced by a timer; crossfade between beat texts via a nested `AnimatePresence` keyed on the beat index; a dimming overlay + a compositor-only particle field run underneath; on completion fire `haptic.notify("success")` and transition `step → reveal`. Tap-to-skip becomes active after beat 1.
**When to use:** READ-07.
**Example:**
```tsx
// Beat timer (effect): advance every BEAT_MS, fire completion haptic, then go to reveal.
useEffect(() => {
  const id = setInterval(() => setBeat((b) => Math.min(b + 1, BEATS.length - 1)), BEAT_MS);
  return () => clearInterval(id);
}, []);
useEffect(() => {
  if (beat === BEATS.length - 1) {
    haptic.notify("success");                 // READ-07 completion haptic
    const t = setTimeout(() => goTo("reveal"), BEAT_MS);
    return () => clearTimeout(t);
  }
}, [beat]);
// Skip: enabled only when beat >= 1 (D-08). Particles = handful of m.div animating y/opacity.
```

### Pattern 5: Particles on compositor-only props (D-10)
**What:** A fixed-count (e.g. 12–20) field of `m.div` dots, each looping a small `y` drift + `opacity` pulse with a per-particle delay. **Only `transform`/`opacity`** — never `top`/`left`/`box-shadow` size. Tinted with `var(--deck-accent)` so it inherits the per-deck theme automatically.
**Anti-pattern it avoids:** canvas/particle libs that animate layout or paint-heavy props and blow the 60fps budget.

### Anti-Patterns to Avoid
- **Animating layout/paint props** (`width`, `height`, `top`, `left`, `margin`, `box-shadow` blur, `background-position`) — they trigger layout/paint each frame → jank. Use `transform`/`opacity` only (D-10; matches web/performance rule).
- **Array index as `AnimatePresence` key** — breaks exit detection. Key on `step` / stable card id.
- **Using the full `motion` component inside `LazyMotion`** — defeats the bundle saving. Use `m.*` from `motion/react-m`; optionally set `<LazyMotion strict>` to *throw* if a full `motion` sneaks in.
- **`100vh` / CSS `env(safe-area-inset-*)` for layout** — UI-04 mandates Telegram SDK insets; `env()` is unreliable in the Telegram WebView and `100vh` ignores the keyboard. Use `viewportStableHeight` + `--tg-safe-area-inset-*`.
- **Mirroring the mock reading into TanStack Query** — it is ephemeral client state; Query is for server state only (ARCHITECTURE rule). Keep it in Zustand/local.
- **Mounting the result/reveal before art preloads** — causes pop-in (violates D-01). Preload next-step card art during the ritual beats.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Screen enter/exit + exit-before-enter | A manual mount/unmount + `setTimeout` crossfade | `AnimatePresence mode="wait"` | Handles exit timing, interruption, and re-entry correctly; manual versions drop frames on rapid taps |
| Stagger timing across N cards | Hand-computed per-card `setTimeout` delays | `delayChildren: stagger()` / variants | Cancels/юresyncs correctly on interruption; avoids drift |
| 3D flip math | Manual `requestAnimationFrame` rotation | `m.div animate={{ rotateY }}` + spring | Velocity-aware spring, GPU transform, `onAnimationComplete` callback for haptics |
| Reduced-motion handling | A custom media-query listener that disables animations | `<MotionConfig reducedMotion="never">` | D-10 wants the opposite of the usual default; one prop locks it explicitly and documents intent |
| Safe-area / theme / haptics | Re-deriving insets from `window.innerHeight`, guessing theme from `prefers-color-scheme` | `window.Telegram.WebApp` `safeAreaInset` / `themeParams` / `HapticFeedback` (via `telegram.ts`) | Platform-accurate (UI-04); guessing breaks on notched devices and ignores Telegram's theme |
| Carousel for onboarding | A swipe/carousel library | A `step` index + `AnimatePresence` (the same primitive you already use) | 3–4 static screens don't justify a dep; reuse the flow primitive |

**Key insight:** This phase's hard part is *timing correctness under interruption* (a user tapping fast through flips, skipping the ritual, hitting back). `motion`'s presence/variants/spring machinery solves exactly that; hand-rolled timers do not and are the classic source of the "abrupt pop-in" the user explicitly banned.

## Common Pitfalls

### Pitfall 1: Brand-voice leakage (SAFE-06)
**What goes wrong:** New onboarding/ritual/result copy slips in "AI", "нейросеть", "модель", "сгенерировано ИИ", or scary fatalistic phrasing in the reversed-cards explainer.
**Why it happens:** Lots of new user-facing strings land in this phase (onboarding ×4, ritual beats, short card phrases, result summary labels), and the mock summary text is authored by hand.
**How to avoid:** Centralize copy; run a ban-list check (`AI`, `нейросеть`, `модель`, `сгенерировано`, ИИ`) over all new strings as a test or grep gate. For ONB-03 use the allowed framing — *задержка / внутреннее сопротивление / скрытое напряжение*, never "плохо/приговор". Mirror the existing AuthGate voice ("Колода…").
**Warning signs:** Any English tech noun in a `.tsx` string literal; any imperative doom ("узнай правду, пока не поздно" — TZ §11.2 explicitly forbids).

### Pitfall 2: Animation jank from non-compositor props (D-01/D-10)
**What goes wrong:** Particles/glow/flip animate `box-shadow`, `width`, `top`, or `background-position`; frame rate drops below 60 on mid-range Android inside Telegram's WebView.
**Why it happens:** It's easy to reach for `box-shadow` for "glow" or `top` for "drift".
**How to avoid:** Restrict every animated value to `transform` (`x`/`y`/`scale`/`rotate`) and `opacity`. For edge-glow, animate `opacity` of a pre-rendered glow layer, not shadow blur. Verify with DevTools "Paint flashing"/FPS meter at 360px.
**Warning signs:** Any `animate={{ boxShadow / width / height / top / left ... }}`; visible stutter when particles + flip run together.

### Pitfall 3: Telegram iOS keyboard overlaps the question field & sticky CTA (UI-04)
**What goes wrong:** On iOS Telegram, opening the keyboard for the question input overlaps bottom-fixed elements; `position:fixed` bottom CTA gets hidden; `viewportHeight` shrinks but `env(safe-area-inset-bottom)` doesn't help.
**Why it happens:** The iOS client doesn't honor `interactive-widget` and behaves as `overlay-content`; documented across multiple Telegram-iOS issues.
**How to avoid:** Size scrollable regions to `viewportStableHeight` (stable, ignores keyboard), pad the sticky CTA with `var(--tg-safe-area-inset-bottom)`, and either move the question input above the fold or scroll it into view on focus. Listen to `viewportChanged`/`safeAreaChanged` to re-measure. Never rely on `100vh` or `env()`.
**Warning signs:** CTA invisible when typing on a real iPhone; content jumps when the keyboard opens/closes.

### Pitfall 4: AnimatePresence not animating exit
**What goes wrong:** Screens swap with no exit animation (hard cut).
**Why it happens:** The `key`/`exit` is on a nested element, not the **direct child** of `AnimatePresence`; or an index key changes identity.
**How to avoid:** Put `key={step}` and the `exit` prop on the immediate `m.div` child (Pattern 1). One keyed child at a time.
**Warning signs:** Enter animates but exit doesn't; React "unique key" warnings.

### Pitfall 5: LazyMotion bundle bloat / wrong import
**What goes wrong:** `LazyMotion` is added but you still `import { motion }` and use `motion.div`, so the full ~34kb feature bundle loads anyway.
**Why it happens:** Mixing `motion.*` and `m.*`.
**How to avoid:** Inside `LazyMotion`, use `m.*` from `motion/react-m`; pass `features={domAnimation}`; optionally `<LazyMotion strict>` to throw on a stray `motion.*`. (`domAnimation` ≈ the features this phase needs — opacity/transform/exit; `domMax` only if you later need layout/drag.)
**Warning signs:** First-load JS larger than expected; `strict` mode throwing.

### Pitfall 6: Pop-in of card art on the reveal/result screen (D-01)
**What goes wrong:** Cards visibly "appear" when the reveal mounts because art (or the CardArt fallback gradients) paint late.
**Why it happens:** No preload; the heavy screen mounts cold.
**How to avoid:** D-10's "preload next-step art" — warm the reveal/result during the ritual's ~3s. The current `CardArt` fallback is pure CSS/SVG (no network) so it's cheap, but still mount it behind the ritual so the first paint is already composited. If real art arrives later, preload the image URLs.
**Warning signs:** Flash/reflow at the ritual→reveal boundary.

## Code Examples

### Extend `telegram.ts` — theme, safe-area insets, haptics (UI-04, READ-07/08)
```ts
// Source: core.telegram.org/bots/webapps (themeParams, colorScheme, safeAreaInset, HapticFeedback)
// Extends the EXISTING frontend/src/lib/telegram.ts (getInitData/telegramReady stay).
interface TgInsets { top: number; bottom: number; left: number; right: number }

export function getColorScheme(): "light" | "dark" {
  return window.Telegram?.WebApp?.colorScheme ?? "dark";          // default dark = premium baseline
}
export function getThemeParams(): Record<string, string> {
  return window.Telegram?.WebApp?.themeParams ?? {};              // bg_color, text_color, ...
}
export function getSafeAreaInsets(): TgInsets {
  const wa = window.Telegram?.WebApp;
  return wa?.safeAreaInset ?? { top: 0, bottom: 0, left: 0, right: 0 };
}
export function getContentSafeAreaInsets(): TgInsets {
  const wa = window.Telegram?.WebApp;
  return wa?.contentSafeAreaInset ?? { top: 0, bottom: 0, left: 0, right: 0 };
}
export const haptic = {
  impact: (style: "light" | "medium" | "heavy" | "rigid" | "soft" = "light") =>
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(style),
  notify: (type: "error" | "success" | "warning") =>
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.(type),
  selection: () => window.Telegram?.WebApp?.HapticFeedback?.selectionChanged?.(),
};
```
> Telegram also exposes CSS vars `--tg-safe-area-inset-{top,bottom,left,right}` and `--tg-content-safe-area-inset-*`. UI-04 says use **SDK insets** — reading them via the JS object above (and applying as inline padding / a CSS var you set) satisfies that; the `--tg-*` CSS vars are a Telegram-provided convenience, distinct from the browser's `env()`.

### Extend `selection.ts` — step machine + question + gating (D-02/D-04/D-13/HOME-07)
```ts
// EXTENDS the existing selection store. Server lists stay in TanStack Query (unchanged).
type Step = "onboarding" | "selection" | "ritual" | "reveal" | "result";
interface FlowExt {
  question: string;
  reversalsEnabled: boolean;
  step: Step;
  history: Step[];
  setQuestion: (q: string) => void;
  toggleReversals: () => void;
  goTo: (s: Step) => void;
  back: () => void;
  startReadingAgain: () => void;          // D-04: back to selection, KEEP question+topic
}
// canStart (HOME-07): Boolean(topic && deckSlug && spreadSlug); else show a gentle hint.
// Question validity (HOME-01/02/D-13): empty -> valid (general); 1..9 chars -> show "уточни" hint;
//                                       10..500 -> valid; >500 -> clamp/hint.
// startReadingAgain: goTo("selection") without clearing question/topic; deck/spread re-selectable.
```

### The Phase-4 seam — mock reading type + builder (D-05/D-06/D-07)
```ts
// reading/types.ts — MIRRORS the future READ-05 (per card) + READ-06 (summary) so Phase 4
// swaps ONLY the data source. Field names anticipate the backend response_models.
export type Orientation = "upright" | "reversed";
export interface MockReadingCard {
  name: string;            // READ-05 название
  positionTitle: string;   // READ-05 позиция (from the chosen spread's positions)
  orientation: Orientation;// READ-05 положение (D-07 toggle)
  shortMeaning: string;    // READ-05 короткое значение
  interpretation: string;  // READ-05 глубокая интерпретация под вопрос
  deckAccent: string;      // READ-05 мистический акцент колоды (deck micro-text)
  shortPhrase: string;     // READ-08 short in-character phrase shown before interpretation
}
export interface MockReadingSummary {
  linkage: string;         // READ-06 связка карт
  mainFactor: string;      // READ-06 главный фактор
  attention: string;       // READ-06 на что обратить внимание
  softAdvice: string;      // READ-06 мягкий совет
  closingPhrase: string;   // READ-06 завершающая фраза в стиле колоды
}
export interface MockReading {
  question: string | null; // null => general reading (HOME-02)
  topic: string;
  deckSlug: string;
  spreadSlug: string;
  createdAt: string;       // ISO; result screen shows the date (READ-09)
  cards: MockReadingCard[];
  summary: MockReadingSummary;
}

// reading/createReading.ts — THE SEAM. Phase 3 builds locally; Phase 4 = POST /api/readings.
export async function createReading(params: {
  question: string | null; topic: string; deckSlug: string; spreadSlug: string;
  reversalsEnabled: boolean; positions: { title: string }[];
}): Promise<MockReading> {
  // 1. draw `positions.length` cards from cardPool.fixture (D-06)
  // 2. orientation per card: reversalsEnabled ? (Math.random() < 0.3 ? "reversed":"upright") : "upright"  (D-07)
  // 3. assemble per-card copy (deck-tinted, brand-safe) + summary; return MockReading
  // Phase 4 replaces the body with the API call; the RETURN TYPE is unchanged.
}
```

### localStorage onboarding flag (ONB-04 / D-11)
```ts
// hooks/useOnboardingSeen.ts — local only; PATCH /api/me/settings is Phase 5.
const KEY = "zerkalo.onboarding_completed";
export function hasSeenOnboarding(): boolean {
  try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
}
export function markOnboardingSeen(): void {
  try { localStorage.setItem(KEY, "1"); } catch { /* private mode — show once per session */ }
}
// FlowRoot initial step = hasSeenOnboarding() ? "selection" : "onboarding".
```

### Onboarding copy (TZ §9.1, verbatim — reuse, then add the ONB-03 reversed-cards screen)
```
Экран 1: «Добро пожаловать в Зеркало Судьбы»
         «Задай вопрос — и колода подсветит то, что важно увидеть сейчас.»
Экран 2: «Выбирай не только расклад, но и атмосферу»
         «Классика, Луна, Тени, Любовь, Путь или Лесной Оракул — каждая колода говорит своим языком.»
Экран 3: «Это не приговор, а подсказка»
         «Карты помогают посмотреть на ситуацию с другой стороны. Решение всегда остаётся за тобой.»
Экран 4: CTA «Сделать первый расклад»
// ONB-03 reversed-cards explainer (Claude's discretion where to place — likely folded into экран 3
// or a 4th screen): plain language — перевёрнутая карта = задержка / внутреннее сопротивление /
// скрытое напряжение, НЕ «плохо». Skip control present on every screen (ONB-02).
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `framer-motion` package | `motion` package, `import { motion } from "motion/react"` | rename (2024) | Install/import is `motion`; project already uses it correctly |
| `staggerChildren` on parent transition | `delayChildren: stagger(...)` (the `stagger()` function) | motion v11/12 | Use `stagger()`; `staggerChildren` still works but is legacy |
| Browser/CSS `env(safe-area-inset-*)` for notches | Telegram `safeAreaInset` / `contentSafeAreaInset` + `--tg-safe-area-inset-*` | Bot API 8.0 (late 2024) | UI-04 mandates the SDK path; `env()` is unreliable in the WebView |
| Importing `m` as a named export for LazyMotion | `import * as m from "motion/react-m"` (subpath export) | motion v12 | Registry confirms the `./react-m` export; use the subpath |

**Deprecated/outdated:**
- `framer-motion` package name — pulls a legacy/redirect; use `motion`.
- `prefers-reduced-motion` auto-handling assumptions — motion does **not** auto-reduce by default; D-10 wants full motion, so lock `<MotionConfig reducedMotion="never">` explicitly.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Onboarding screen copy/order from TZ §9.1 + a folded ONB-03 reversed-cards screen | Onboarding copy | LOW — copy is Claude's discretion (CONTEXT); reviewable, no structural impact |
| A2 | Beat count = 3 (×~1s) and particle count ~12–20 for the ~3s ritual | Pattern 4/5 | LOW — D-08 says ~3s / 3 beats; exact density is Claude's discretion under D-10 |
| A3 | `domAnimation` (not `domMax`) is the right LazyMotion feature set (no drag/layout needed) | Pitfall 5 | LOW — phase needs opacity/transform/exit/variants only; switch to `domMax` if a layout animation appears |
| A4 | Short in-character per-card phrases + summary copy authored from TZ §10.3 deck micro-texts | reading types | LOW — content, brand-voice gated by SAFE-06; reviewable |
| A5 | Spring tuning (stiffness ~260, damping ~26) for the flip feels right at 60fps | Pattern 2/3 | LOW — easing is Claude's discretion under D-10; tune during implementation |

**Note:** All *technical/API* claims (Telegram surface, motion API, versions, package legitimacy) are `[VERIFIED]`/`[CITED]`, not assumed. The assumptions above are exactly the copy/UX-tuning items CONTEXT already delegated to Claude's discretion — no new user confirmation is required beyond normal review.

## Open Questions

1. **Card pool fixture size & source (D-06)**
   - What we know: it's a small bundled client-side fixture (card names + rough meanings); no `/api/cards`.
   - What's unclear: how many cards (a curated ~22 Major Arcana? the full 78?) and whether to reuse the backend's seeded `cards.json` content for forward-fidelity.
   - Recommendation: a curated subset (e.g. the 22 Major Arcana) is enough to populate 3–4-card spreads with variety; if the Phase-1 `cards` seed JSON is readable, transcribe a slice for name/meaning fidelity. Plannable as a single fixture task.

2. **Particle performance budget on low-end Android inside Telegram**
   - What we know: compositor-only props hold 60fps in general.
   - What's unclear: exact safe particle count when flip + dimming + particles run together on a 2-year-old Android in the Telegram WebView.
   - Recommendation: start at ~12–16 particles, profile at 360px; cap count rather than adding reduced-motion (D-10 forbids the downgrade path). Visual-regression/perf check belongs in Validation Architecture.

## Environment Availability

> Phase 3 is a pure front-end/code phase. The only external runtime is the Telegram WebApp object, which is injected by the client at runtime (already abstracted behind `telegram.ts` with a dev fallback). No new tools/services are required for *implementation*.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `motion` | all animations | ✓ (lockfile) | 12.40.0 (`^12`) | — |
| `zustand` | step machine | ✓ (lockfile) | `^5` | — |
| Vitest + RTL | unit/component tests | ✓ (configured in `vite.config.ts`, jsdom) | vitest `^3.2.6` | — |
| Playwright | visual-regression at 360/390/430 + flip flow (web/testing rule) | ✗ (not installed) | — | Manual device check + Vitest component tests; add Playwright if visual-regression is in scope (Wave 0) |
| `window.Telegram.WebApp` | theme/insets/haptics (UI-04) | runtime-injected | — | Methods are optional-chained → no-op outside Telegram; dev fallback already in `telegram.ts` |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** Playwright (visual regression) — use Vitest component tests + manual device verification for MVP; install only if the plan commits to screenshot regression.

## Validation Architecture

> `workflow.nyquist_validation: true` (config). Included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Vitest `^3.2.6` + `@testing-library/react` `^16` (jsdom) |
| Config file | `frontend/vite.config.ts` (`test: { environment: "jsdom", include: ["src/**/*.test.{ts,tsx}"] }`) |
| Quick run command | `cd frontend && npx vitest run src/<path>.test.tsx` |
| Full suite command | `cd frontend && npm test` (alias for `vitest run`) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HOME-01/02/D-13 | empty→valid; 1–9→hint; 10–500→valid; >500→clamp/hint | unit | `npx vitest run src/stores/selection.test.ts` | ❌ Wave 0 (extend existing) |
| HOME-07 | `canStart` true only with topic+deck+spread | unit | `npx vitest run src/stores/selection.test.ts` | ❌ Wave 0 |
| D-02 | `goTo`/`back`/`history` step transitions | unit | `npx vitest run src/stores/selection.test.ts` | ❌ Wave 0 |
| D-04 | `startReadingAgain` returns to selection, preserves question+topic | unit | `npx vitest run src/stores/selection.test.ts` | ❌ Wave 0 |
| D-07 | reversals off→all upright; on→only upright/reversed values present | unit | `npx vitest run src/reading/createReading.test.ts` | ❌ Wave 0 |
| D-05 | `createReading` returns a fully-populated `MockReading` (all READ-05/06 fields) | unit | `npx vitest run src/reading/createReading.test.ts` | ❌ Wave 0 |
| ONB-04/D-11 | `hasSeenOnboarding` false→true after `markOnboardingSeen`; initial step gating | unit | `npx vitest run src/hooks/useOnboardingSeen.test.ts` | ❌ Wave 0 |
| SAFE-06 | no banned token (`AI`/`нейросеть`/`модель`/`сгенерировано`/`ИИ`) in new copy modules | unit (string gate) | `npx vitest run src/reading/copy.test.ts` | ❌ Wave 0 |
| ONB-02 | skip control advances past onboarding | component | `npx vitest run src/components/onboarding/OnboardingFlow.test.tsx` | ❌ Wave 0 |
| READ-08/D-09 | first flip reveals «раскрыть все»; tapping it flips remaining | component | `npx vitest run src/components/reveal/RevealScreen.test.tsx` | ❌ Wave 0 |
| READ-09/D-12 | result renders all reading fields; «ещё расклад» wired; save/история stubbed | component | `npx vitest run src/components/result/ResultScreen.test.tsx` | ❌ Wave 0 |
| UI-01/UI-04 (visual) | 360/390/430 layout, sticky CTA above safe-area, no overflow | visual (optional) | Playwright (if adopted) | ❌ Wave 0 (optional) |

> **Not unit-testable (acceptance = manual / D-01):** 60fps smoothness, haptic firing, particle feel, crossfade quality. These are the phase's *first-class* acceptance criteria (D-01) and need real-device verification (the `ui_safety_gate`/human-verify step), not automated assertions. Note them as manual acceptance checks in the plan; do not fake them with timing assertions.

### Sampling Rate
- **Per task commit:** the targeted quick-run command for the touched module.
- **Per wave merge:** `cd frontend && npm test` (full Vitest suite green).
- **Phase gate:** full suite green + manual device pass on the smoothness/haptic/visual criteria before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `src/stores/selection.test.ts` — extend for question validation, `canStart`, step transitions, `startReadingAgain` (HOME-01/02/07, D-02/04/13)
- [ ] `src/reading/createReading.test.ts` — reversal distribution + full-shape `MockReading` (D-05/06/07)
- [ ] `src/hooks/useOnboardingSeen.test.ts` — localStorage flag (ONB-04/D-11)
- [ ] `src/reading/copy.test.ts` — SAFE-06 ban-list gate over new copy modules
- [ ] `src/components/onboarding/OnboardingFlow.test.tsx`, `reveal/RevealScreen.test.tsx`, `result/ResultScreen.test.tsx` — interaction tests
- [ ] (Optional) Playwright install + config for visual regression at 360/390/430 — only if screenshot regression is in scope
- [ ] No framework install needed for unit/component tests — Vitest + RTL already configured

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high`. Phase 3 is front-end-only and introduces **no new auth, no new endpoint, no secret, no server input**. The relevant surface is narrow.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged) | Existing `AuthGate` + initData→JWT (Phase 1); this phase adds none |
| V3 Session Management | no | Existing session store; untouched |
| V4 Access Control | no | No new endpoints; no client-side gating of privileged actions |
| V5 Input Validation | **yes** | The free-text **question** (HOME-01) — length-validate (10–500, empty ok); render as **text only** (never `dangerouslySetInnerHTML`); it is stored in client state only this phase (no network) |
| V6 Cryptography | no | D-07 mock reversals use `Math.random` deliberately (not security-sensitive); real CSPRNG draw is Phase-4 **backend** (do not hand-roll crypto here) |
| V7 Error Handling / Logging | minor | Keep in-character soft messaging (matches AuthGate); no stacktrace/secret leak in any new copy |

### Known Threat Patterns for React + Telegram Mini App (this phase)
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| XSS via the user's question or any mock copy rendered as HTML | Tampering | Render strings as React text nodes only; no `dangerouslySetInnerHTML`; no `innerHTML` |
| localStorage tampering of `onboarding_completed` | Tampering | Cosmetic only (re-shows onboarding at worst); no trust placed in it — acceptable |
| Trusting client state as authority (e.g. treating the mock reading as real) | Spoofing/Elevation | None needed *here* (no backend), but the Phase-4 seam must keep draw/limits **backend-only** — already locked in STATE; do not let the mock leak forgeable expectations into the contract |
| Brand/safety copy leakage (fatalistic claims, "AI") | Info-disclosure / policy | SAFE-06 ban-list gate (also a test); SAFE-04/05 tone rules deferred to Phase-4 generation but the mock copy should already model the soft voice |

**Net:** no `high`-severity security work is triggered this phase. The one real control is **treat the question as untrusted text → length-validate + render as text** (V5). Everything crypto/auth/limit-related is correctly deferred to backend phases.

## Sources

### Primary (HIGH confidence)
- core.telegram.org/bots/webapps — `themeParams` fields, `colorScheme`, `safeAreaInset`/`contentSafeAreaInset` (+ `--tg-safe-area-inset-*` CSS vars, Bot API 8.0), `HapticFeedback.impactOccurred/notificationOccurred/selectionChanged` (exact arg values), `ready()`/`expand()`/`viewportStableHeight`
- motion.dev/docs/react-animate-presence — `mode` (`sync`/`wait`/`popLayout`), keyed direct child + `exit`, `initial={false}`, step-swap example
- motion.dev/docs/react-transitions — `delayChildren: stagger()`, variants inheritance, spring (`stiffness`/`damping`/`mass`) vs tween
- motion.dev/docs/react-lazy-motion — `LazyMotion` + `domAnimation`, `m` component (~4.6kb vs ~34kb), sync/async feature loading, `strict`
- motion.dev/docs/react-accessibility — `MotionConfig reducedMotion` `"user"`/`"always"`/`"never"`; `"never"` forces full animations (locks D-10)
- npm registry (2026-06-11) — `motion@12.40.0` (pub 2026-05-21, peer react ^18||^19, exports `./react` + `./react-m`), `@telegram-apps/sdk-react@3.3.9` (pub 2025-12-05)
- slopcheck 0.6.1 `scan --pkg npm` — `motion` `[OK]`, `@telegram-apps/sdk-react` `[OK]` (npm ecosystem)
- Existing codebase — `selection.ts`, `CatalogScreen.tsx`, `useDeckTheme.ts`/`deckThemes.css`, `CardArtFallback.tsx`, `telegram.ts`, `DeckCard.tsx` (motion usage), `vite.config.ts` (Vitest), `App.tsx`
- `.planning/REFERENCE-TZ.md` §9.1 (onboarding copy), §9.3–9.5 (ritual/reveal/result flows), §9.8 (empty/error voice), §10.2 (micro-animation list), §10.3 (deck micro-texts), §11.2 (no-fear monetization voice)

### Secondary (MEDIUM confidence)
- desandro 3dtransforms / dev.to flip guides — the `perspective` + `preserve-3d` + `backfaceVisibility` two-face flip structure (cross-checked against motion transform docs)
- docs.telegram-mini-apps.com/platform/viewport — `viewportHeight` vs `viewportStableHeight`, `bindCssVars()` (community SDK docs)

### Tertiary (LOW confidence — flagged)
- TelegramMessenger/Telegram-iOS issues #1296/#1377/#1410 — iOS keyboard overlaps bottom-fixed inputs; `env()` unreliable in WebView (community-reported, but consistent across multiple issues → treated as a real pitfall to design around)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions/exports verified on the npm registry; nothing new to install
- Architecture (step machine + AnimatePresence + flip/stagger + ritual): HIGH — patterns confirmed against current motion docs; one note (crossfade `position:absolute`) flagged as contextual
- Telegram surface (theme/insets/haptics): HIGH — exact property/method names from the official Bot API page
- Reduced-motion lock (D-10): HIGH — `reducedMotion="never"` confirmed as the explicit override
- Pitfalls: MEDIUM-HIGH — jank/voice/import pitfalls are HIGH; iOS-keyboard pitfall is community-sourced (LOW source) but cross-corroborated and low-risk to design around
- Copy/UX tuning (onboarding text, particle density, easing): assumptions, but explicitly Claude's-discretion per CONTEXT — no extra user confirmation needed

**Research date:** 2026-06-11
**Valid until:** ~2026-07-11 (stable stack; motion/Telegram move moderately — re-verify `motion` major and Bot API version if revisiting after a month)
