---
phase: 01-foundation-telegram-auth
plan: 03
subsystem: database
tags: [seed, postgresql, sqlalchemy, upsert, on_conflict, idempotent, cli, tarot, prompts]

requires:
  - phase: 01-02
    provides: "17 SQLAlchemy models (Topic/Deck/Card/SpreadType/SpreadPosition/PromptTemplate) + slug UNIQUE constraints + the 0001 initial migration the seed upserts into"
provides:
  - "Idempotent `python -m app.seed` CLI — loads the MVP catalog (7 topics, 6 decks, 7 spreads + 23 positions, 78 cards, 11 prompt_templates) via upsert-by-slug in FK-safe order"
  - "5 JSON seed files at the exact TZ §27 slugs, IP-clean (original deck names + style-free universal card meanings)"
  - "6 distinct deck prompt_modifiers + 6 deck_modifier templates — the 'same question, different deck' core-value content, locked for Phase 2 catalog + Phase 4 prompt assembly"
  - "safety + refusal prompt templates carrying the crisis-safe copy seed for the Phase 4 SafetyService"
  - "test_seed.py — real exact-count (7/6/7/78/23/11) + idempotency assertions; skips cleanly when DB unreachable"
affects: [deck-catalog, spread-catalog, readings, prompt-engine, safety-service, admin-panel]

tech-stack:
  added: []
  patterns:
    - "Seed content authored as JSON files under app/seed/data/ + a thin loader (data/code split); meanings live as data, not Python constants, so the admin panel and content edits don't touch code"
    - "Idempotent upsert via pg_insert(...).on_conflict_do_update(index_elements=['slug']) — re-runnable seed, DB-guaranteed no duplicates"
    - "Child rows without a natural unique key (spread_positions) made idempotent by a scoped delete->insert per parent inside the same transaction"
    - "`python -m app.seed` package CLI (__main__.py) opens one AsyncSession, runs run_seed, commits once; run_seed itself does NOT commit (caller owns the transaction boundary)"
    - "Deterministic one-shot generator (_gen_cards.py) produces the 78-card JSON reproducibly; cards.json is byte-identical to its generator output"

key-files:
  created:
    - backend/app/seed/__init__.py
    - backend/app/seed/__main__.py
    - backend/app/seed/loader.py
    - backend/app/seed/data/topics.json
    - backend/app/seed/data/decks.json
    - backend/app/seed/data/spreads.json
    - backend/app/seed/data/cards.json
    - backend/app/seed/data/prompts.json
    - backend/app/seed/data/_gen_cards.py
  modified:
    - backend/tests/integration/test_seed.py

key-decisions:
  - "Seed as JSON files + loader (CLI), NOT an Alembic data-migration (RESEARCH Pattern 6) — content is re-runnable and editable independent of schema history"
  - "spread_positions idempotency via scoped delete->insert (no single-column unique key exists), not ON CONFLICT — keyed by spread_type_id so each spread rebuilds only its own positions"
  - "run_seed returns a per-table count map (used by both the CLI log and the test assertions) and does NOT commit; __main__.py commits once"
  - "78 cards carry PLACEHOLDER but non-empty universal meanings/keywords/advice (full literary copy is a later content task per the plan); meanings are style-free (cards layer), deck style stays in deck_cards"
  - "11 prompt_templates: 1 system + 1 single_card + 1 final_summary + 6 deck_modifier (one per deck) + 1 safety + 1 refusal; system/single_card/final_summary reproduce TZ §16-18, deck_modifiers reproduce TZ §19, safety/refusal carry TZ §20.3 crisis-safe copy"

patterns-established:
  - "app/seed/ data+loader+CLI structure: data/*.json authored content, loader.py upsert-by-slug, __main__.py the `python -m app.seed` entrypoint"
  - "Idempotent upsert-by-slug as the standard seed/reseed mechanism for slug-keyed catalog tables"
  - "Count-map contract: run_seed's return value is the single source of truth the integration test asserts against"

requirements-completed: [INFRA-03]

duration: 35min
completed: 2026-06-10
---

# Phase 01 Plan 03: MVP Seed Content & Idempotent Loader Summary

**An idempotent `python -m app.seed` CLI that upserts the MVP catalog by slug in FK-safe order — 7 topics, 6 decks (each with a distinct prompt_modifier + palette), 7 spreads with 23 positions, all 78 universal tarot cards (placeholder style-free meanings), and 11 prompt_templates (system/single_card/final_summary/6 deck_modifier/safety/refusal) — all at the exact TZ §27 slugs and IP-clean.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-06-10T14:05Z
- **Completed:** 2026-06-10T14:40Z
- **Tasks:** 2 executed (Task 1: seed data + loader CLI; Task 2: integration test)
- **Files created/modified:** 10 (9 created, 1 modified)

## Accomplishments

