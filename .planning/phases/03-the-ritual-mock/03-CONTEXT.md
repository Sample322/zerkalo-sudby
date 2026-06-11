# Phase 3: The Ritual (mock) - Context

**Gathered:** 2026-06-11
**Status:** Ready for planning

<domain>
## Phase Boundary

The complete **front-end reading journey against a MOCK reading** — no LLM, no `POST /api/readings`, no backend card draw (all of that is Phase 4). This phase locks the UX and animation contract end-to-end so Phase 4 can wire the real generation underneath without reworking screens.

**In scope:**
- Onboarding 3–4 screens, skippable, shown once (ONB-01..04) — incl. plain-language reversed-cards explainer (ONB-03)
- Main selection flow extending the existing `CatalogScreen`: free-text question (HOME-01/02), 7 topics (HOME-03), spread recommendation (HOME-04), deck carousel (HOME-05), spread pick (HOME-06), gated «Начать расклад» (HOME-07)
- Ritual prep screen (READ-07): "слышит вопрос / перемешиваются / рядом", dimming, particles, completion haptic
- Staggered flip-reveal of cards (READ-08) against the mock result
- Result screen (READ-09) populated from a mock reading
- Premium-dark mobile-first UI (UI-01), micro-animations via `motion` (UI-03), Telegram theme + safe-area adaptation (UI-04), brand-voice clean (SAFE-06)

**Out of scope (later phases):** real generation / safety classifier / CSPRNG draw / generation_logs (Phase 4), limits & paywall & Telegram Stars (Phase 4+), history & profile & settings persistence (Phase 5), admin/analytics.

</domain>

<decisions>
## Implementation Decisions

### Navigation & Flow
- **D-01 (governing NFR):** User's explicit, repeated bar — *transitions and animations must feel very smooth, no jank, no abrupt "just appearing", while loading fast.* Treat perceived smoothness/performance as a first-class acceptance criterion for this phase, not polish.
- **D-02:** Screen navigation = **state-machine in the existing Zustand store** (a `step` field) with `motion` `AnimatePresence` for enter/exit transitions. No react-router (browser history causes jank inside a Mini App). *(Claude discretion under D-01 — user delegated the mechanism, set the smoothness constraint.)*
- **D-03:** "Back" = **in-app back buttons** per screen (not the Telegram native BackButton).
- **D-04:** Result-screen **«ещё расклад» returns to the selection screen with question + topic preserved** (user can change deck/spread and re-run). Not a full reset, not a same-config re-ritual.

### Mock Reading Data
- **D-05:** The mock result is **schema-faithful to the FUTURE real contract** (READ-05 per-card fields + READ-06 summary fields). Define the reading TypeScript type now to match what Phase 4's `POST /api/readings` will return, so Phase 4 swaps **only the data source** — the reveal/result UI stays untouched. Keep the "build mock reading" call behind a single function (the future fetch seam).
- **D-06:** Mock card pool = **a small bundled client-side fixture** (card names + rough meanings). No `GET /api/cards` endpoint in this phase — keeps Phase 3 frontend-only.
- **D-07:** Reversals simulated client-side via a **local toggle**: on → ~70% upright / 30% reversed (plain `Math.random` fine for the mock; CSPRNG is a Phase-4 backend concern), off → all upright. Mirrors future READ-02. Persisting the setting via `PATCH /api/me/settings` is Phase 5 — local state only here.

### Animation Contract (the artifact this phase locks)
- **D-08:** Ritual prep (READ-07) = **auto-advancing timeline ~3s** across three beats («слышит вопрос → перемешиваются → рядом») with crossfade, dimming + particles (transform/opacity only), **completion haptic**; **tap-to-skip after the first beat**.
- **D-09:** Card reveal (READ-08) = **tap-to-flip each card one by one**; after the first flip an **«раскрыть все»** control staggers-flips the rest. Short in-character phrase precedes each card's interpretation.
- **D-10:** **Full animations always — NO `prefers-reduced-motion` downgrade path.** Locked engineering consequence (to satisfy D-01 without a degraded mode): animations MUST be **compositor-only** (`transform`/`opacity`), hold a **60fps budget**, lazy-load heavy `motion` features, and **preload next-step art**. Vestibular/reduced-motion accessibility is a known, accepted tradeoff — see Deferred.

### Stub Boundaries
- **D-11:** `onboarding_completed` persists to **localStorage** this phase; the `PATCH /api/me/settings` path is Phase 5. ONB-04 satisfied locally (not re-shown after completion within the client).
- **D-12:** Result-screen actions **«сохранить карточку» and «история» are present but stubbed** (visible, disabled or a "скоро" affordance) — History is Phase 5, share-card is later. **«ещё расклад» is fully wired** (D-04).
- **D-13:** **Empty question is valid → general reading** (HOME-02). Question rules: 10–500 chars with a gentle "уточни" hint when too short (HOME-01); empty is explicitly allowed (no hint).
- **D-14 [informational]:** Limits, paywall, real draw, safety classifier, analytics events — **NOT in this phase**. The mock flow never calls a generation endpoint. (Negative scope-fence — honored by absence; plan-checker confirmed no plan introduces these. Not separately plan-trackable.)

