---
phase: 02-deck-spread-catalog
reviewed: 2026-06-11T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - backend/app/api/decks.py
  - backend/app/api/spreads.py
  - backend/app/main.py
  - backend/app/models/spread.py
  - backend/app/schemas/catalog.py
  - backend/app/seed/data/compatibility.json
  - backend/app/seed/loader.py
  - backend/app/services/catalog.py
  - frontend/src/App.tsx
  - frontend/src/api/decks.ts
  - frontend/src/api/spreads.ts
  - frontend/src/components/CardArtFallback.tsx
  - frontend/src/components/CatalogScreen.tsx
  - frontend/src/components/DeckCard.tsx
  - frontend/src/components/DeckCarousel.tsx
  - frontend/src/components/SpreadCard.tsx
  - frontend/src/components/TopicChip.tsx
  - frontend/src/hooks/useDecks.ts
  - frontend/src/hooks/useSpreads.ts
  - frontend/src/index.css
  - frontend/src/lib/queryClient.ts
  - frontend/src/main.tsx
  - frontend/src/stores/selection.ts
  - frontend/src/theme/deckThemes.css
  - frontend/src/theme/useDeckTheme.ts
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-06-11
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Reviewed the Deck & Spread Catalog slice: two auth-gated FastAPI routers, the catalog
service + seed loader, the catalog schemas, and the React/TanStack-Query/Zustand catalog
surface with per-deck theming.

The project's hard constraints hold up under adversarial inspection:

- **Auth gating** — both routers depend on `get_current_user`; the unauthenticated
  rejection is covered by `test_catalog_requires_auth`.
- **IP boundary (DECK-04)** — no schema in `schemas/catalog.py` exposes
  `cards.meaning_*` / `advice_*`; `prompt_modifier` is intentionally surfaced
  (DECK-02) and `prompt_instruction` appears only in TS types/tests, never rendered.
- **Injection** — all DB access uses SQLAlchemy 2.0 `select()` with bound params and
  PG `ARRAY.any()`; the frontend builds query strings with `URLSearchParams`.
- **State separation** — server lists stay in TanStack Query; Zustand holds only the
  ephemeral topic/deck/spread selection.
- **Brand voice** — the recommendation reason builder is RU-only, has a dedicated
  banned-word test, and no UI copy says "AI"/"нейросеть"/"модель".

No Critical issues were found. The findings below are correctness/robustness gaps: the
most material is a recommendation `reason` that can assert a deck-spread fit the data
does not support (WR-01), plus an unencoded slug at the deck-detail fetch boundary
(WR-02).

## Warnings

### WR-01: `recommend_spread` reason claims a deck↔spread fit even when the spread was chosen by topic-only / fallback

**File:** `backend/app/services/catalog.py:118-160` (reason at `145-160`, builder at `42-58`)

**Issue:** `recommend_spread` resolves the spread in three stages — (1) deck-compatible +
topic, (2) topic-only, (3) constant fallback `three_keys` — but unconditionally returns
`_build_reason(topic, deck)` using the **requested** deck regardless of which stage won.
When stages 2 or 3 fire, the returned spread is not in that deck's
`deck_spread_compatibility` set, yet the reason still says the deck "звучит в атмосфере …
этот расклад раскрывает её особенно бережно" / "ложится в этот расклад яснее всего" —
a user-facing claim the data contradicts.

This is exercised (and silently passes) in `test_spread_recommend_fallback`
(`topic=day&deck_slug=heart_oracle`): `heart_oracle` has no `day` topic and no
`day`-tagged compatible spread, so the topic-only branch returns `day_three_signs`, which
is **not** one of heart_oracle's recommended spreads (`between_us, three_keys,
thread_of_time, two_roads`). The reason nonetheless attributes the pick to heart_oracle.
The existing test only asserts the reason is non-empty and brand-safe, so it does not
catch the semantic mismatch.

**Fix:** Track which stage produced the spread and only pass the deck into the reason when
the deck-compatible branch actually selected it; otherwise build a deck-agnostic reason.

```python
async def recommend_spread(session, *, topic, deck_slug=None):
    deck: Deck | None = None
    spread: SpreadType | None = None
    matched_via_deck = False

    if deck_slug:
        deck = await get_deck(session, deck_slug)
        # ... deck-compatible query ...
        spread = (await session.execute(stmt)).scalars().first()
        matched_via_deck = spread is not None

    if spread is None:
        # ... topic-only query ...
        spread = (await session.execute(stmt)).scalars().first()

    if spread is None:
        spread = await _fallback_spread(session)

    # Only attribute the pick to the deck when the deck branch actually chose it.
    return spread, _build_reason(topic, deck if matched_via_deck else None)