- **MVP catalog as data (INFRA-03):** five JSON files under `app/seed/data/` carrying the exact TZ §27 slug sets — `topics.json` (7), `decks.json` (6), `spreads.json` (7 spread_types + 23 positions), `cards.json` (78), `prompts.json` (11). Content lives as data, so future content edits and the admin panel never touch loader code.
- **The core-value content is locked:** all 6 decks have a genuinely **distinct** `prompt_modifier` (the "same question, different deck" differentiator, TZ §19), each with an original subtitle/atmosphere/tone (TZ §7) and a `visual_style` palette (the 6 palettes from TZ §21.2). Mirrored as 6 `deck_modifier` prompt_templates for the Phase 4 prompt engine.
- **78 universal cards, all rows present:** 22 Major Arcana (`major_00_fool` … `major_21_world`, number 0–21, suit NULL) + 56 Minor (4 suits × ace..king, `wands_01` … `pentacles_14`, number 1–14). Every row has non-empty, **style-free** `meaning_upright`/`meaning_reversed`/`advice_upright`/`advice_reversed` + keyword arrays (placeholder copy; universal layer only — no imagery, no commercial deck names). Produced reproducibly by `_gen_cards.py` (cards.json is byte-identical to its generator).
- **Idempotent loader + CLI:** `loader.py` upserts by slug with `pg_insert(...).on_conflict_do_update(index_elements=["slug"])` in FK-safe order (topics→decks→cards→spread_types→spread_positions→prompt_templates). `spread_positions` (no single-column unique key) is rebuilt per spread via a scoped delete→insert. `python -m app.seed` (`__main__.py`) opens one `AsyncSession`, runs `run_seed`, commits once, and prints the per-table counts. Verified: `python -m app.seed` resolves the module and reaches the DB connect boundary; re-running is a no-op upsert by construction.
- **Real seed test (skip removed):** `test_seed_counts` asserts the exact map `{topics:7, decks:6, spread_types:7, cards:78, spread_positions:23, prompt_templates:11}`; `test_seed_idempotent` runs `run_seed` twice and asserts identical counts with no `IntegrityError`. Both commit across transactions (idempotency is a re-run property), migrate to a clean `head` per test on a worker thread, reverse afterwards, and skip cleanly when Postgres is unreachable (matches `test_migration.py`).

## Task Commits

Each task was committed atomically on `gsd/phase-01-foundation-telegram-auth`:

1. **Task 1: Seed JSON data + idempotent upsert-by-slug loader CLI** — `40d8f5d` (feat)
2. **Task 2: Seed integration test — exact counts + idempotency** — `3311aae` (test)

**Plan metadata:** committed separately (docs: complete plan) with this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

**Seed package**
- `backend/app/seed/__init__.py` — exposes `run_seed` / `upsert_by_slug`
- `backend/app/seed/__main__.py` — `python -m app.seed` CLI: one AsyncSession, run_seed, single commit, prints counts
- `backend/app/seed/loader.py` — `upsert_by_slug` (ON CONFLICT DO UPDATE), `_upsert_spreads` (scoped delete→insert for positions), `run_seed` (FK-safe orchestration, returns count map)

**Seed data**
- `backend/app/seed/data/topics.json` — 7 topics (love/work/money/choice/day/self_reflection/general)
- `backend/app/seed/data/decks.json` — 6 decks (classic_arcana/moon_mirror/shadow_arcana/heart_oracle/path_deck/forest_oracle), distinct prompt_modifiers + palettes, all free/mvp/active
- `backend/app/seed/data/spreads.json` — 7 spread_types (card_count 3×5 + 4×2) each with its positions (sum 23)
- `backend/app/seed/data/cards.json` — 78 universal cards (22 major + 56 minor)
- `backend/app/seed/data/prompts.json` — 11 prompt_templates (system + single_card + final_summary + 6 deck_modifier + safety + refusal)
- `backend/app/seed/data/_gen_cards.py` — deterministic one-shot generator for cards.json (documents/reproduces the 78-row set)

**Tests**
- `backend/tests/integration/test_seed.py` — exact-count + idempotency assertions; Wave-0 `@pytest.mark.skip` removed

## Decisions Made

