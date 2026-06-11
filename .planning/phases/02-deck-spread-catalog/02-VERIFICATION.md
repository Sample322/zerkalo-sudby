---
phase: 02-deck-spread-catalog
verified: 2026-06-11T14:10:00Z
status: human_needed
score: 5/5 must-haves verified (in code); 2 inherently-visual/live items routed to human
overrides_applied: 0
deferred:
  - truth: "Selecting a deck changes per-deck particles (criterion 2 'particles' clause)"
    addressed_in: "Phase 3 — The Ritual (mock)"
    evidence: "Phase 3 Success Criterion 3: 'Tapping «Начать расклад» plays the ritual prep ... with dimming, particles, and a completion haptic'; UI-01/UI-03 (premium-dark atmosphere + micro-animations via motion) are mapped to Phase 3 in REQUIREMENTS.md."
human_verification:
  - test: "Open the authenticated Mini App (backend up: docker compose up → alembic upgrade head → python -m app.seed; then npm run dev). Select two different decks in the carousel."
    expected: "The app background and accent visibly change between decks (each of the 6 palettes), with a smooth ~400ms transition. data-deck flips on <html>."
    why_human: "Visible background/accent change is a visual judgment; automated tests prove the data-deck attribute flip and CSS-var wiring, but not the rendered visual result. Phase is MVP/UI mode and the plan itself defers this to a visual user smoke."
  - test: "With the backend stack up and seeded, pick a topic (e.g. «Любовь») with a deck selected (e.g. Сердечный Оракул), then a deck/topic combo with NO compatible match (e.g. topic=День + Сердечный Оракул)."
    expected: "A recommended spread + reason appears over /api/spreads/recommend. For the compatible case the reason should fit; for the no-match (topic-only/fallback) case, confirm the reason does not falsely claim the spread is specially suited to the requested deck (WR-01)."
    why_human: "Requires a live Postgres-backed server (DB-gated integration tests skip without Postgres in this env). The recommendation-reason accuracy (WR-01) is a semantic/product judgment a grep cannot certify."
  - test: "Browse the catalog and inspect a deck preview tile (and any card-slot surfaces that render)."
    expected: "Every deck with no uploaded art shows an atmospheric deck-tinted CSS/SVG placeholder (no broken image icon, no failed network request for art)."
    why_human: "Visual confirmation of the no-broken-image guarantee; automated test proves role=img/no-<img> at unit level but not the rendered atmosphere across the live carousel."
---

# Phase 2: Deck & Spread Catalog Verification Report

**Phase Goal:** The user can browse the Core-Value substrate — 6 genuinely distinct decks and 7 spreads — with a topic-aware recommendation and per-deck visual theming, served from seeded, IP-clean data (universal `cards` meaning kept separate from deck `deck_cards` style).
**Verified:** 2026-06-11T14:10:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

