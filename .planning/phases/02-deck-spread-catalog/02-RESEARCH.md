# Phase 2: Deck & Spread Catalog - Research

**Researched:** 2026-06-10
**Domain:** Read-only catalog slice — FastAPI async read APIs (decks/spreads/recommend) + React 19 catalog UI with per-deck runtime theming, served from Phase 1 seeded data
**Confidence:** HIGH (all stack/versions inherited from verified Phase 1 STACK.md; Phase 1 models/seed/auth read directly from disk; TZ API contract + palettes verified against source)

## Summary

Phase 2 is a **read-only vertical slice on top of a complete Phase 1 foundation**. Everything the catalog needs already exists: 17 SQLAlchemy models (incl. `Deck`, `DeckCard`, `DeckSpreadCompatibility`, `SpreadType`, `SpreadPosition`, `Card`, `Topic`), an idempotent seed for 7 topics / 6 decks / 7 spreads+23 positions / 78 cards / 11 prompt templates, a `get_current_user` Bearer dependency, a thin-router→service backend pattern, a Zustand session store, and an `apiFetch` Bearer seam. There is **no new stack** — Phase 2 reuses the locked versions from STACK.md (FastAPI 0.136 / SQLAlchemy 2 async / Pydantic v2 on the backend; React 19 / TanStack Query 5 / Zustand 5 / Tailwind v4 / motion 12 on the frontend). No external packages are installed in this phase.