- **Seed via JSON + loader CLI, not an Alembic data-migration** (RESEARCH Pattern 6): content is re-runnable and editable independent of schema history; `python -m app.seed` is the operator entrypoint.
- **`spread_positions` idempotency via scoped delete→insert** rather than `ON CONFLICT`: the table has no single-column unique key, so each spread deletes only its own positions (keyed by `spread_type_id`) and re-inserts the authored set inside the same transaction — re-runnable without duplicates and without a schema change.
- **`run_seed` returns a count map and does NOT commit**; the CLI commits once. The same map is the contract the integration test asserts against (single source of truth for counts).
- **Cards carry placeholder, non-empty, style-free meanings** (per the plan's downstream-consumer directive): all 78 rows present so Phase 2 can render the full deck and Phase 4 can assemble prompts; full literary copy is an explicit later content task. Universal meaning stays in `cards`; deck style stays in `deck_cards` (ARCHITECTURE boundary).
- **Prompt content reproduces the TZ** field-for-field: system/single_card/final_summary from §16–18, the 6 deck_modifiers from §19, safety/refusal from the §20.3 crisis-safe formulation — so Phase 4 composes from authored copy, not improvised text.

## Deviations from Plan

None — plan executed exactly as written.

Both tasks landed exactly as specified: the Plan-02 models already exposed every column the seed needed (slugs, JSONB `visual_style`, TEXT[] keywords/recommended_topics, the prompt/spread/position fields), so no schema or model changes were required, and the FK-safe upsert + idempotency strategy worked as designed. `ruff format` reformatted `loader.py` and `_gen_cards.py` to the project's 100-col style during Task 1 (tooling normalization, not a behavior change) — both remain lint- and format-clean.

## Issues Encountered

- **No live database in this environment** (consistent with Plans 01–02: Docker Desktop's Linux engine not up, nothing on `:5432` — `python -m app.seed` reaches the TCP connect and fails with `OSError`). The seed was therefore **validated DB-free** along every path that does not require a live connection:
  - JSON count assertions (the plan's `python -c` verify): cards 78 / decks 6 / spreads 7 / topics 7 / prompts 11 — pass.
  - Structural contracts: 6 **distinct** non-empty deck prompt_modifiers, all decks free/mvp/active with palettes; spread `card_count`s {3,3,3,3,3,4,4} with `position_index` 1..N and non-empty `prompt_instruction`s summing to 23; prompt type set with exactly 6 `deck_modifier`s + system + single_card + final_summary + safety + refusal, all `template_text` non-empty; all 78 card slugs unique with all meaning/keyword fields non-empty.
  - IP-cleanliness: word-boundary scan of all seed JSON for `rider`/`waite`/`smith`/`rws`/`thoth`/`crowley`/`marseille` — zero hits.
  - `python -m app.seed` module wiring: resolves the package, imports `run_seed`, opens `SessionLocal`, and reaches the real DB connect (fails there as expected) — proving the CLI is correct up to the DB boundary.
  - **Count-contract simulation:** `run_seed` driven against a mocked `AsyncSession` returns exactly the test's `EXPECTED_COUNTS` and issues 139 `execute` calls (7 topics + 6 decks + 78 cards + 7 spread upserts + 7 position-deletes + 23 position-inserts + 11 prompts) — exercising the full loader loop and FK-safe order without a DB.
  - `ruff check` + `ruff format --check` clean on `app/seed` and the test; full suite `pytest -q` → **12 passed, 15 skipped** (the 2 new seed tests skip cleanly with a clear reason; no regressions).
  The live `alembic upgrade head && python -m app.seed && python -m app.seed` + `pytest tests/integration/test_seed.py` is a **user smoke** (below).

## User Setup Required

To turn the DB-free validation into a live confirmation (run once locally with Docker Desktop running, from `backend/` with a real `.env` in place):

1. **Start the stack:** `docker compose up -d` (`postgres:16` + `redis:7`).
2. **Apply the migration + run the seed twice (INFRA-03 idempotency smoke):**
   ```
   cd backend && alembic upgrade head && python -m app.seed && python -m app.seed
   ```
   Expect both seed runs to exit 0 and print `seed complete: topics=7, decks=6, spread_types=7, spread_positions=23, cards=78, prompt_templates=11` (no duplicate-key error on the second run).
3. **Run the seed integration test:**
   ```
   cd backend && pytest -q tests/integration/test_seed.py
   ```
   Expect `2 passed` (exact counts 7/6/7/78/23/11 + idempotency). It skips with a clear reason when the DB is down.

## Next Phase Readiness

- **Phase 2 (deck/spread catalog):** topics, decks (with palettes/tone/recommended_topics), spreads + positions, and all 78 cards are seedable at locked slugs — the catalog endpoints and the deck-selection UI have real content to render. `deck_cards` (imagery) + `deck_spread_compatibility` are intentionally NOT seeded here; they're authored alongside art/compat in Phase 2 (per the plan).
- **Phase 4 (prompt engine + safety):** the 11 prompt_templates (system, single_card, final_summary, 6 deck_modifier, safety, refusal) are present and slug-addressable; the PromptEngine composes from authored copy and the SafetyService has its crisis-safe seed.
- **No blockers.** Seed files load + parse, the loader is lint-clean and idempotent by construction, and the count contract is proven DB-free. Only outstanding item is the user-run live seed/test smoke above.

## Self-Check: PASSED

- All 9 created files + 1 modified file verified present on disk (3 package files, 5 data JSONs, 1 generator, 1 test).
- Both task commit hashes verified in git history: `40d8f5d` (seed data + loader), `3311aae` (seed test).
- Seed validated DB-free: JSON counts (78/6/7/7/11), structural contracts (distinct modifiers, 23 positions, prompt type set), IP-clean scan (zero commercial-deck hits), `python -m app.seed` reaches DB-connect, and a mocked-session `run_seed` returns exactly `EXPECTED_COUNTS` (139 execute calls).
- `ruff check` + `ruff format --check` clean on `app/seed` + the test; `pytest -q` → 12 passed, 15 skipped, 0 failures.

---
*Phase: 01-foundation-telegram-auth*
*Completed: 2026-06-10*
