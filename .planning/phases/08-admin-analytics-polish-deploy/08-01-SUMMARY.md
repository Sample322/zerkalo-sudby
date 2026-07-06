---
phase: 08-admin-analytics-polish-deploy
plan: 01
title: Prompt-version safety-valve (ADMIN-05)
status: complete
completed: 2026-07-07
commits: [7acfb22, "<frontend-commit>"]
requirements: [ADMIN-05, ADMIN-01]
---

# 08-01 — Prompt-version safety-valve — SUMMARY

## What shipped
The production safety valve for generation: multiple `prompt_templates` versions coexist per slug
with exactly one active, so a bad generation prompt can be **rolled back live, no redeploy**.

- **Migration 0005** (`0005_prompt_template_versions`): drops single-column slug uniqueness
  (`prompt_templates_slug_key` + unique `ix_prompt_templates_slug`, via `IF EXISTS` for
  metadata-vs-migration parity) → `UNIQUE (slug, version)` + partial-unique `uq_prompt_active_per_slug`
  (`UNIQUE (slug) WHERE is_active`) + non-unique lookup `ix_prompt_templates_slug`. Additive,
  reversible. **Validated against real Postgres**: `upgrade head` (0001→0005) → constraints correct
  (old `slug_key` gone, new pair present) → `downgrade base` → re-`upgrade head`, all clean.
- **Model** (`models/prompt.py`): slug no longer `unique=True`; `__table_args__` declares the
  `(slug, version)` UniqueConstraint + the partial-unique-active Index (metadata == migration).
- **Engine UNCHANGED**: `PromptEngine._active_template` already filtered `slug AND is_active`
  (`scalar_one_or_none`) — the partial-unique index is exactly what makes that correct.
- **Seed loader**: prompts now upsert `ON CONFLICT (slug, version)` (new `_upsert_prompts`), so a
  redeploy refreshes the seeded version in place and never clobbers an operator-created version.
- **Admin API** (`api/admin_prompts.py`, `require_admin`, mounted `/api`): `GET /api/admin/prompts`
  (grouped by slug), `POST /{slug}/versions` (create + activate), `POST /{slug}/activate` (rollback)
  — atomic deactivate-then-activate in one tx (existence-checked first → 404 mutates nothing).
  Schemas in `schemas/admin.py` (extra=forbid).
- **Frontend**: `PromptVersions.tsx` (per-slug version list, active badge, «Откатить» + «+ новая
  версия» publish form) wired into `AdminScreen`; `api/admin.ts` fetch/activate/publish. In-voice
  copy, no banned brand tokens.

## Verification
- **Backend `uv run pytest`: 143 passed** (incl. 8 new `test_admin_prompts` — publish/activate/
  rollback, 403 non-admin, 409 duplicate, 404 unknown, partial-unique guard) + `test_models_metadata`
  updated for the intentional non-unique slug.
- Migration round-trip validated against real Postgres (above). Ruff clean.
- **Frontend `tsc -b` clean, `vitest run` 123 passed.**

## Deviations / notes
- **`conftest._db_ready` improved** (create_all `checkfirst` → DROP+recreate `public` schema): a
  persistent local test DB otherwise keeps a stale schema when a model's constraints change, which
  broke the seed's new `ON CONFLICT (slug, version)`. Unchanged for the no-Postgres skip path (the
  user's normal environment), so the project's "integration skips = green" contract is preserved.
- **10 pre-existing integration failures are NOT from this plan.** They appear only because this
  sandbox has an incidental local Postgres (the project has always run with Postgres absent →
  integration skipped). They are: `test_card_draw_db` (×4, a greenlet lazy-load bug in the UNCHANGED
  `card_draw.py`) and `test_migration`/`test_seed`/`test_seed_compatibility` (×6, `DuplicateTable` —
  those tests own their schema via `alembic upgrade head`/`downgrade base` and collide with any
  `_db_ready` that pre-creates tables). Both were already failing at session start with a live DB and
  are a separate integration-harness isolation issue (create_all-vs-alembic + a lazy-load) — flagged
  for a follow-up, out of Phase-8 scope.
- Deploy applies 0005 automatically (entrypoint `alembic upgrade head`), then the seed re-seeds via
  the new `(slug, version)` conflict key — no manual step.
