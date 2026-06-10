---
phase: 01-foundation-telegram-auth
plan: 02
subsystem: database
tags: [sqlalchemy, alembic, postgresql, jsonb, enum, uuid, asyncpg, migrations, schema]

requires:
  - phase: 01-01
    provides: "DeclarativeBase + UUID/timestamp mixins, async Alembic env.py (Base.metadata target), Wave-0 pytest harness with the test_migration RED stub"
provides:
  - "17 SQLAlchemy 2 typed models (16 TZ §13 tables + the topics lookup) — Base.metadata complete for autogenerate"
  - "app/models/enums.py — 9 native PG ENUM types (StrEnum-backed, value-persisting) for the fixed status/type sets"
  - "0001_initial_schema — single initial Alembic migration creating all 17 tables, 9 ENUMs, FK indexes, and 8 UNIQUE constraints; reversible (downgrade base drops tables child-first + DROP TYPE)"
  - "Durable slug keys + telegram_id/payload uniqueness locked for every downstream phase and the admin panel"
  - "test_migration.py — real information_schema round-trip assertion (17 tables + 8 uniques + reversibility), skips cleanly when DB unreachable"
affects: [seed-loader, telegram-auth, deck-catalog, readings, payments, admin-panel]

tech-stack:
  added: []
  patterns:
    - "One model file per aggregate group (topic/user/card/deck/spread/reading/prompt/billing/analytics); __init__ imports every class so Base.metadata is autogenerate-complete"
    - "Native PG ENUMs declared once as shared SAEnum instances (values_callable persists lowercase slugs); access_type reused across decks+spread_types = one CREATE TYPE"
    - "Hand-written initial migration with explicit ENUM create/drop (create_type=False) and child-first reverse-order downgrade; validated DB-free via offline `alembic upgrade/downgrade --sql`"
    - "DB-dependent integration test drives Alembic in a worker thread (own event loop, sidesteps pytest-asyncio's running loop) and skips cleanly when Postgres is unreachable"
    - "cards/deck_cards boundary enforced in code + asserted in a DB-free unit test (no imagery in cards, no base meaning in deck_cards)"

key-files:
  created:
    - backend/app/models/enums.py
    - backend/app/models/topic.py
    - backend/app/models/user.py
    - backend/app/models/card.py
    - backend/app/models/deck.py
    - backend/app/models/spread.py
    - backend/app/models/reading.py
    - backend/app/models/prompt.py
    - backend/app/models/billing.py
    - backend/app/models/analytics.py
    - backend/alembic/versions/0001_initial_schema.py
    - backend/tests/unit/test_models_metadata.py
  modified:
    - backend/app/models/__init__.py
    - backend/tests/integration/test_migration.py

key-decisions:
  - "Native PG ENUMs (not String+CHECK) for all 9 fixed sets per RESEARCH recommendation — DB-level integrity for stable value lists"
  - "enums backed by Python enum.StrEnum (3.12) + values_callable so the DB stores lowercase slugs ('free','pending',...) and ruff UP042 stays clean"
  - "Migration HAND-WRITTEN (not --autogenerate) because no live DB in this environment; authored from Base.metadata and validated via offline SQL render (upgrade + downgrade)"
  - "topics is a lookup ONLY (not a FK target): readings.topic stays TEXT slug; decks/spreads recommended_topics stay TEXT[] (RESEARCH Pitfall 5)"
  - "app_events.user_id is a bare UUID (not a FK) per TZ §13.15 — anonymous-capable, survives user deletion for analytics"
  - "FK ondelete: CASCADE for owned children (deck_cards, user_limits, readings→reading_cards), RESTRICT for catalog/audit references (readings.deck_id, reading_cards.card_id/deck_card_id/position_id, payments/subscriptions.product_id)"
  - "Timestamp columns follow TZ exactly per table (user_limits=updated_at only; payments=created/paid/refunded, no updated_at; readings/reading_cards=created_at only) — TimestampMixin used only where TZ specifies both created_at+updated_at"

patterns-established:
  - "Aggregate-grouped model files with a central enums.py of shared native-ENUM type instances"
  - "Reversible hand-written migration: explicit CREATE TYPE up front, reverse-order DROP TABLE then DROP TYPE; offline --sql is the DB-free correctness gate"
  - "Worker-thread Alembic driver in tests so the async env.py's asyncio.run does not collide with pytest-asyncio's loop"

requirements-completed: [INFRA-02]

duration: 30min
completed: 2026-06-10
---

