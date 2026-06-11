# 02-03 Summary — Catalog UI

**Plan:** 02-03 (Deck & Spread Catalog — UI slice)
**Status:** complete
**Branch:** gsd/phase-02-deck-spread-catalog
**Mode:** inline execution

## What shipped
- **API clients** (`api/decks.ts`, `api/spreads.ts`): typed `fetchDecks/fetchDeck/fetchSpreads/fetchRecommendation` through the Phase 1 `apiFetch` Bearer seam; `URLSearchParams` query building; typed `CatalogError` on non-2xx; no `any`.
- **TanStack Query hooks** (`hooks/useDecks.ts`, `hooks/useSpreads.ts`): `useDecks` (staleTime 5m), `useSpreads` (`placeholderData: keepPreviousData`), `useRecommendation` (gated `enabled: Boolean(topic)`). Server state stays in Query — never mirrored into Zustand.
- **Presentational components** (`TopicChip`, `DeckCard`, `DeckCarousel`, `SpreadCard`): mobile-first (360–430px), premium-dark glass, designed hover/focus/active, consume `var(--deck-*)`, `motion/react` tap/hover scale, `CardArtFallback` deck-preview tile (DECK-05). Ritual-framed copy, zero AI strings.
- **CatalogScreen** (`components/CatalogScreen.tsx`): composes 7 topic chips + deck carousel + spread list + recommendation banner; mounts `useDeckTheme()` (selecting a deck re-themes live, UI-02); loading/error/empty states in product voice. Wired into `App.tsx` behind `AuthGate` (replaced the Phase 1 SanctumStatus placeholder).

## Requirements
DECK-01, DECK-03, SPREAD-01, SPREAD-03, UI-02 — covered (with 02-01/02-02 completing DECK-02/04/05, SPREAD-02/04).

## Verification
- `npm run test -- --run` → **12 passed** (7 files): useDecks (fetch path → 6 decks), DeckCarousel (render 6 + click→slug, empty-safe), CatalogScreen (decks+spreads render, deck-select flips `data-deck` UI-02 end-to-end, topic→recommendation reason brand-voice-clean), + Plan 02 + Phase 1 tests.
- `npm run build` → green (tsc -b + vite build, 499 modules, 0 type errors, no `any`).

## User smoke (visual + live API)
With backend up (`docker compose up` → migrate → seed) + `npm run dev`: open authenticated app → 6 decks in carousel, selecting a deck visibly re-themes (UI-02), 7 spreads with positions, picking a topic shows a recommended spread + reason (SPREAD-03/04 end-to-end).