All five success criteria are satisfied in the codebase at the artifact, wiring, and data-flow levels. Automated tests pass end-to-end (frontend 12/12; backend 29 passed, 26 DB-gated skips). Status is `human_needed` (not `passed`) because the success criteria are inherently visual ("visibly changes background/accent") and live-API ("recommendation over HTTP"), the DB-gated integration suite cannot execute without Postgres in this environment, and the phase is MVP/UI mode. No gaps block goal achievement; the particles/microcopy portion of criterion 2 is explicitly scheduled for Phase 3 (deferred, not a gap).

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | 6 free decks in a carousel, each with name/atmosphere/tone/"for which questions"/preview, backed by `GET /api/decks` + `/api/decks/{slug}` | ✓ VERIFIED | `decks.json` = 6 distinct decks (sort_order 1–6); `catalog.list_decks` filters is_active + orders by sort_order; `api/decks.py` both routes auth-gated; `DeckCarousel`→`DeckCard` renders title/atmosphere/tone/"Для:" + `CardArt` preview; `test_decks_list` asserts exactly 6 sorted; `test_deck_detail`/`test_deck_not_found` cover detail + 404; `CatalogScreen.test.tsx` renders all 6. |
| 2 | Selecting a deck visibly changes background, accent, microcopy, and particles (per-deck palette) | ⚠️ PARTIAL (core met; particles/microcopy → Phase 3) | Background + accent: `deckThemes.css` has all 6 `[data-deck]` palettes matching `decks.json`; `useDeckTheme` flips `document.documentElement.dataset.deck`; `index.css` body bg reads `var(--deck-bg/--deck-deep)` w/ 400ms transition; components consume `var(--deck-accent/-soft)`; `useDeckTheme.test.ts` + `CatalogScreen.test.tsx` prove the flip end-to-end. **Particles: not implemented** (no particle code in frontend); **global microcopy: does not swap per deck** (atmosphere/tone is per-deck data inside DeckCard, not a global microcopy swap). Both deferred to Phase 3 (see Deferred Items). Visible bg/accent change routed to human (visual). |
| 3 | 7 spreads (3–4 cards) with positions; choosing a topic surfaces a recommended spread (with reason) via `GET /api/spreads` + `/recommend`, honoring deck↔spread compatibility | ✓ VERIFIED (advisory: WR-01 reason copy) | `spreads.json` = 7 spreads (5×3-card + 2×4-card), 23 positions, each with `prompt_instruction`; `list_spreads` eager-loads positions via selectinload + parameterized `ARRAY.any()` topic filter + deck compat subquery; `recommend_spread` stage-1 join honors `deck_spread_compatibility` (is_recommended DESC, score DESC, sort_order) → topic-only → fallback `three_keys`; compat seeded from §7 w/ topic-overlap scores; `test_spreads_list` (7 + 23 positions), `test_spreads_topic_filter`, `test_spread_recommend_honors_compat`, `test_compat_*` all assert. The *pick* honors compatibility. **Advisory (WR-01):** the *reason text* can attribute a topic-only/fallback pick to the requested deck — a copy-accuracy gap, not a compatibility-honoring failure; routed to human for the no-match case. |
| 4 | Card with no uploaded art renders an atmospheric CSS/SVG fallback (no broken images) | ✓ VERIFIED | `CardArtFallback` renders `role="img"` + inline `<svg>` sigil + gradient from `var(--deck-bg)`→`var(--deck-deep)`, **no `<img>`, no network** when `src` null; no `deck_cards.json` seed exists (table empty → fallback always exercised in Phase 2); `CardArtFallback.test.tsx` asserts both branches (null→role=img/no-img; src→img). |
| 5 | Seed data: only original deck names + style-free universal card meanings, no RWS/commercial deck references | ✓ VERIFIED | 6 original RU deck names (Классические Арканы, Лунное Зеркало, Тени Арканов, Сердечный Оракул, Колода Пути, Лесной Оракул); `cards.json` = 78 universal cards with `meaning_*`/`advice_*` held in `cards` and NEVER exposed via catalog schemas (DECK-04 — `DeckOut`/`DeckDetailOut` omit them; `test_*_no_base_meaning` assert); grep for rider/waite/smith/thoth/crowley/marseille/RWS across seed data → zero matches. |

**Score:** 5/5 truths verified in code (criterion 2 core met; its particles/microcopy clause deferred to Phase 3). 3 items routed to human for visual/live confirmation.

### Deferred Items