# Phase 01 Plan 02: Database Schema & Initial Migration Summary

**All 16 TZ §13 tables plus a `topics` lookup are now SQLAlchemy 2 typed models on `Base.metadata`, and one reversible initial Alembic migration (`0001_initial_schema`) creates all 17 tables with UUID PKs, JSONB/TEXT[] columns, 9 native PG ENUMs, FK indexes, and the 8 UNIQUE constraints (telegram_id, payment payload, six slugs) that every later phase and the admin panel depend on.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-06-10T13:03Z
- **Completed:** 2026-06-10T13:33Z
- **Tasks:** 2 executed (Task 1 TDD: RED metadata test → GREEN models; Task 2: migration + integration test)
- **Files modified:** 14 (12 created, 2 modified)

## Accomplishments

- **17 typed models (INFRA-02 substrate):** one file per aggregate — `topic`, `user`, `card`, `deck` (decks + deck_cards + deck_spread_compatibility), `spread` (spread_types + spread_positions), `reading` (readings + reading_cards), `prompt`, `billing` (user_limits + products + payments + subscriptions), `analytics` (app_events + generation_logs). `app/models/__init__.py` imports every class, so `Base.metadata.tables` has exactly 17 entries and Alembic autogenerate is complete.
- **9 native PG ENUM types** in `enums.py` (StrEnum-backed, value-persisting): `card_arcana_type`, `card_suit`, `access_type` (shared by decks + spread_types), `reading_status`, `card_orientation`, `prompt_template_type`, `product_type`, `payment_status`, `subscription_status`.
- **One reversible initial migration** `0001_initial_schema`: creates the 9 ENUMs once up front, then 17 tables in FK-dependency order (parents → children), with all UUID PKs, JSONB (`visual_style`, `raw_update`, `event_properties`), TEXT[] (`recommended_topics`, `keywords_*`, `deck_specific_keywords`), every FK indexed, and the 8 UNIQUE constraints. `downgrade()` drops tables child-first then `DROP TYPE` for each ENUM — `alembic downgrade base` returns to an empty schema.
- **Integrity locked (threat mitigations):** `users.telegram_id` UNIQUE (T-02-01 auth-upsert), `payments.payload` UNIQUE + `telegram_payment_charge_id` indexed (T-02-02 payment idempotency), `generation_logs` + `app_events` + `payments.raw_update` audit trail present (T-02-03).
- **Real migration test** (`test_migration.py`): `@pytest.mark.skip` removed; it runs `alembic upgrade head`, asserts all 17 tables + the 8 uniques via `information_schema`, then `alembic downgrade base` and asserts the tables are gone — driven through a worker thread so the async `env.py` does not collide with pytest-asyncio's loop. Skips cleanly when Postgres is unreachable.

## Task Commits

Each task was committed atomically on `gsd/phase-01-foundation-telegram-auth`:

1. **Task 1: SQLAlchemy 2 typed models for all 17 tables** (TDD) — `1edf6e8` (feat). RED was a DB-free metadata unit test (`test_models_metadata.py`) asserting 17 tables + uniques + native ENUMs + the cards/deck_cards boundary; it failed (no models), then GREEN after the models + enums landed.
2. **Task 2: Initial Alembic migration (0001) + migration test** — `1ef0b8a` (feat).

**Plan metadata:** committed separately (docs: complete plan) with this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

**Models**
- `backend/app/models/enums.py` — 9 native PG ENUM types as shared `SAEnum` instances (StrEnum + `values_callable`)
- `backend/app/models/topic.py` — `topics` lookup (slug UNIQUE, title, sort_order, is_active) — NOT a FK target
- `backend/app/models/user.py` — `User` (telegram_id BIGINT UNIQUE NOT NULL + profile/settings flags + last_seen_at)
- `backend/app/models/card.py` — `Card` (universal meaning only; arcana_type/suit ENUMs; no imagery)
- `backend/app/models/deck.py` — `Deck` + `DeckCard` (style layer, no base meaning) + `DeckSpreadCompatibility`
- `backend/app/models/spread.py` — `SpreadType` + `SpreadPosition`
- `backend/app/models/reading.py` — `Reading` (status ENUM) + `ReadingCard` (orientation ENUM, immutable)
- `backend/app/models/prompt.py` — `PromptTemplate` (type ENUM, slug UNIQUE)
- `backend/app/models/billing.py` — `UserLimits` + `Product` (product_type ENUM) + `Payment` (payload UNIQUE, status ENUM, raw_update JSONB) + `Subscription` (status ENUM)
- `backend/app/models/analytics.py` — `AppEvent` (bare UUID user_id, event_properties JSONB) + `GenerationLog` (reading_id FK)
- `backend/app/models/__init__.py` — imports all 17 model classes (autogenerate completeness)

