---
phase: 2
slug: deck-spread-catalog
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `02-RESEARCH.md` → `## Validation Architecture`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend framework** | pytest 8 + pytest-asyncio + httpx AsyncClient (ASGITransport) — reuse Phase 1 conftest |
| **Frontend framework** | Vitest + React Testing Library + a `QueryClientProvider` test wrapper |
| **Quick run command** | `cd backend && pytest -q tests/unit` ; `cd frontend && npm run test -- --run` |
| **Full suite command** | `cd backend && pytest -q` ; `cd frontend && npm run test -- --run && npm run build` |
| **Estimated runtime** | backend ~30s, frontend ~15s |

DB-backed API integration tests require live Postgres (compose). Docker engine currently unavailable in the build env → those tests skip cleanly and are listed as user smokes.

---

## Sampling Rate

- **After every task commit:** run the matching quick suite (backend unit OR frontend test --run)
- **After every plan wave:** full backend `pytest -q` + frontend `npm run test --run` + `npm run build`
- **Before `/gsd-verify-work`:** full suites green; catalog API smokes pass against a live stack
- **Max feedback latency:** ~40s

---

## Per-Task Verification Map

> Refined by planner/executor. Representative coverage of phase success criteria:

| ID | Requirement | Expected behavior | Test Type | Automated Command | Status |
|----|-------------|-------------------|-----------|-------------------|--------|
| decks-list | DECK-01/03 | `GET /api/decks` → 6 active free decks, sorted | integration (DB) | `pytest -q tests/integration/test_catalog.py::test_decks_list` | ⬜ pending |
| deck-detail | DECK-02/03 | `GET /api/decks/{slug}` → detail (tone, atmosphere, prompt_modifier, palette) | integration (DB) | `pytest -q ...::test_deck_detail` | ⬜ pending |
| deck-404 | DECK-03 | unknown slug → 404 | integration (DB) | `pytest -q ...::test_deck_not_found` | ⬜ pending |
| spreads-list | SPREAD-01/02/03 | `GET /api/spreads` → 7 spreads each with positions (title/desc/prompt_instruction) | integration (DB) | `pytest -q ...::test_spreads_list` | ⬜ pending |
| spreads-recommend | SPREAD-03/04 | `GET /api/spreads/recommend?topic=love[&deck_slug=]` → spread + reason, honoring compatibility; deterministic fallback | integration (DB) | `pytest -q ...::test_spread_recommend` | ⬜ pending |
| compat-seed | SPREAD-04 | `deck_spread_compatibility` populated (per TZ §7 deck→spread table); idempotent | integration (DB) | `pytest -q ...::test_compat_seeded` | ⬜ pending |
| catalog-auth | (Phase 1 carryover) | catalog routes require Bearer; missing/invalid → 401 | integration | `pytest -q ...::test_catalog_requires_auth` | ⬜ pending |
| theme-switch | UI-02 | selecting a deck sets `data-deck` + CSS vars (bg/accent change) | frontend (vitest/RTL) | `npm run test -- --run src/.../theme` | ⬜ pending |
| card-fallback | DECK-05 | card with null art renders atmospheric CSS/SVG fallback (no broken img/network) | frontend (vitest/RTL) | `npm run test -- --run src/.../cardFallback` | ⬜ pending |
| catalog-hooks | DECK-03/SPREAD-03 | TanStack Query hooks fetch + cache decks/spreads; QueryClientProvider mounted | frontend (vitest/RTL) | `npm run test -- --run src/.../catalog` | ⬜ pending |
| brand-voice | (brand) | no "AI/нейросеть/модель" strings in catalog UI copy | frontend/source assert | grep over frontend/src | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Backend: extend Phase 1 `tests/conftest.py` (catalog fixtures); add `tests/integration/test_catalog.py` stubs for the node IDs above
- [ ] Frontend: install/configure Vitest + React Testing Library if absent; add a `renderWithClient` helper (QueryClientProvider wrapper); test stubs for theme-switch, card-fallback, catalog-hooks
- [ ] Mount `QueryClientProvider` in `frontend/src/main.tsx` (currently missing — first consumer)
- [ ] Add `SpreadType.positions` relationship (ORM-only, no migration) so nested positions can `selectinload`

---

## Manual-Only / DB-gated Verifications

| Behavior | Requirement | Why | Test Instructions |
|----------|-------------|-----|-------------------|
| Catalog API against live DB | DECK/SPREAD | needs Postgres (Docker engine down in build env) | `docker compose up -d` → `alembic upgrade head` → `python -m app.seed` → `pytest -q tests/integration/test_catalog.py` |
| Visual per-deck theme swap on device | UI-02 | real visual confirmation | open frontend, switch decks, confirm bg/accent/microcopy change is visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (QueryClientProvider, positions relationship, frontend test setup)
- [ ] No watch-mode flags (use `--run`)
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