### Claude's Discretion
- Exact onboarding screen copy/order (3–4 screens incl. the ONB-03 reversed-cards explainer in plain, non-scary language — *delay / inner resistance / hidden tension*, never "bad/плохо"); swipe vs button nav, constrained by D-01.
- Particle style/density, exact beat durations inside the ~3s ritual, easing curves — constrained by D-10 (compositor-only) and per-deck theme vars.
- Result-screen layout composition (premium-dark glass, large cards, sticky bottom CTA) per UI-01.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project source-of-truth
- `.planning/REFERENCE-TZ.md` — original full TZ. Relevant: §9.x screen flows (incl. §9.8 empty/error states in product voice), §10.1–10.2 premium-dark UI + the micro-animation spec (shuffle, card "breathing", flip, edge-glow, staggered text reveal, haptic, final gather), §21.2 the 6-deck palettes (already implemented in `deckThemes.css`).
- `.planning/REQUIREMENTS.md` — Phase 3 IDs: ONB-01..04, HOME-01..07, READ-07/08/09, SAFE-06, UI-01/03/04. **READ-05/06 define the future reading shape the mock must mirror (D-05).**
- `.planning/ROADMAP.md` → "Phase 3: The Ritual (mock)" — goal + 5 success criteria.
- `CLAUDE.md` — stack (React 19 + Vite 7 + Tailwind v4 + Zustand + TanStack Query + `motion` from `motion/react`), brand-voice ban list (no "AI/нейросеть/модель/сгенерировано ИИ"), mobile-first 360–430px, sticky bottom CTA.

### Forward contract (anticipate, don't build)
- `.planning/ROADMAP.md` → "Phase 4" success criteria + `.planning/REQUIREMENTS.md` READ-01..06 — the real `POST /api/readings` contract. The mock reading type (D-05) must be shaped so Phase 4 is a drop-in source swap.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/stores/selection.ts` — Zustand `{topic, deckSlug, spreadSlug}` + setters. Extend with `question`, `reversalsEnabled`, and the `step` state-machine field (D-02). Keep server state out (client-only by design).
- `frontend/src/components/CatalogScreen.tsx` — the selection surface; becomes the "main flow" screen. Add free-text question input (HOME-01/02) + «Начать расклад» gating (HOME-07). Already wires topic chips + deck carousel + spread list + recommendation banner.
- `frontend/src/theme/useDeckTheme.ts` + `frontend/src/theme/deckThemes.css` — per-deck palette (UI-02) flows into ritual/reveal/result automatically via `data-deck` on `<html>`.
- `frontend/src/components/CardArtFallback.tsx` — card faces in reveal + result (no deck art seeded → fallback always exercised).
- `frontend/src/lib/telegram.ts` — Telegram WebApp SDK seam. Extend for theme params + **safe-area insets via SDK insets, NOT CSS `env()`** (UI-04) + `HapticFeedback` (READ-07 completion, UI-03).
- `frontend/src/components/{DeckCard,DeckCarousel,SpreadCard,TopicChip}.tsx` — reuse in the selection step.
- `motion` (installed) — `AnimatePresence` for screen transitions (D-02), flip/stagger/particles (D-08/09). Import from `motion/react`.

### Established Patterns
- Client state in Zustand, server state in TanStack Query, never mirror. The mock reading is client-only ephemeral state → Zustand/local, NOT Query.
- Brand-voice gate (SAFE-06): zero "AI/нейросеть/модель/сгенерировано ИИ" strings — applies to all new ritual/onboarding/result copy.
- `AuthGate` wraps the authenticated surface; the whole Phase 3 flow lives inside it.

### Integration Points
- `frontend/src/App.tsx` currently renders `<AuthGate><CatalogScreen/></AuthGate>` — Phase 3 replaces `CatalogScreen` with a flow-container (state-machine root) that mounts onboarding/selection/ritual/reveal/result by `step`.
- Phase 4 seam: the «Начать расклад» handler builds the mock reading now; later it calls `POST /api/readings`. Keep that boundary a single function (D-05).

</code_context>

<specifics>
## Specific Ideas

- User's explicit, repeated emphasis: *"все действия и анимации очень плавные, без рывков, без просто появления, и при этом быстро грузится."* This is the felt-quality bar — perceived smoothness is a first-class acceptance criterion (D-01), not finishing polish.

</specifics>

<deferred>
## Deferred Ideas

- `prefers-reduced-motion` / vestibular accessibility fallback — user chose full animations always (D-10); accessible reduced-motion mode deferred (revisit post-MVP or if accessibility scope is added).
- Real reading generation, safety classifier, CSPRNG card draw, `generation_logs` — Phase 4.
- History list / detail / soft-delete, profile & settings persistence (`PATCH /api/me`) — Phase 5.
- Share-card / real «сохранить карточку» export — later phase.
- Limits, weekly reset, paywall, Telegram Stars — Phase 4+ (LIMIT/PAY).
- Telegram native BackButton integration — user chose in-app back buttons; native BackButton could be revisited later but not now.

</deferred>

---

*Phase: 03-the-ritual-mock*
*Context gathered: 2026-06-11*