**Migration + tests**
- `backend/alembic/versions/0001_initial_schema.py` — the single initial migration (775-line diff incl. test)
- `backend/tests/unit/test_models_metadata.py` — DB-free metadata contract (17 tables + uniques + enums + boundary)
- `backend/tests/integration/test_migration.py` — real `information_schema` round-trip; skip removed

## Decisions Made

- **Native PG ENUMs for all 9 fixed sets** (RESEARCH recommendation) over String+CHECK — DB-level integrity for stable value lists; the `access_type` type is shared across `decks` and `spread_types` (one `CREATE TYPE`).
- **`enum.StrEnum` + `values_callable`** so the DB stores the lowercase slugs the API/Telegram speak (`'free'`, `'pending'`, `'paid'`, …) and ruff `UP042` stays clean (no `(str, enum.Enum)` multiple-inheritance).
- **Hand-written migration** (not `--autogenerate`) per the orchestrator directive, because no live DB is available here. Authored from `Base.metadata` and validated with `alembic upgrade head --sql` / `downgrade head:base --sql` (offline render): 360 lines, 18 `CREATE TABLE` (17 + `alembic_version`), 9 `CREATE TYPE`, 8 `UNIQUE`, and a fully reverse-ordered downgrade.
- **`topics` is a lookup only** (RESEARCH Pitfall 5): not a FK target; `readings.topic` stays a TEXT slug, `recommended_topics` stays TEXT[].
- **`app_events.user_id` is a bare UUID, not a FK** (TZ §13.15) so events can be anonymous and survive user deletion for analytics.
- **FK `ondelete` policy:** CASCADE for owned children (deck_cards, spread_positions, deck_spread_compatibility, user_limits, readings, reading_cards, payments, subscriptions, generation_logs from their owner), RESTRICT for catalog/audit references (readings→decks/spread_types, reading_cards→cards/deck_cards/spread_positions, payments/subscriptions→products) so referenced catalog/audit rows can't be silently orphaned. (Rule 2 — correctness/integrity hardening; TZ specifies the FK but not the action.)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint] `enum.StrEnum` instead of `(str, enum.Enum)`**
- **Found during:** Task 1 (ruff check app/models)
- **Issue:** ruff `UP042` flags `class X(str, enum.Enum)` and recommends `enum.StrEnum` (available on the 3.12 target).
- **Fix:** Switched all 9 enum classes to `enum.StrEnum`; `values_callable` still persists member values.
- **Files modified:** backend/app/models/enums.py
- **Verification:** `ruff check app` exits 0; metadata test confirms enums still resolve by value.
- **Committed in:** `1edf6e8` (Task 1).