The backend work is three thin routers (`/api/decks`, `/api/decks/{slug}`, `/api/spreads`, `/api/spreads/recommend`) delegating to a `CatalogService`, with Pydantic v2 `from_attributes` response schemas that eager-load relationships (`selectinload`) to avoid async lazy-load errors. All routes sit behind `get_current_user` (every app route is JWT-gated per Phase 1). The frontend work is TanStack Query hooks (server state only — never mirrored into Zustand), a small Zustand selection store `{topic, deckSlug, spreadSlug}`, a runtime per-deck theming mechanism (a `data-deck` attribute on the root + CSS-variable sets driven by each deck's seeded `visual_style.palette`), and three presentational components (`DeckCard` carousel, `SpreadCard`, `TopicChip`) plus a per-deck atmospheric CSS/SVG fallback for null card art (DECK-05).

**The single most important finding is a seed gap:** Phase 1's `loader.py` deliberately seeds only the rows the INFRA-03 counts depend on and **does NOT populate `deck_spread_compatibility`** (nor `deck_cards`). SPREAD-04 ("recommendation honors deck↔spread compatibility") therefore has **zero data to read** unless Phase 2 adds compatibility seed rows. The TZ defines the `deck_spread_compatibility` *schema* (§13.7) but provides **no explicit deck→spread mapping table** anywhere — so the compatibility rows must be **derived** (the obvious, defensible rule: a (deck, spread) pair is recommended when their seeded `recommended_topics` arrays overlap, with `compatibility_score` = size of the overlap). This must be a planned task, and `/api/spreads/recommend` must also have a **graceful fallback** for when no compatibility row exists.

**Primary recommendation:** Build a `CatalogService` (thick) behind thin routers, derive + seed `deck_spread_compatibility` from `recommended_topics` overlap (extending the existing idempotent loader), gate all routes with `get_current_user`, implement `/recommend` with a topic→compatibility lookup plus a deterministic fallback (highest topic-overlap spread, else `three_keys`), and theme the frontend at runtime via a `data-deck` root attribute mapping to CSS-variable palette sets sourced from each deck's `visual_style`.

## User Constraints (from Phase 1 / PROJECT.md)

> No `CONTEXT.md` exists for Phase 2 yet (the phase directory does not exist). These constraints are carried from PROJECT.md / CLAUDE.md and the Phase 1 locked decisions, and bind this phase. If `/gsd-discuss-phase` later writes a `CONTEXT.md`, its `## Decisions` supersede anything here.

### Locked Decisions (binding)
- **6 decks in MVP, all free** — `classic_arcana, moon_mirror, shadow_arcana, heart_oracle, path_deck, forest_oracle` (DECK-01). Count is fixed by the user.
- **7 spreads** — `three_keys, thread_of_time, between_us, two_roads, day_three_signs, resource_and_risk, what_is_in_shadow` (SPREAD-01), 3–4 cards each.
- **IP separation** — universal `cards` meaning is kept separate from deck `deck_cards` style layer (DECK-04). The catalog reads must respect this boundary: never merge base meaning into a deck-style response.
- **Brand voice** — no "AI / нейросеть / модель / сгенерировано ИИ" in any UI string, microcopy, or API-returned reason text (SAFE-06 spirit; applies to the `reason` field of `/recommend`).
- **Stack is locked** (STACK.md): React 19.2 + TS 5.7 + Vite 7 + Tailwind v4 + motion 12 + Zustand 5 + TanStack Query 5; FastAPI 0.136 + SQLAlchemy 2 async + Pydantic v2 + Redis 7. **No Redux, no `framer-motion` package name, no SQLAlchemy legacy `Query`, no Pydantic v1 idioms.**
- **Backend authority** — card draw / limits are backend-only (not relevant to this read-only phase, but the "thin router → thick service" pattern is the locked structure).
- **Mobile-first 360–430px**, premium-dark UI, per-deck theming from the 6 palettes in TZ §21.2 (UI-02).

### Claude's Discretion (recommend within these)
- **Redis caching of catalog responses** — STACK.md lists it as optional ("Cache deck/spread catalog … Admin toggle busts cache"). Admin is Phase 8; recommendation below is **keep it simple — TTL-only or skip entirely for MVP** (see Architecture Patterns).
- **Exact shape of the compatibility derivation rule** and the `reason` copy strings (within brand voice).
- **Component-internal structure** (how `DeckCard` carousel scrolls, fallback SVG art design) within the design-quality and mobile-first constraints.

### Deferred Ideas (OUT OF SCOPE for Phase 2)
- Reading generation, card draw, ritual UX (Phase 3/4).
- `deck_cards` **imagery population** — real art is a content task loaded via admin (Phase 8). Phase 2 only needs the *fallback* for when art is null; it does **not** need to seed image URLs. (Whether to seed empty/placeholder `deck_cards` rows at all is an open question — see below.)
- Admin CRUD / cache-bust-on-edit (Phase 8).
- Premium/seasonal decks, 5–7 card spreads (v2).

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DECK-01 | 6 free decks available | All 6 seeded in `decks.json` (verified on disk), all `access_type=free`, `is_active=true`, `is_mvp=true`. `/api/decks` lists them. |
| DECK-02 | Each deck has unique tone/atmosphere/`prompt_modifier`/visual theme | Verified: all 6 seeded decks have distinct `tone`, `atmosphere`, `prompt_modifier`, and `visual_style.palette` (the 6 TZ §21.2 palettes). Catalog response surfaces tone/atmosphere/visual_style; theming consumes `visual_style`. |
| DECK-03 | API: `GET /api/decks`, `GET /api/decks/{slug}` | New thin routers + `CatalogService`; Pydantic `from_attributes` schemas. |
| DECK-04 | Universal `cards` separate from `deck_cards`; 78 cards seeded | Verified: `Card` model holds meaning only (no imagery); `DeckCard` holds imagery only (no base meaning); 78 cards seeded. Catalog reads must not violate this. |
| DECK-05 | Card image/thumbnail/back slots with atmospheric CSS/SVG fallback when art null | `DeckCard.back_image_url` is nullable; `image_url`/`thumbnail_url` are NOT-NULL in the model but **no `deck_cards` rows are seeded** → frontend must render a per-deck styled fallback whenever a card-art URL is absent/empty. Concrete technique below. |
| SPREAD-01 | 7 spreads (3–4 cards) | All 7 seeded in `spreads.json` (verified), `card_count` ∈ {3,3,3,3,3,4,4}. |
| SPREAD-02 | Each spread has positions w/ title, description, `prompt_instruction` | Verified: 23 `spread_positions` seeded, each with `title`, `description`, `prompt_instruction`. Catalog response nests positions. |
| SPREAD-03 | API: `GET /api/spreads` (filter topic/deck), `/api/spreads/recommend` | New routers; query params `topic`, `deck_slug`; recommend returns `{recommended_spread, reason}`. |
| SPREAD-04 | Recommendation honors `deck_spread_compatibility` | **GAP: table not seeded.** Phase 2 must derive + seed compatibility rows, then read them in `/recommend` with a fallback. |
| UI-02 | Selecting a deck changes background/accent/microcopy/particles/tone (6 palettes) | Runtime theming via `data-deck` root attribute + CSS-var palette sets from `visual_style`. Concrete approach below. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| List/detail decks & spreads | API / Backend | Database | Catalog data is durable PG state; FastAPI owns the HTTP contract + serialization. |
| Topic→spread recommendation logic | API / Backend | Database | Business rule (compatibility lookup + fallback) belongs in a service, not the client. Client must not re-derive it. |
| Compatibility data | Database (seed) | — | Derived once at seed time from `recommended_topics`; read at request time. |
| Catalog caching (optional) | API / Backend (Redis) | — | If added, server-side TTL cache; the client's TanStack Query is a separate cache layer. |
| Server-state caching (decks/spreads) | Frontend (TanStack Query) | — | Client cache/SWR of GET responses; **not** duplicated into Zustand. |
| Selection state `{topic, deckSlug, spreadSlug}` | Frontend (Zustand) | — | Ephemeral client UI state — the user's in-progress choices. |
| Per-deck theming (bg/accent/microcopy/particles) | Browser / Client | — | Pure presentation: a root `data-deck` attribute swaps CSS-variable sets at runtime. |
| Null-art fallback rendering | Browser / Client | — | Visual concern; CSS/SVG placeholder styled per deck palette. |

## Standard Stack

**No new packages.** Phase 2 uses only what STACK.md pinned and Phase 1 installed. The relevant subset:

### Backend (already installed — verified in Phase 1)
| Library | Version (pinned) | Purpose in Phase 2 | Source |
|---------|------------------|--------------------|--------|
| FastAPI | 0.136.x | New `/api/decks`, `/api/spreads` routers | [CITED: STACK.md] |
| SQLAlchemy (async) | 2.0.x | `select()` + `selectinload()` reads | [CITED: STACK.md] |
| Pydantic | 2.10.x | Response schemas (`from_attributes=True`) | [CITED: STACK.md] |
| asyncpg | 0.30.x | PG driver (unchanged) | [CITED: STACK.md] |
| redis-py | 5.2.x | **Optional** catalog cache (discretion) | [CITED: STACK.md] |

### Frontend (already installed — verified in `frontend/package.json` on disk)
| Library | Version (installed) | Purpose in Phase 2 | Source |
|---------|---------------------|--------------------|--------|
| react / react-dom | 19.2.* | Catalog components | [VERIFIED: frontend/package.json] |
| @tanstack/react-query | ^5 | Server-state hooks for catalog GETs | [VERIFIED: frontend/package.json] |
| zustand | ^5 | Selection store `{topic, deckSlug, spreadSlug}` | [VERIFIED: frontend/package.json] |
| motion | ^12 | DeckCard hover/tap, carousel, staggered fade-in (TZ §21.4) | [VERIFIED: frontend/package.json] |
| tailwindcss + @tailwindcss/vite | 4.3.* | CSS-first theming via `@theme` + CSS vars | [VERIFIED: frontend/package.json] |
| vitest + jsdom | ^3.2 / ^25 | Frontend unit/component tests | [VERIFIED: frontend/package.json] |

> **Gap note:** `@tanstack/react-query` is a dependency but **no `QueryClientProvider` is mounted yet** — `App.tsx` and `main.tsx` do not wrap the tree in a provider (verified: `main.tsx` not shown but `App.tsx` only renders `<AuthGate>`). Phase 2 must add the `QueryClient` + `QueryClientProvider` setup (Wave 0 frontend task). This is the first phase to actually use TanStack Query.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `selectinload` eager loading | Lazy loading relationships | Lazy load on an async session raises `MissingGreenlet`/`StatementError` — **must** eager-load. Not a real alternative. |
| Derived compatibility from topic overlap | Hand-authored compatibility table | Hand-authoring is more precise but the TZ gives no source data and it's 6×7=42 rows of judgment calls; deriving from existing `recommended_topics` is defensible, deterministic, testable, and re-derivable. Recommend derive; allow a `custom_note` override per row. |
| TTL-only Redis cache | No cache | Catalog is tiny (6+7 rows) and rarely changes; for MVP a DB read per request is negligible. Recommend **skip cache for MVP** unless load testing shows a need (admin cache-bust is Phase 8 anyway). |

**Installation:** None. (No `## Package Legitimacy Audit` section follows — this phase installs zero external packages. slopcheck N/A.)

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────────┐
   Telegram WebView      │  React Mini App (Phase 2 additions)          │
   (authenticated,       │                                             │
    JWT in session)      │  TanStack Query hooks  ──fetch(Bearer)──┐   │
                         │   useDecks() useSpreads() useRecommend() │   │
                         │        │ (server cache)                  │   │
                         │        ▼                                 │   │
                         │  Components: DeckCard carousel,          │   │
                         │   SpreadCard, TopicChip                  │   │
                         │        │ onSelect                        │   │
                         │        ▼                                 │   │
                         │  Zustand selectionStore                  │   │
                         │   {topic, deckSlug, spreadSlug}          │   │
                         │        │ deckSlug                        │   │
                         │        ▼                                 │   │
                         │  ThemeController: set <html data-deck>   │   │
                         │   → CSS-var palette swap (bg/accent/...) │   │
                         └──────────────────────────────────────────┼──┘
                                            HTTPS Bearer JWT         │
                                                                     ▼
                         ┌─────────────────────────────────────────────┐
                         │  FastAPI backend (Phase 2 additions)         │
                         │  api/decks.py    GET /api/decks              │
                         │                  GET /api/decks/{slug}       │
                         │  api/spreads.py  GET /api/spreads?topic&deck │
                         │                  GET /api/spreads/recommend  │
                         │      │  Depends(get_current_user)  [Phase 1] │
                         │      ▼                                       │
                         │  services/catalog.py  (thick)               │
                         │   list_decks / get_deck / list_spreads /    │
                         │   recommend_spread (compat lookup+fallback) │
                         │      │ select()+selectinload()              │
                         │      ▼                                       │
                         │  PostgreSQL: decks, spread_types,           │
                         │   spread_positions, deck_spread_compat ◄─── │ seeded by
                         │   (Phase 1 schema; compat seeded in Ph2)    │ extended loader
                         └─────────────────────────────────────────────┘
```

A reader can trace the recommendation use case: user taps a TopicChip → Zustand stores `topic` → `useRecommend(topic, deckSlug)` fires → `GET /api/spreads/recommend` → `CatalogService.recommend_spread` looks up `deck_spread_compatibility` (joined to topic via the deck's/spread's `recommended_topics`), picks the `is_recommended` / highest-`compatibility_score` spread, else falls back, and returns `{recommended_spread, reason}`.

### Recommended Project Structure (additive — extends Phase 1)

```
backend/app/
├── api/
│   ├── decks.py          # NEW: GET /api/decks, /api/decks/{slug}   (thin)
│   └── spreads.py        # NEW: GET /api/spreads, /api/spreads/recommend (thin)
├── services/
│   └── catalog.py        # NEW: CatalogService (thick — all query logic)
├── schemas/
│   └── catalog.py        # NEW: DeckOut, DeckDetailOut, SpreadOut, SpreadPositionOut,
│                         #      RecommendationOut  (Pydantic v2, from_attributes)
└── seed/
    ├── loader.py         # EXTEND: add compatibility derivation + upsert
    └── data/
        └── compatibility.json   # NEW (optional): explicit overrides, else derive in code

frontend/src/
├── main.tsx              # EXTEND: wrap <App> in <QueryClientProvider>
├── api/
│   ├── decks.ts          # NEW: fetchDecks/fetchDeck via apiFetch
│   └── spreads.ts        # NEW: fetchSpreads/fetchRecommendation via apiFetch
├── hooks/
│   ├── useDecks.ts       # NEW: TanStack Query hooks
│   └── useSpreads.ts     # NEW
├── stores/
│   └── selection.ts      # NEW: Zustand {topic, deckSlug, spreadSlug, setters}
├── theme/
│   ├── deckThemes.css    # NEW: [data-deck="..."] { --bg/--accent/... } sets, or
│   └── applyDeckTheme.ts # NEW: runtime fallback if palettes come from API (see below)
└── components/
    ├── DeckCard.tsx      # NEW (TZ §21.3)
    ├── DeckCarousel.tsx  # NEW
    ├── SpreadCard.tsx    # NEW (TZ §21.3)
    ├── TopicChip.tsx     # NEW (TZ §21.3)
    └── CardArtFallback.tsx  # NEW: per-deck atmospheric SVG/CSS placeholder (DECK-05)
```

### Pattern 1: Thin router → thick `CatalogService` with eager-loaded reads
**What:** Routers do HTTP + auth dependency only; `CatalogService` owns every `select()`. This is the locked Phase 1 pattern (`api/` thin, `services/` thick — verified in `users.py`/`telegram_auth.py`).
**When to use:** All four endpoints.
**Critical detail — eager loading:** SpreadType→SpreadPosition is 1:N; serializing positions inside an async request **requires** `selectinload` or you hit a lazy-load greenlet error.
```python
# Source: SQLAlchemy 2.0 async relationship loading [CITED: docs.sqlalchemy.org/en/20/orm/queries.html]
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.spread import SpreadType

async def list_spreads(session, *, topic=None, deck_slug=None) -> list[SpreadType]:
    stmt = (
        select(SpreadType)
        .where(SpreadType.is_active.is_(True))
        .options(selectinload(SpreadType.positions))   # eager — avoids MissingGreenlet
        .order_by(SpreadType.sort_order)
    )
    if topic:
        stmt = stmt.where(SpreadType.recommended_topics.any(topic))  # PG ARRAY .any()
    # deck_slug filter -> join deck_spread_compatibility (see Pattern 3)
    return list((await session.scalars(stmt)).all())
```
> **Model gap to fix:** `SpreadType` currently has **no `positions` relationship** defined (verified in `spread.py` — only columns, no `relationship()`). Phase 2 must add `positions: Mapped[list["SpreadPosition"]] = relationship(...)` (and similarly any relationships the catalog needs) before `selectinload` works. This is a model edit, not a migration (relationships are ORM-only, no DDL). Same applies to `Deck`↔`DeckSpreadCompatibility` if joined via ORM.

### Pattern 2: Pydantic v2 response schemas with `from_attributes` + nested positions
**What:** Mirror the Phase 1 `schemas/auth.py` style. `ConfigDict(from_attributes=True)` builds the response straight from ORM rows; nest `SpreadPositionOut` inside `SpreadOut`.
```python
# Source: Phase 1 schemas/auth.py pattern [VERIFIED: backend/app/schemas/auth.py]
from pydantic import BaseModel, ConfigDict

class SpreadPositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    position_index: int
    title: str
    description: str | None = None
    prompt_instruction: str | None = None

class SpreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    title: str
    description: str | None = None
    card_count: int
    recommended_topics: list[str]
    positions: list[SpreadPositionOut]

class RecommendationOut(BaseModel):
    recommended_spread: SpreadOut
    reason: str                     # brand-voice copy, no "AI"/"модель"
```
> **IP boundary in serialization (DECK-04):** `DeckDetailOut` exposes deck catalog fields + `visual_style` (for theming). It must **not** embed base card meanings. If a deck detail ever includes cards, expose only `deck_cards` style fields (image slots) — never `cards.meaning_*`. For Phase 2 the deck detail does not need cards at all.

### Pattern 3: `/recommend` = compatibility lookup with deterministic fallback
**What:** Read `deck_spread_compatibility`; if a row exists for (deck, topic-matched spread), prefer `is_recommended=true` then highest `compatibility_score`. If no compatibility data matches (e.g. no `deck_slug` given, or no row), fall back to the highest topic-overlap active spread, else the default `three_keys`.
```python
# Recommendation resolution order (deterministic, testable):
# 1. If deck_slug given: candidate spreads = deck_spread_compatibility rows for that deck,
#    filtered to spreads whose recommended_topics include `topic`.
#    pick: is_recommended DESC, compatibility_score DESC, sort_order ASC.
# 2. Else (no deck or no compat match): active spreads where recommended_topics @> [topic],
#    pick highest overlap then sort_order.
# 3. Else: three_keys (the seeded default — its description says "подходит почти любому вопросу").
# reason: human, in-character, references the topic/deck atmosphere — NEVER mentions AI/model.
```
**Trade-offs:** (+) Always returns a spread + a reason; never 404s on a valid topic. (−) Quality of the recommendation is only as good as the derived compatibility; mitigate with `custom_note` overrides and the topic-overlap heuristic.

### Pattern 4: Runtime per-deck theming via `data-deck` + CSS-variable sets (UI-02)
**What:** Define one CSS-variable set per deck keyed by a root `data-deck` attribute; flip the attribute when `deckSlug` changes in the selection store. This is the cleanest Tailwind-v4 / CSS-vars approach and matches the project's web/coding-style rule ("design tokens as CSS vars").

**Two viable sourcing strategies — recommend (A):**

**(A) Static CSS, palettes hardcoded in `deckThemes.css`** (the 6 known palettes are fixed in MVP and identical in seed + TZ §21.2):
```css
/* Source: deck palettes verified in decks.json visual_style + TZ §21.2 [VERIFIED: backend/app/seed/data/decks.json] */
:root { --deck-bg: #0B0A0F; --deck-accent: #C9A45C; --deck-soft: #F3E3C3; --deck-deep: #6B3F1D; }
[data-deck="classic_arcana"] { --deck-bg:#1E1510; --deck-accent:#C9A45C; --deck-soft:#F3E3C3; --deck-deep:#6B3F1D; }
[data-deck="moon_mirror"]    { --deck-bg:#0B1026; --deck-accent:#5E6AD2; --deck-soft:#C7D2FE; --deck-deep:#9BD5FF; }
[data-deck="shadow_arcana"]  { --deck-bg:#08070A; --deck-accent:#8B5CF6; --deck-soft:#D6C7FF; --deck-deep:#2A1838; }
[data-deck="heart_oracle"]   { --deck-bg:#1A0710; --deck-accent:#E8A0B8; --deck-soft:#F6D7DE; --deck-deep:#8F1D46; }
[data-deck="path_deck"]      { --deck-bg:#101318; --deck-accent:#C2A46D; --deck-soft:#E5D3A3; --deck-deep:#697386; }
[data-deck="forest_oracle"]  { --deck-bg:#07130D; --deck-accent:#D08A2D; --deck-soft:#D7C58A; --deck-deep:#1F5A3D; }
```
```ts
// flip the attribute when selection changes (subscribe to Zustand)
useEffect(() => {
  document.documentElement.dataset.deck = deckSlug ?? "";
}, [deckSlug]);
```
Components style with `bg-[var(--deck-bg)]`, `text-[var(--deck-accent)]`, etc. (Tailwind v4 arbitrary values read CSS vars). A `transition` on background/color gives the "visibly changes" effect (UI-02 success criterion).

**(B) Dynamic, palettes from the API** (`visual_style.palette` is already in the `/api/decks` response): set inline CSS vars on the root from the fetched palette via `element.style.setProperty('--deck-accent', deck.visual_style.accent)`. Use this only if you want admin-edited palettes to flow through without a frontend deploy (that's a Phase 8 concern). **For MVP, (A) is simpler and testable; (B) is the post-MVP path.** Either way the values are identical.

> **"particles" (UI-02):** a particle background tinted by `--deck-accent` (a motion/CSS layer reading the CSS var) satisfies "particles change with deck" without bespoke per-deck particle systems. Full particle animation polish is shared with the ritual screen (Phase 3, UI-03) — Phase 2 only needs the accent-tinted variant to exist.

### Pattern 5: Per-deck atmospheric null-art fallback (DECK-05)
**What:** When a card's `image_url`/`thumbnail_url`/`back_image_url` is null/empty (which is **always** in Phase 2 — no `deck_cards` seeded), render a styled CSS/SVG placeholder using the active deck palette + the card's arcana symbol/initial, never a broken `<img>`.
**Concrete technique:**
```tsx
// CardArtFallback.tsx — no network, pure CSS/SVG, deck-tinted via CSS vars
// - gradient background from --deck-bg → --deck-deep
// - an inline <svg> sigil (arcana glyph or card number) stroked in --deck-accent
// - a subtle grain/glow (radial-gradient overlay) for "atmosphere" (design-quality rule)
function CardArt({ src, alt, arcanaGlyph }: { src?: string|null; alt: string; arcanaGlyph: string }) {
  if (src) return <img src={src} alt={alt} width={...} height={...} loading="lazy" />;
  return (
    <div className="card-art-fallback" role="img" aria-label={alt}>
      <svg viewBox="0 0 100 160" aria-hidden>{/* sigil stroked in var(--deck-accent) */}</svg>
    </div>
  );
}
```
This is testable in vitest/RTL: render a card with `src=null` → assert the fallback element (`role="img"` / a `data-testid`) is present and no `<img>` is rendered.

### Anti-Patterns to Avoid
- **Mirroring catalog data into Zustand.** TanStack Query owns `/api/decks`, `/api/spreads`, `/recommend` responses. Zustand holds only `{topic, deckSlug, spreadSlug}` (the user's choices), never the fetched lists. (ARCHITECTURE + web/patterns rule; Phase 1 session store comment already states this.)
- **Lazy-loading relationships on the async session.** Always `selectinload` positions/compat. A bare `spread.positions` access in a response will raise.
- **Re-deriving the recommendation client-side.** The rule lives in `CatalogService`; the client only renders `{recommended_spread, reason}`.
- **Embedding `cards.meaning_*` in any deck/style response.** Violates DECK-04 IP boundary.
- **Putting "AI"/"модель"/"нейросеть" into the `reason` string** or any microcopy.
- **Building a Redis cache + invalidation now.** Premature — admin edits (the bust trigger) are Phase 8; catalog is 13 rows.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Server-state caching / refetch / loading & error states | A custom fetch+useState+useEffect cache | TanStack Query `useQuery` | Already a dependency; handles SWR, dedupe, retries, `isPending`/`isError`. |
| Bearer attachment on catalog fetches | A new fetch wrapper | Existing `apiFetch` (`api/client.ts`) | Phase 1 built it as the reusable Bearer seam; reuse verbatim. |
| ORM→JSON serialization | Manual dict-building | Pydantic v2 `from_attributes` + `response_model` | Matches Phase 1; validates + documents via OpenAPI. |
| Idempotent compatibility seeding | A new ad-hoc script | Extend `loader.py` (`run_seed`) with the same upsert-or-scoped-delete pattern | `loader.py` already owns FK-safe idempotent seeding; compat has no slug → use scoped delete→insert keyed by (deck_id, spread_type_id), exactly like `spread_positions`. |
| ARRAY topic filtering | Python-side list filtering after fetch | PG `ARRAY .any()` / `@>` in the `select()` | Push the filter to the DB; `recommended_topics` is `TEXT[]`. |

**Key insight:** Phase 2 is almost entirely *assembly* of Phase 1 primitives. The only genuinely new logic is the **compatibility derivation rule** and the **recommendation fallback** — everything else is wiring established patterns.

## Runtime State Inventory

> This is a greenfield read-only slice — no rename/refactor/migration. **One data-population item** is in scope (compatibility seed), which is a seed task, not a runtime-state migration. No OS/secret/build-artifact state changes.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `deck_spread_compatibility` table is **empty** (not seeded by Phase 1 `loader.py` — verified). SPREAD-04 reads it. | **Seed task:** derive + upsert compatibility rows (data population, not migration). |
| Stored data | `deck_cards` table is **empty** (not seeded). DECK-05 fallback depends on art being absent. | **None required** for Phase 2 (fallback handles null art). Optional: decide whether to seed empty `deck_cards` shells (open question). |
| Live service config | None — no external service holds catalog state. | None. |
| OS-registered state | None. | None. |
| Secrets/env vars | None new. Reuses `DATABASE_URL`, `JWT_SECRET`, `VITE_API_BASE` from Phase 1. | None. |
| Build artifacts | Frontend adds a `QueryClientProvider` in `main.tsx`; no stale artifacts. | None. |

**Verified explicitly:** the empty-table findings come from reading `loader.py` (it seeds only `topics/decks/cards/spread_types/spread_positions/prompt_templates` and its own docstring states `deck_cards`/`deck_spread_compatibility` are "authored alongside art/compat in Phase 2").

## Common Pitfalls

### Pitfall 1: SPREAD-04 has no data (the seed gap)
**What goes wrong:** `/api/spreads/recommend` is built to "honor `deck_spread_compatibility`", but the table is empty, so it silently always hits the fallback and SPREAD-04's acceptance ("honoring compatibility") is never actually exercised.
**Why it happens:** Phase 1 deliberately scoped compat out (its loader docstring says so); easy to assume "seed exists = all catalog data exists."
**How to avoid:** Make "derive + seed `deck_spread_compatibility`" an explicit Wave-0/early task **with its own test** asserting non-zero rows AND that at least one (deck, spread) pair is `is_recommended=true`. The recommend test must cover both the compat-hit and the fallback path.
**Warning signs:** `/recommend` returns the same spread for every deck; compat row count is 0.

### Pitfall 2: Async lazy-load on nested positions
**What goes wrong:** `SpreadOut` serializes `positions`, but the query didn't eager-load → `MissingGreenlet` / `sqlalchemy.exc.StatementError` at response time (works in a sync REPL, fails under FastAPI async).
**Why it happens:** `selectinload` is easy to forget; also **`SpreadType.positions` relationship doesn't exist yet** (model only has columns).
**How to avoid:** Add the `relationship()` to the model first, then always `.options(selectinload(...))`. Add an integration test that hits `/api/spreads` and asserts positions are present.
**Warning signs:** Endpoint 500s with a soft-error JSON (the Phase 1 handler will mask the real cause — check server logs for greenlet/StatementError).

### Pitfall 3: No `QueryClientProvider` mounted
**What goes wrong:** First `useQuery` call throws "No QueryClient set, use QueryClientProvider".
**Why it happens:** TanStack Query is installed but unused in Phase 1; the provider was never added.
**How to avoid:** Add `QueryClient` + `<QueryClientProvider>` in `main.tsx` as a Wave-0 frontend task before any hook is written.
**Warning signs:** Runtime error on first catalog render.

### Pitfall 4: Theme doesn't visibly change (UI-02 acceptance)
**What goes wrong:** CSS vars are set but components use hardcoded Tailwind colors, so selecting a deck changes nothing visible.
**Why it happens:** Mixing fixed palette utility classes with the CSS-var theme.
**How to avoid:** Catalog components must consume `var(--deck-*)` (via Tailwind arbitrary values or a small set of themed utility classes), and the root background must read `--deck-bg`. Add a vitest/jsdom test asserting `document.documentElement.dataset.deck` updates when `setDeck` is called, plus a Playwright visual check (DB-gated → user smoke) that two decks render different backgrounds.
**Warning signs:** `data-deck` flips but the UI looks identical.

### Pitfall 5: Recommendation `reason` leaks brand-voice violations
**What goes wrong:** A generated/templated reason includes "модель рекомендует" or similar.
**Why it happens:** Reason copy is easy to write technically.
**How to avoid:** Keep reason templates in-character ("Для темы «Любовь» колода чаще раскрывается через расклад «Между нами»…"). Add a test scanning the reason for the banned substrings (`/ai|нейросет|модель|сгенерирован/i`).

## Code Examples

### Catalog GET hook (TanStack Query v5)
```ts
// Source: TanStack Query v5 useQuery API [CITED: tanstack.com/query/v5/docs/react/reference/useQuery]
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchSpreads } from "../api/spreads";

export function useSpreads(topic?: string, deckSlug?: string) {
  return useQuery({
    queryKey: ["spreads", { topic, deckSlug }],
    queryFn: () => fetchSpreads({ topic, deckSlug }),
    staleTime: 5 * 60_000,           // catalog is near-static
    placeholderData: keepPreviousData, // v5 replacement for keepPreviousData:true
  });
}
```

### Recommendation hook (gated on a chosen topic)
```ts
export function useRecommendation(topic?: string, deckSlug?: string) {
  return useQuery({
    queryKey: ["recommend", { topic, deckSlug }],
    queryFn: () => fetchRecommendation({ topic: topic!, deckSlug }),
    enabled: Boolean(topic),         // don't fire until a topic is picked
  });
}
```

### Selection store (Zustand — client state only)
```ts
// Source: Phase 1 stores/session.ts pattern [VERIFIED: frontend/src/stores/session.ts]
import { create } from "zustand";
interface SelectionState {
  topic: string | null; deckSlug: string | null; spreadSlug: string | null;
  setTopic: (t: string|null) => void;
  setDeck: (d: string|null) => void;
  setSpread: (s: string|null) => void;
}
export const useSelection = create<SelectionState>((set) => ({
  topic: null, deckSlug: null, spreadSlug: null,
  setTopic: (topic) => set({ topic }),
  setDeck: (deckSlug) => set({ deckSlug }),
  setSpread: (spreadSlug) => set({ spreadSlug }),
}));
```

### Thin router (mirrors users.py)
```python
# Source: Phase 1 api/users.py thin-router pattern [VERIFIED: backend/app/api/users.py]
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, get_session
from app.schemas.catalog import DeckOut
from app.services import catalog

router = APIRouter(tags=["decks"])

@router.get("/decks", response_model=list[DeckOut])
async def list_decks(_=Depends(get_current_user), session=Depends(get_session)):
    return await catalog.list_decks(session)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TanStack Query `keepPreviousData: true` + `isPreviousData` | `placeholderData: keepPreviousData` helper | v5 (2023) | Use the helper import; the boolean option is removed. [CITED: tanstack.com migrating-to-v5] |
| Tailwind `tailwind.config.js` + PostCSS | Tailwind v4 CSS-first `@theme` + `@tailwindcss/vite` | v4 | Theming is CSS-vars-native; matches `index.css` already in repo. [CITED: STACK.md] |
| Pydantic v1 `orm_mode`/`.dict()` | v2 `from_attributes=True`/`.model_dump()` | v2 | Already the Phase 1 convention. |

**Deprecated/outdated:** none newly relevant to this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Compatibility should be **derived from `recommended_topics` overlap** (TZ provides no explicit deck→spread mapping). | Patterns / Stack | If the user wants hand-curated pairings, the derivation must be replaced with an authored table. Low risk — derivation is a sensible default and `/discuss-phase` can confirm. Override via `custom_note`/explicit `compatibility.json`. |
| A2 | All catalog routes require auth (`get_current_user`), like every other app route. | Stack / Patterns | If catalog should be public (unauthenticated preview), the dependency is dropped. Low risk — Phase 1 established "auth gates everything"; TZ shows no public catalog. **Confirm in discuss.** |
| A3 | Redis catalog caching is **skipped for MVP** (DB read per request). | Stack / Patterns | If load is high, add a TTL cache later. Negligible risk at MVP scale (13 rows). |
| A4 | `deck_cards` rows are **not seeded** in Phase 2 (fallback handles null art); real art is Phase 8 content. | Runtime State / DECK-05 | If the user expects seeded placeholder image URLs, add a `deck_cards` seed task. Medium-relevance open question (below). |
| A5 | Static hardcoded palette CSS (strategy A) is acceptable for MVP theming vs. API-driven (strategy B). | Pattern 4 | If admin-editable palettes must work pre-Phase-8, use strategy B. Low risk — values are identical and B is a small change. |
| A6 | `/recommend` fallback default spread is `three_keys`. | Pattern 3 | If a different default is wanted, change one constant. Trivial. (`three_keys` is the seeded "подходит почти любому вопросу" default.) |

## Open Questions

1. **Should Phase 2 seed `deck_cards` shells (78×6 rows with null/empty art), or leave the table empty and rely purely on the frontend fallback?**
   - What we know: DECK-05 only requires the *fallback* to render; no art exists. The catalog endpoints in TZ §14.3/§14.4 don't return per-card data for decks.
   - What's unclear: whether any Phase 2 UI needs to enumerate a deck's 78 cards (e.g. a "card gallery" preview). The success criteria say "preview" of a deck, which the `visual_style` + a few sample fallbacks can satisfy without 468 rows.
   - Recommendation: **leave `deck_cards` empty in Phase 2**; render fallbacks. Seed `deck_cards` only if a deck-detail card grid is actually in the plan. Confirm in `/discuss-phase`.

2. **Is the catalog authenticated or public?** (Assumption A2.)
   - Recommendation: keep it behind `get_current_user` for consistency; confirm.

3. **Derived vs. authored compatibility, and exact scoring.** (Assumption A1.)
   - Recommendation: derive from topic overlap (`compatibility_score = |deck.recommended_topics ∩ spread.recommended_topics|`, `is_recommended = score ≥ 2` or top-1 per topic), allow `custom_note`. Confirm the rule in discuss.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (via Docker) | All catalog reads + compat seed | ✗ (Docker daemon not running in this env — consistent across Phase 1 plans) | postgres:16 target | Tests skip cleanly via `_db_ready`; DB-gated assertions run as **user smoke** |
| Redis | Only if optional cache added (not recommended) | ✗ | redis:7 | Skip cache for MVP |
| Node + pnpm/npm | Frontend build/test | ✓ (Phase 1 ran `npm run build`/`vitest`) | per package.json | — |

**Missing dependencies with no fallback:** none that block *writing/validating* code — DB-touching tests are written and skip cleanly (the established Phase 1 pattern), then run live by the user.
**Missing dependencies with fallback:** PostgreSQL → DB-gated tests skip; covered by a documented user smoke (`docker compose up` → `alembic upgrade head` → `python -m app.seed` → `pytest`).

## Validation Architecture

> `workflow.nyquist_validation: true` (verified in config.json) — this section is required.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio + httpx `ASGITransport` (Phase 1 established) |
| Backend config | `backend/pyproject.toml` / `pytest` settings (Phase 1); integration conftest with transaction-isolated session + `_db_ready` skip |
| Frontend framework | Vitest 3 + jsdom 25 (+ React Testing Library to add — `@testing-library/react` is **not yet installed**; component tests need it) |
| Quick run (backend) | `cd backend && pytest -q tests/unit` |
| Quick run (frontend) | `cd frontend && npm run test` (`vitest run`) |
| Full suite (backend) | `cd backend && pytest -q` (DB-gated integration runs under `docker compose up`) |

> **Wave-0 gap:** component tests for `DeckCard`/`CardArtFallback`/theme need `@testing-library/react` + `@testing-library/jest-dom`. Pure-logic tests (selection store, theme attribute effect, recommendation-reason brand-voice scan) can run with bare vitest/jsdom. Add RTL as a Wave-0 devDep if component-render assertions are in scope.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DECK-03 | `GET /api/decks` returns 6 active decks (sorted by sort_order) | integration (DB) | `pytest -q tests/integration/test_catalog_decks.py::test_list_decks_returns_six` | ❌ Wave 0 |
| DECK-03 | `GET /api/decks/{slug}` returns detail; unknown slug → 404 | integration (DB) | `pytest -q tests/integration/test_catalog_decks.py::test_deck_detail` | ❌ Wave 0 |
| DECK-03/AUTH | catalog routes 401 without Bearer | integration (no DB needed — 401 before query) | `pytest -q tests/integration/test_catalog_auth.py` | ❌ Wave 0 |
| DECK-04 | deck/detail response contains **no** `cards.meaning_*` fields (IP boundary) | unit (schema) | `pytest -q tests/unit/test_catalog_schema.py::test_no_base_meaning_leak` | ❌ Wave 0 |
| SPREAD-03 | `GET /api/spreads` returns 7 with nested positions (23 total) | integration (DB) | `pytest -q tests/integration/test_catalog_spreads.py::test_list_spreads_with_positions` | ❌ Wave 0 |
| SPREAD-03 | `GET /api/spreads?topic=love` filters by topic | integration (DB) | `...::test_spreads_topic_filter` | ❌ Wave 0 |
| SPREAD-04 | `deck_spread_compatibility` has rows after seed (≥1 `is_recommended`) | integration (DB) | `pytest -q tests/integration/test_seed_compatibility.py` | ❌ Wave 0 |
| SPREAD-04 | `/recommend?topic=love&deck_slug=heart_oracle` returns a spread + reason honoring compat | integration (DB) | `pytest -q tests/integration/test_recommend.py::test_recommend_uses_compatibility` | ❌ Wave 0 |
| SPREAD-04 | `/recommend` falls back when no compat row matches | integration (DB) | `...::test_recommend_fallback` | ❌ Wave 0 |
| SPREAD-04/SAFE-06 | recommendation `reason` contains no banned brand-voice substrings | unit | `pytest -q tests/unit/test_recommend_reason.py` | ❌ Wave 0 |
| DECK-05 | card with null art renders atmospheric fallback (no `<img>`) | frontend component (vitest+RTL) | `npm run test -- CardArtFallback` | ❌ Wave 0 |
| UI-02 | selecting a deck updates `document.documentElement.dataset.deck` / CSS vars | frontend unit (vitest+jsdom) | `npm run test -- theme` | ❌ Wave 0 |
| UI-02 | two decks render visibly different backgrounds | visual (Playwright) | **user smoke** (Playwright not yet wired; DB+running app needed) | ❌ user smoke |

### Sampling Rate
- **Per task commit:** backend `pytest -q tests/unit` + the touched integration file; frontend `npm run test` (relevant file). Quick (<30s) where DB-free.
- **Per wave merge:** full `pytest -q` (integration skips without DB) + full `vitest run`.
- **Phase gate:** full suite green; DB-gated integration confirmed green by the user smoke (`docker compose up` → migrate → seed → `pytest`) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `backend/tests/integration/test_catalog_decks.py`, `test_catalog_spreads.py`, `test_recommend.py`, `test_seed_compatibility.py`, `test_catalog_auth.py` — cover DECK-03/05, SPREAD-03/04.
- [ ] `backend/tests/unit/test_catalog_schema.py`, `test_recommend_reason.py` — IP-boundary + brand-voice (DB-free).
- [ ] `frontend`: add `@testing-library/react` + `@testing-library/jest-dom` devDeps; `selection.test.ts`, `theme.test.ts`, `CardArtFallback.test.tsx`.
- [ ] `frontend/src/main.tsx`: mount `QueryClientProvider` (prerequisite, not a test, but Wave-0).
- [ ] Model edit: add `SpreadType.positions` relationship (+ any compat relationship) before `selectinload`.

> **DB-gated note:** Docker is unavailable in this environment (consistent across all Phase 1 plans). All DB-touching integration tests must be **written** and must **skip cleanly** via the existing `_db_ready` fixture, then be run live by the user. The auth-401 and all unit/schema/frontend-logic tests run without a DB now.

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high` (verified in config.json).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Reuse Phase 1 `get_current_user` (Bearer JWT, HS256 pinned). No new auth code. |
| V3 Session Management | yes (inherited) | Phase 1 JWT; no session changes in this phase. |
| V4 Access Control | yes | Every catalog route gated by `get_current_user`. Catalog is read-only, non-user-specific data — no per-object authorization needed (no user-owned rows are read). Admin write paths are Phase 8 (not here). |
| V5 Input Validation | yes | `topic` / `deck_slug` are query params → validate as constrained strings; use parameterized `select()` (no string-built SQL). Unknown slug → 404, not an error leak. Pydantic validates request/response. |
| V6 Cryptography | no | No crypto in this phase. |
| V7 Error Handling | yes (inherited) | Phase 1 global soft-error handler already prevents stack-trace leaks; the catalog 500 path (e.g. greenlet error) returns the soft RU JSON — ensure real cause is logged server-side. |

### Known Threat Patterns for {FastAPI read API + React catalog}
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via `topic`/`deck_slug` query params | Tampering | Parameterized SQLAlchemy `select()` + ARRAY `.any()`/`@>`; never f-string SQL. |
| Unauthenticated catalog scraping | Information Disclosure | `get_current_user` on all routes (Assumption A2 — confirm). Catalog is non-sensitive but kept gated for consistency. |
| Enumeration / error oracle on `{slug}` | Information Disclosure | Return a clean 404 for unknown slugs; no internal detail. |
| Brand-voice leak ("AI/модель") in API `reason` | (product/compliance) | Brand-voice test on the `reason` string; in-character templates only. |
| XSS via deck copy rendered in React | Tampering | React escapes by default; do **not** use `dangerouslySetInnerHTML` for deck/spread text. CSS-var theme values are controlled (seeded palettes), not user input. |

## Sources

### Primary (HIGH confidence)
- `backend/app/models/{deck,card,spread,topic}.py` — exact columns, nullability, the empty `positions` relationship gap [VERIFIED on disk]
- `backend/app/seed/loader.py` + `data/{decks,spreads,topics}.json` — what is and isn't seeded; compatibility/deck_cards gap; palettes [VERIFIED on disk]
- `backend/app/api/{users,deps}.py`, `backend/app/main.py`, `backend/app/schemas/auth.py`, `backend/tests/integration/conftest.py` — thin-router/dep/schema/test patterns to mirror [VERIFIED on disk]
- `frontend/src/{api/client.ts,stores/session.ts,index.css,App.tsx}` + `frontend/package.json` — `apiFetch` seam, Zustand pattern, Tailwind v4 `@theme`, installed deps, missing QueryClientProvider [VERIFIED on disk]
- `.planning/REFERENCE-TZ.md` §13.7 (compat schema), §14.3/§14.4 (decks/spreads/recommend API contract → `{recommended_spread, reason}`), §21.2 (6 palettes — match seed), §21.3 (component names) [VERIFIED on disk]
- `.planning/research/STACK.md`, `ARCHITECTURE.md` — locked stack + thin/thick + state-management boundaries [CITED]
- `.planning/config.json` — `nyquist_validation`, `security_enforcement`, ASVS L1 [VERIFIED]

### Secondary (MEDIUM confidence)
- tanstack.com/query/v5/docs — `useQuery` params, `placeholderData: keepPreviousData`, v5 migration (removed `keepPreviousData` boolean) [CITED, web-verified June 2026]
- docs.sqlalchemy.org/en/20 — async `selectinload` requirement for relationship serialization [CITED — standard 2.0 async guidance]

### Tertiary (LOW confidence)
- None. (No claim in this research rests on a single unverified web source; the compatibility-derivation rule is an explicit `[ASSUMED]` design recommendation, not a sourced fact.)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — inherited from verified STACK.md; installed deps confirmed in `package.json`; zero new packages.
- Architecture/patterns: HIGH — mirror Phase 1 patterns read directly from disk; SQLAlchemy async eager-load is standard.
- Seed-gap finding: HIGH — read `loader.py` and its docstring directly; the empty tables are explicit and intentional.
- Recommendation derivation rule: MEDIUM (flagged `[ASSUMED]`) — TZ provides schema but no mapping data; the topic-overlap rule is a defensible default to confirm in discuss.
- Theming approach: HIGH — palettes verified identical in seed + TZ; CSS-var/`data-deck` is standard Tailwind v4.

**Research date:** 2026-06-10
**Valid until:** 2026-07-10 (stable — internal patterns + locked stack; only TanStack/SQLAlchemy minor APIs could drift, both low-churn)