Items not yet met but explicitly addressed in a later milestone phase (Step 9b). Informational only — not actionable gaps.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | Per-deck **particles** and global **microcopy** swap (criterion 2's "...microcopy, and particles" clause) | Phase 3 — The Ritual (mock) | Phase 3 Success Criterion 3 explicitly lists "dimming, particles, and a completion haptic"; UI-01 (premium-dark atmosphere) and UI-03 (micro-animations via `motion`) are mapped to Phase 3 in REQUIREMENTS.md. Phase 2's plans scoped theming to the CSS-variable bg/accent swap (UI-02), which IS delivered. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/schemas/catalog.py` | DeckOut/DeckDetailOut/SpreadPositionOut/SpreadOut/RecommendationOut, from_attributes, no base-meaning leak | ✓ VERIFIED | All 5 models present w/ `ConfigDict(from_attributes=True)`; `prompt_modifier` exposed (DECK-02), `meaning_*`/`advice_*` omitted (DECK-04). |
| `backend/app/services/catalog.py` | list_decks/get_deck/list_spreads/recommend_spread, selectinload, compat + fallback | ✓ VERIFIED | All functions present; selectinload on positions; parameterized ARRAY.any(); compat join; `DEFAULT_SPREAD_SLUG="three_keys"`; pure `_build_reason`. |
| `backend/app/api/decks.py` | GET /decks, /decks/{slug} behind get_current_user | ✓ VERIFIED | Both routes auth-gated; 404 on unknown slug. |
| `backend/app/api/spreads.py` | GET /spreads, /spreads/recommend behind get_current_user | ✓ VERIFIED | Both static routes auth-gated; recommend maps None→404. |
| `backend/app/seed/data/compatibility.json` | Per-deck recommended spread slugs from §7 | ✓ VERIFIED | 6 deck rows transcribed from §7. |
| `backend/app/seed/loader.py` | `_upsert_compatibility` idempotent seed | ✓ VERIFIED | Scoped delete→insert per deck_id; is_recommended=True; topic-overlap score; wired into run_seed after decks+spreads; returns count. |
| `frontend/src/lib/queryClient.ts` | Shared QueryClient w/ catalog defaults | ✓ VERIFIED | staleTime 5m, retry 1, no refetch-on-focus. |
| `frontend/src/stores/selection.ts` | Zustand {topic,deckSlug,spreadSlug}+setters, no server mirroring | ✓ VERIFIED | All fields + setters; ARCHITECTURE boundary comment; no catalog data stored. |
| `frontend/src/theme/deckThemes.css` | 6 `[data-deck]` palettes + transition | ✓ VERIFIED | 6 palettes match decks.json; transition on body (index.css). |
| `frontend/src/theme/useDeckTheme.ts` | Effect hook writing dataset.deck | ✓ VERIFIED | Reads deckSlug from useSelection; writes dataset.deck in useEffect. |
| `frontend/src/components/CardArtFallback.tsx` | Per-deck null-art placeholder, role=img | ✓ VERIFIED | role="img", inline SVG sigil, no img/network when src null. |
| `frontend/src/api/decks.ts` + `spreads.ts` | fetch via apiFetch, typed, throw on non-ok | ✓ VERIFIED | apiFetch Bearer seam; URLSearchParams; typed CatalogError; no `any`. |
| `frontend/src/hooks/useDecks.ts` + `useSpreads.ts` | useDecks/useSpreads/useRecommendation | ✓ VERIFIED | Correct queryKeys; keepPreviousData; recommendation gated on topic. |
| `frontend/src/components/DeckCarousel.tsx` | Selection-aware carousel mapping over decks | ✓ VERIFIED | Maps over decks (never hardcoded); empty-safe; forwards onSelect(slug). |
| `frontend/src/components/CatalogScreen.tsx` | Composed catalog wired to selection + theming | ✓ VERIFIED | Mounts useDeckTheme; 7 topic chips; carousel; spread list; recommendation banner; loading/error/empty in product voice; wired into App behind AuthGate. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `api/spreads.py` | `services/catalog.py` | router delegates to catalog.recommend_spread/list_spreads | ✓ WIRED | `catalog.list_spreads(...)`, `catalog.recommend_spread(...)` called. |
| `services/catalog.py` | `deck_spread_compatibility` | select join filtering by topic + is_recommended/score | ✓ WIRED | `DeckSpreadCompatibility` joined in recommend_spread + list_spreads subquery. |
| `seed/loader.py` | `deck_spread_compatibility` | run_seed seeds compat idempotently | ✓ WIRED | `_upsert_compatibility` called from run_seed; scoped delete→insert. |
| `main.py` | `api/decks.py` + `spreads.py` | include_router under /api | ✓ WIRED | Both `include_router(..., prefix="/api")`. |
| `main.tsx` | `lib/queryClient.ts` | QueryClientProvider wraps App | ✓ WIRED | Provider wraps `<App/>` inside StrictMode. |
| `theme/useDeckTheme.ts` | `stores/selection.ts` | reads deckSlug, writes data-deck | ✓ WIRED | `useSelection((s)=>s.deckSlug)` → dataset.deck. |
| `components/CardArtFallback.tsx` | `theme/deckThemes.css` | consumes var(--deck-*) | ✓ WIRED | gradient/border use var(--deck-bg/-deep/-accent). |
| `api/decks.ts` | `api/client.ts` | fetch via apiFetch (Bearer) | ✓ WIRED | `apiFetch("/api/decks")`. |
| `hooks/useDecks.ts` | `api/decks.ts` | queryFn calls fetchDecks | ✓ WIRED | `queryFn: fetchDecks`. |
| `components/DeckCard.tsx` | `stores/selection.ts` | onSelect calls setDeck(slug) | ✓ WIRED | `onSelect(deck.slug)` → CatalogScreen binds `setDeck`. |
| `components/CatalogScreen.tsx` | `theme/useDeckTheme.ts` | mounts useDeckTheme | ✓ WIRED | `useDeckTheme()` called at top of CatalogScreen. |
| `App.tsx` | `components/CatalogScreen.tsx` | renders inside AuthGate | ✓ WIRED | `<AuthGate><CatalogScreen/></AuthGate>`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| DeckCarousel | `decksQuery.data` | `useDecks` → `fetchDecks` → `GET /api/decks` → `catalog.list_decks` → `select(Deck)` | DB query (real); 6 seeded decks | ✓ FLOWING (live confirmation = human, DB-gated) |
| SpreadCard list | `spreadsQuery.data` | `useSpreads` → `fetchSpreads` → `GET /api/spreads` → `catalog.list_spreads` → `select(SpreadType).selectinload(positions)` | DB query (real); 7 seeded spreads + 23 positions | ✓ FLOWING (live confirmation = human, DB-gated) |
| Recommendation banner | `recommendation.data` | `useRecommendation` (gated on topic) → `fetchRecommendation` → `GET /api/spreads/recommend` → `catalog.recommend_spread` compat join + fallback | DB query (real); reason from `_build_reason` | ✓ FLOWING; reason copy accuracy = human (WR-01) |
| DeckCard preview | `CardArt src={null}` | hardcoded null (no deck_cards seeded in Phase 2) | Intentional null → CSS/SVG fallback | ✓ FLOWING (fallback is the designed path) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Frontend test suite (UI-02 e2e, DECK-05, fetch paths, carousel) | `npm run test -- --run` | 7 files, 12 tests passed | ✓ PASS |
| Backend full suite (unit + DB-gated skips) | `pytest -q` (.venv) | 29 passed, 26 skipped, exit 0 | ✓ PASS |
| cards.json base-card count (DECK-04) | `python -c "len(json.load(...cards.json))"` | 78 | ✓ PASS |
| No `deck_cards.json` seed (DECK-05 fallback always exercised) | `ls app/seed/data/*.json` | topics/decks/spreads/prompts/cards/compatibility only | ✓ PASS |
| IP-clean seed (criterion 5) | grep rider\|waite\|smith\|thoth\|crowley\|marseille\|RWS in seed data | No matches | ✓ PASS |
| Brand-voice clean (no AI/нейросеть/модель in UI copy) | grep ai\|нейросет\|модель\|сгенерирован in frontend src | Only substrings (await/available/main/domain) + the test's own regex literal | ✓ PASS |
| Live decks/spreads/recommend over HTTP (seeded Postgres) | DB-gated integration | SKIPPED (no Postgres in env) | ? SKIP → human |

### Probe Execution

No conventional `scripts/*/tests/probe-*.sh` probes exist in this project, and neither the PLANs nor SUMMARYs declare probe paths. Verification relies on the unit/integration test suites (run above) + code inspection. (Step 7c: no probes declared or discovered.)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DECK-01 | 02-01 (+02-03 UI) | 6 free decks | ✓ SATISFIED | decks.json=6; test_decks_list==6; carousel renders 6. |
| DECK-02 | 02-01 | Each deck has tone/atmosphere/prompt_modifier/visual theme | ✓ SATISFIED | All 6 carry distinct tone/atmosphere/prompt_modifier/visual_style palette; DeckOut exposes prompt_modifier; test asserts. |
| DECK-03 | 02-01 (+02-03) | API catalog + detail (GET /api/decks, /{slug}) | ✓ SATISFIED | Both routes present, auth-gated, 404 on unknown. |
| DECK-04 | 02-01 | Universal `cards` meaning separate from deck style; 78 base cards | ✓ SATISFIED | cards.json=78; meaning_*/advice_* in `cards`, never in catalog schemas; FORBIDDEN_FIELDS tests pass. |
| DECK-05 | 02-02 (+02-03) | Image/thumbnail/back slots with CSS/SVG fallback | ✓ SATISFIED | CardArtFallback role=img/no-img/no-network; no deck_cards seeded → always exercised; both branches tested. |
| SPREAD-01 | 02-01 (+02-03) | 7 spreads, 3–4 cards | ✓ SATISFIED | spreads.json=7 (3/4-card); test_spreads_list==7. |
| SPREAD-02 | 02-01 | Positions w/ title, description, prompt_instruction | ✓ SATISFIED | 23 positions, each with prompt_instruction; SpreadOut nests positions; schema test asserts. |
| SPREAD-03 | 02-01 (+02-03) | API list (filter by topic/deck) + recommendation | ✓ SATISFIED | /spreads w/ topic+deck_slug filters; /spreads/recommend; tests assert. |
| SPREAD-04 | 02-01 | Recommendation honors deck_spread_compatibility | ✓ SATISFIED (advisory WR-01 on reason copy) | compat seeded from §7; recommend_spread join + ranking; test_spread_recommend_honors_compat + test_compat_* assert. |
| UI-02 | 02-02 + 02-03 | Deck selection changes bg/accent/microcopy/particles (6 palettes) | ✓ SATISFIED (bg/accent); particles/microcopy → Phase 3 | data-deck swap proven e2e; 6 palettes match §21.2/decks.json; particles/microcopy deferred per ROADMAP Phase 3. |

All 10 declared requirement IDs are accounted for across the plans and satisfied (UI-02's particles/microcopy sub-clause deferred to Phase 3, consistent with REQUIREMENTS.md mapping of UI-01/UI-03 to Phase 3). No ORPHANED requirements — REQUIREMENTS.md maps exactly DECK-01..05, SPREAD-01..04, UI-02 to Phase 2, all claimed by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/models/spread.py` | 38, 56 | ruff `UP037` — quoted forward refs in `relationship()` Mapped annotations | ℹ️ Info (quality gate) | `ruff check app tests` exits 1 (2 errors), contradicting 02-01-SUMMARY's "ruff check → clean". Both are cosmetic, auto-fixable (`--fix`), and idiomatic for SQLAlchemy forward references; no runtime/behavioral impact. Recommend `ruff check --fix` to restore a green lint gate. |
| `backend/app/services/catalog.py` | 119–123, 160 | `recommend_spread` returns `_build_reason(topic, deck)` regardless of which resolution stage chose the spread (WR-01) | ⚠️ Warning | Reason copy can claim a deck↔spread fit on a topic-only/fallback pick. The *recommendation pick* still honors compatibility; only the *reason wording* can overstate. Advisory per task instructions; routed to human for the no-match case. |

No `TBD`/`FIXME`/`XXX` debt markers in any phase-modified file. No stubs (all artifacts substantive + wired + data-flowing). No `console.log`. No banned brand-voice strings.

### Human Verification Required

1. **Visible per-deck re-theming (UI-02 / criterion 2 core)**
   - **Test:** Bring the backend up (`docker compose up` → `alembic upgrade head` → `python -m app.seed`), run `npm run dev`, open the authenticated Mini App, and select two different decks in the carousel.
   - **Expected:** Background and accent visibly change between decks (one of the 6 palettes each), with a smooth ~400ms transition; `data-deck` flips on `<html>`.
   - **Why human:** The visible background/accent change is a visual judgment. Automated tests prove the `data-deck` flip + CSS-var wiring, not the rendered result. Phase is MVP/UI mode; the plan defers this to a visual user smoke.

2. **Live recommendation over HTTP + WR-01 reason accuracy (criterion 3)**
   - **Test:** With the seeded backend up, pick a topic with a compatible deck (e.g. «Любовь» + Сердечный Оракул), then a no-match combo (e.g. topic=День + Сердечный Оракул).
   - **Expected:** A recommended spread + reason renders for both. For the no-match (topic-only/fallback) case, confirm the reason does not falsely assert the spread is specially suited to the requested deck (WR-01).
   - **Why human:** DB-gated integration cannot run without Postgres in this environment (clean skips). Reason-copy accuracy is a product/semantic judgment grep cannot certify.

3. **No-broken-image fallback in the live carousel (DECK-05 / criterion 4)**
   - **Test:** Browse the catalog and inspect deck preview tiles (and any card-slot surfaces rendered).
   - **Expected:** Every art-less surface shows an atmospheric deck-tinted CSS/SVG placeholder — no broken-image icon, no failed art network request.
   - **Why human:** Visual confirmation across the live carousel; the unit test proves role=img/no-`<img>` but not the rendered atmosphere in context.

### Gaps Summary

No gaps block goal achievement. All 5 success criteria and all 10 requirement IDs are satisfied in the codebase at the artifact, wiring, and data-flow levels, with passing automated tests (frontend 12/12; backend 29 passed / 26 DB-gated skips). Two items are routed to human verification because they are inherently visual ("visibly changes background/accent") or require a live Postgres-backed server (the DB-gated integration suite skips cleanly here) — not because anything is missing in code. The particles/microcopy portion of criterion 2 is intentionally deferred to Phase 3 (ROADMAP Phase 3 SC #3 + UI-01/UI-03 mapping), so it is recorded as a Deferred Item, not a gap.

Two advisory items for follow-up (neither fails the phase): (a) `ruff check` exits non-zero on 2 cosmetic `UP037` nits in `spread.py` — the 02-01-SUMMARY "ruff clean" claim is inaccurate; run `ruff check --fix` to restore the lint gate; (b) WR-01 (recommend_spread reason can misattribute a fallback pick to the requested deck) — the recommendation pick still honors compatibility, but the reason copy should be made deck-agnostic on topic-only/fallback branches.

---

_Verified: 2026-06-11T14:10:00Z_
_Verifier: Claude (gsd-verifier)_