**2. [Rule 2 - Missing Critical] Explicit FK `ondelete` actions**
- **Found during:** Task 1 (writing the FK columns)
- **Issue:** TZ §13 names the foreign keys but not their delete behavior; without an explicit action, referenced catalog/audit rows (decks, products, cards, spread_positions) could be deleted out from under historical readings/payments, or owned children could be orphaned.
- **Fix:** CASCADE for owned children, RESTRICT for catalog/audit references (see Decisions). The same actions are mirrored in the migration's `ForeignKeyConstraint(..., ondelete=...)`.
- **Files modified:** backend/app/models/*.py, backend/alembic/versions/0001_initial_schema.py
- **Verification:** offline `--sql` render shows 18 `ON DELETE` clauses with the intended actions.
- **Committed in:** `1edf6e8` + `1ef0b8a`.

**3. [Rule 2 - Coverage] DB-free metadata unit test (TDD RED for Task 1)**
- **Found during:** Task 1 (the plan's only automated verify for Task 1 was a one-liner `python -c`; the tdd="true" flag needs a real RED→GREEN test, and the migration round-trip needs a live DB).
- **Issue:** Needed a fast, DB-independent RED that locks the 17-table contract + uniques + enums + the cards/deck_cards boundary so the schema is guarded even when no Postgres is up.
- **Fix:** Added `tests/unit/test_models_metadata.py` (5 assertions over `Base.metadata`). It failed first (no models), then passed after GREEN.
- **Files modified:** backend/tests/unit/test_models_metadata.py
- **Verification:** `pytest -q tests/unit` → 12 passed (5 new), 4 skipped (Plan-04 stubs).
- **Committed in:** `1edf6e8` (Task 1).

**4. [Rule 3 - Blocking] Worker-thread Alembic driver in the migration test**
- **Found during:** Task 2 (designing the integration test)
- **Issue:** The async `env.py` calls `asyncio.run`, which raises `RuntimeError` if invoked inside pytest-asyncio's already-running event loop — so calling `alembic command.upgrade` directly from an async test fails.
- **Fix:** The test runs `command.upgrade/downgrade` on a fresh worker thread (no running loop) and re-raises any error on the main thread.
- **Files modified:** backend/tests/integration/test_migration.py
- **Verification:** test collects + skips cleanly when DB is down; logic renders/validates offline. Real run is a user smoke (below).
- **Committed in:** `1ef0b8a` (Task 2).

---

**Total deviations:** 4 (1 lint, 2 missing-critical/coverage, 1 blocking). All necessary for ruff-cleanliness, schema/referential integrity, TDD discipline, or a runnable async migration test. No scope creep — exactly the 17 tables + one migration the plan specified.

**Impact on plan:** None negative. The schema matches TZ §13 field-by-field (verified against the reproduced `<behavior>` and the source TZ), the `topics` lookup is added per orchestrator directive 1, and all eight uniques + nine ENUMs are present and reversible.

## Issues Encountered

- **No live database in this environment** — Docker Desktop's Linux engine did not finish initializing within the available window (consistent with Plan 01's note), and there is no local Postgres / nothing on port 5432. The migration was therefore **validated DB-free** via Alembic offline SQL rendering (`upgrade head --sql` and `downgrade head:base --sql`), which exercises the full DDL generation path: 360 lines, all 9 `CREATE TYPE`, 18 `CREATE TABLE` (17 + `alembic_version`), 8 `UNIQUE`, and a complete reverse-order downgrade. The live `alembic upgrade head` + `pytest tests/integration/test_migration.py` is a user smoke (below); the test skips cleanly until then.
- **Backslash paths in the Bash tool** — Windows tree, POSIX shell; used `/c/zerkalo-sudby/...` forward-slash paths and the repo's `.venv/Scripts/*.exe` interpreters.

## User Setup Required

To turn the DB-free validation into a live confirmation (run once locally with Docker Desktop running):

1. **Start the stack:** `docker compose up -d` (brings up `postgres:16` + `redis:7` + backend), with a real `.env` in place (from Plan 01's setup).
2. **Apply + reverse the migration (INFRA-02 smoke):**
   ```
   cd backend && alembic upgrade head && alembic downgrade base && alembic upgrade head
   ```
   Expect each step to exit 0 (idempotent round-trip).
3. **Run the migration integration test:**
   ```
   cd backend && pytest -q tests/integration/test_migration.py
   ```
   Expect `1 passed` (it asserts all 17 tables + the 8 uniques via `information_schema`, then reverses). It skips with a clear reason when the DB is down.

## Next Phase Readiness

- **Plan 03 (seed):** the migrated schema + slug keys are locked; build `app/seed/` (topics/decks/spreads/cards/prompts) against these tables and flip `test_seed.py` from skip to real counts.
- **Plan 04 (auth):** `users.telegram_id` UNIQUE is ready for the `INSERT ... ON CONFLICT (telegram_id)` upsert; `user_limits` is in place for the limit checks.
- **Phase 7 (payments):** `payments.payload` UNIQUE + `telegram_payment_charge_id` index make Stars idempotency DB-guaranteed; `subscriptions` models the entitlement window.
- **No blockers.** Models lint clean and load (17 tables on `Base.metadata`); the migration renders correct, reversible SQL offline. Only outstanding item is the user-run live `alembic upgrade head` smoke above.

## Self-Check: PASSED

- All 12 created files + 2 modified files verified present on disk (10 model files, enums, migration, 2 tests, __init__, SUMMARY).
- Both task commit hashes verified in git history: `1edf6e8` (models), `1ef0b8a` (migration + test).
- Migration validated DB-free: offline `alembic upgrade head --sql` (360 lines, 18 CREATE TABLE, 9 CREATE TYPE, 8 UNIQUE) and `downgrade head:base --sql` (18 DROP TABLE child-first + 9 DROP TYPE) both render clean (exit 0).
- `ruff check app/models` exits 0; `pytest -q` → 12 passed, 15 skipped (DB-gated migration/health + Plan-03/04 stubs), 0 failures.

---
*Phase: 01-foundation-telegram-auth*
*Completed: 2026-06-10*