```

Add a regression test asserting that for `topic=day, deck_slug=heart_oracle` the reason is
the deck-agnostic variant (does not contain the deck title).

### WR-02: `fetchDeck` interpolates `slug` into the URL path without encoding

**File:** `frontend/src/api/decks.ts:40-44`

**Issue:** `apiFetch(\`/api/decks/${slug}\`)` injects `slug` directly into the path. Unlike
`api/spreads.ts` (which correctly routes all user-influenced values through
`URLSearchParams`), this path segment is unescaped. A slug containing `/`, `?`, `#`, or
whitespace would change the request target (e.g. `a/b` resolves to `/api/decks/a/b`, a `?`
starts a query string, `#` truncates client-side). While Phase 2 slugs are server-issued
and `fetchDeck` is not yet wired into a screen, this is an exported public boundary that
later phases will call with values that may originate from routing/deep links. Harden it
now rather than relying on every future caller passing a clean slug.

**Fix:**

```typescript
export async function fetchDeck(slug: string): Promise<DeckDetail> {
  const res = await apiFetch(`/api/decks/${encodeURIComponent(slug)}`);
  if (!res.ok) throw new CatalogError(res.status);
  return (await res.json()) as DeckDetail;
}
```

### WR-03: `SpreadCard` hardcodes the plural "карты" — grammatically wrong for some card counts

**File:** `frontend/src/components/SpreadCard.tsx:42`

**Issue:** `{spread.card_count} карты` is rendered for every spread. Russian numeral
agreement requires "карта" for counts ending in 1 (but not 11), "карты" for 2–4 (not
12–14), and "карт" otherwise. Current seed spreads are all 3 or 4 cards, so the bug is
latent — but `card_count` is server-driven (REQUIREMENTS allow new spreads), and the
moment a 1-card "карта дня" or a 5+ card spread is seeded the UI will read "1 карты" /
"5 карты", which reads as broken to the 18–35 RU audience. This is a correctness gap in
user-facing copy, not a style preference.

**Fix:** Pluralize via a small helper (no library needed):

```typescript
function pluralizeCards(n: number): string {
  const mod100 = n % 100;
  const mod10 = n % 10;
  if (mod100 >= 11 && mod100 <= 14) return "карт";
  if (mod10 === 1) return "карта";
  if (mod10 >= 2 && mod10 <= 4) return "карты";
  return "карт";
}
// ...
<span className="text-xs opacity-70">{spread.card_count} {pluralizeCards(spread.card_count)}</span>
```

## Info

### IN-01: No DB-level unique constraint on `deck_spread_compatibility(deck_id, spread_type_id)`

**File:** `backend/app/models/deck.py:67-80`, relied on by `backend/app/seed/loader.py:99-157`

**Issue:** Idempotency of `deck_spread_compatibility` rests entirely on the loader's
app-level scoped delete-then-insert (`_upsert_compatibility`). There is no unique
constraint on `(deck_id, spread_type_id)`, so any other insert path (a future admin tool,
a partial/interrupted seed, a manual fix) can create duplicate compatibility rows.
`recommend_spread`'s ranking (`is_recommended DESC, compatibility_score DESC,
sort_order ASC`) would then surface non-deterministic ordering and the `selectinload`/join
could fan out duplicates. The comment in `loader.py` explicitly notes "no single-column
unique key"; a composite `UniqueConstraint` would make the integrity guarantee
structural rather than procedural.

**Fix:** Add `__table_args__ = (UniqueConstraint("deck_id", "spread_type_id",
name="uq_deck_spread"),)` to `DeckSpreadCompatibility` (with an accompanying migration),
then the loader can use `ON CONFLICT` instead of delete-then-insert.

### IN-02: `useRecommendation` uses a `topic as string` assertion instead of narrowing

**File:** `frontend/src/hooks/useSpreads.ts:19`

**Issue:** `queryFn: () => fetchRecommendation({ topic: topic as string, deckSlug })`
casts away the `string | null | undefined` type. It is safe at runtime only because
`enabled: Boolean(topic)` gates the query, but the cast couples the two lines: if the
`enabled` guard is ever loosened, TypeScript will not flag the now-possible
`undefined` topic. Per the project TS rules (avoid `as`, prefer narrowing), guard
explicitly.

**Fix:**

```typescript
export function useRecommendation(topic?: string | null, deckSlug?: string | null) {
  return useQuery({
    queryKey: ["recommend", { topic: topic ?? null, deckSlug: deckSlug ?? null }],
    queryFn: () => {
      if (!topic) throw new Error("recommendation requires a topic");
      return fetchRecommendation({ topic, deckSlug });
    },
    enabled: Boolean(topic),
  });
}
```

### IN-03: Glyph/sigil derivation is duplicated across `DeckCard` and `CardArtFallback`

**File:** `frontend/src/components/DeckCard.tsx:51` and `frontend/src/components/CardArtFallback.tsx:35`

**Issue:** `DeckCard` passes `glyph={deck.title.charAt(0)}` while `CardArt` independently
computes a fallback sigil `alt.trim().charAt(0).toUpperCase() || "✦"`. Two slightly
different "first character of a string" rules now exist for the same visual concern
(`DeckCard` does not uppercase or trim; `CardArt` does, plus the ✦ fallback). This is
minor DRY drift that will diverge further as more callers render `CardArt`. Note also
that `deck.title.charAt(0)` on an empty title yields `""`, which would make `CardArt`
fall through to its own `alt`-based sigil — harmless today but an implicit dependency
between the two components.

**Fix:** Drop the explicit `glyph` prop from `DeckCard` and let `CardArt` own the
single derivation rule (it already handles the empty/■ case), or extract a shared
`deckSigil(title: string)` helper used by both.

### IN-04: `useDecks` duplicates the global `staleTime` already set on the QueryClient

**File:** `frontend/src/hooks/useDecks.ts:11` vs `frontend/src/lib/queryClient.ts:8`

**Issue:** The shared `QueryClient` already sets `staleTime: 5 * 60_000` as the default for
all queries; `useDecks` re-declares the identical `staleTime: 5 * 60_000`. The redundant
literal invites drift (change one, forget the other) and obscures that decks follow the
default policy. `useSpreads`/`useRecommendation` correctly rely on the default and do not
restate it.

**Fix:** Remove the redundant `staleTime` from `useDecks` (inherit the client default), or
add a brief comment if the intent is to pin decks independently of the global value.

---

_Reviewed: 2026-06-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
