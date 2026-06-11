# 02-01 Summary — Backend Catalog API

**Plan:** 02-01 (Deck & Spread Catalog — backend slice)
**Status:** complete
**Branch:** gsd/phase-02-deck-spread-catalog
**Mode:** inline execution (no subagent)

## What shipped
- **Task 1** (`719ccb7`): `SpreadType.positions` ORM relationship (no migration — metadata stays 17 tables); `compatibility.json` (6 deck→spread rows transcribed from TZ §7); `loader._upsert_compatibility` derives `deck_spread_compatibility` idempotently (scoped delete→insert by deck_id, `is_recommended=True`, `compatibility_score` = topic-overlap), wired into `run_seed` after decks+spreads; `test_seed_compatibility.py` (DB-gated).
- **Task 2** (`feat catalog schemas + service`): `schemas/catalog.py` (DeckOut incl. `prompt_modifier`, DeckDetailOut, SpreadPositionOut, SpreadOut, RecommendationOut — Pydantic v2 `from_attributes`, no base-meaning leak); `services/catalog.py` (CatalogService: list_decks/get_deck/list_spreads/recommend_spread with `selectinload`, parameterized ARRAY `.any()`, deterministic fallback `DEFAULT_SPREAD_SLUG="three_keys"`, pure `_build_reason` brand-voice RU); unit tests `test_catalog_schema.py` + `test_recommend_reason.py`.
- **Task 3** (`feat auth-gated catalog routers`): `api/decks.py` (GET /api/decks, /api/decks/{slug}→404), `api/spreads.py` (GET /api/spreads with topic/deck_slug filters, GET /api/spreads/recommend), both behind `get_current_user`; wired in `main.py`; `test_catalog.py` integration (list/detail/404/positions/topic-filter/recommend/fallback/auth).

## Requirements
DECK-01, DECK-02, DECK-03, DECK-04, SPREAD-01, SPREAD-02, SPREAD-03, SPREAD-04 — covered.

## Verification
- `ruff check` → clean on all new files.
- `pytest -q` (full backend) → **29 passed, 26 skipped** (DB-gated integration — incl. test_catalog, test_seed_compatibility — skip cleanly without Postgres). App imports + routers wire correctly (collection loads `app.main`).

## User smoke (DB-gated — Docker engine unavailable in build env)
```
docker compose up -d
cd backend && alembic upgrade head && python -m app.seed && python -m app.seed   # idempotent; count map now includes deck_spread_compatibility (28 rows)
pytest -q tests/integration/test_catalog.py tests/integration/test_seed_compatibility.py   # expect all pass
```

## Notes
- DeckOut exposes `prompt_modifier` (DECK-02) but never `cards.meaning_*`/`advice_*` (DECK-04).
- compat rows: 5+5+4+4+4+5 = 27 across 6 decks (each `is_recommended=true`).
