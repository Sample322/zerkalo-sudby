# 02-02 Summary — Frontend Foundation

**Plan:** 02-02 (Deck & Spread Catalog — frontend foundation)
**Status:** complete
**Branch:** gsd/phase-02-deck-spread-catalog
**Mode:** inline execution

## What shipped
- **QueryClientProvider mounted** (`lib/queryClient.ts` + `main.tsx`) — first TanStack Query consumer; staleTime 5m, retry 1, no refetch-on-focus (catalog is near-static). Closes RESEARCH Pitfall 3.
- **Zustand selection store** (`stores/selection.ts`): `{topic, deckSlug, spreadSlug}` + setters; client-only, never mirrors server catalog (ARCHITECTURE boundary).
- **Per-deck theming UI-02** (`theme/deckThemes.css` + `theme/useDeckTheme.ts` + `index.css`): `useDeckTheme` writes `document.documentElement.dataset.deck`; 6 `[data-deck=...]` CSS-variable palettes (bg/accent/soft/deep) transcribed from decks.json/§21.2; body bg reads `var(--deck-*)` with a 400ms transition.
- **DECK-05 fallback** (`components/CardArtFallback.tsx`): null-art → atmospheric deck-tinted CSS/SVG placeholder (`role="img"`, inline SVG sigil in `var(--deck-accent)`, no `<img>`, no network); real `src` → lazy `<img>`.
- **RTL test harness** (`test/renderWithClient.tsx`) + RTL devDeps added.

## Requirements
UI-02, DECK-05 — covered.

## Verification
- `npm install` → 20 packages, 0 vulnerabilities.
- `npm run test -- --run` → **8 passed** (selection 2, useDeckTheme 1 [data-deck flip+clear], CardArtFallback 2 [null→role=img/no-img, src→img], + existing telegram 3).
- `npm run build` → green (tsc -b + vite build, 85 modules, dist emitted). Provider mount + theme + component type-check.
- No brand-voice strings in added copy.

## User smoke (visual)
Run the app, switch decks → background/accent visibly change (UI-02); a card with no art shows the atmospheric placeholder (DECK-05).
