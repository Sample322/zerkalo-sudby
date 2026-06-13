---
phase: 4
slug: real-personal-reading-keystone
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `04-RESEARCH.md` → Validation Architecture. Task IDs are filled in at execution time (plans not yet written when this was created); rows are keyed by requirement.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"`) + httpx ASGITransport |
| **Config file** | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths=["tests"]`) |
| **Quick run command** | `cd backend && pytest tests/unit -x -q` |
| **Full suite command** | `cd backend && pytest -q` |
| **Estimated runtime** | ~15–30s (LLM mocked; no network) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/unit -x -q`
- **After every plan wave:** Run `cd backend && pytest -q`
- **Before `/gsd-verify-work`:** Full suite must be green; the live-API smoke test is env-gated and skipped by default.
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Task IDs (`04-NN-MM`) assigned by the planner; tracked here by requirement until then. All LLM-touching tests mock `LLMService` — no real Anthropic call.

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| READ-01 | `POST /api/readings` requires Bearer (401 without JWT); validates body | integration | `pytest tests/integration/test_readings_auth.py -x` | ❌ W0 | ⬜ pending |
| READ-02 | CSPRNG draw: count==positions; reversals off→all upright; on→reversed possible | unit | `pytest tests/unit/test_card_draw.py -x` | ❌ W0 | ⬜ pending |
| READ-02 | uses `secrets`/`SystemRandom`, not `random` | unit | `pytest tests/unit/test_card_draw.py::test_uses_csprng -x` | ❌ W0 | ⬜ pending |
| READ-03 | `ReadingOutput` schema round-trips fused §17+§18; `validate_json` rejects bad shape | unit | `pytest tests/unit/test_reading_schema.py -x` | ❌ W0 | ⬜ pending |
| READ-03/05/06 | success: mocked LLM → readings+reading_cards persisted, status completed, response carries all fields | integration | `pytest tests/integration/test_readings_flow.py::test_success -x` | ❌ W0 | ⬜ pending |
| READ-04 | invalid JSON twice → reading=failed, soft §9.8 body, limit NOT consumed | integration | `pytest tests/integration/test_readings_flow.py::test_honest_fail -x` | ❌ W0 | ⬜ pending |
| READ-04 | invalid once then valid → corrective retry escalates to Sonnet, succeeds | integration | `pytest tests/integration/test_readings_flow.py::test_corrective_retry -x` | ❌ W0 | ⬜ pending |
| READ-10 | limit consumed exactly once on success; unchanged on every non-success exit | integration | `pytest tests/integration/test_readings_limit.py -x` | ❌ W0 | ⬜ pending |
| READ-11/SAFE-06 | generated/response copy contains no banned brand token | unit | `pytest tests/unit/test_brand_guard.py -x` | ❌ W0 | ⬜ pending |
| SAFE-01/02 | normal→generate; *_sensitive→safety_modifier appended to prompt | unit | `pytest tests/unit/test_safety_routing.py -x` | ❌ W0 | ⬜ pending |
| SAFE-03 / SAFE-01 | crisis (regex+classify) → refusal, NO draw, NO generation, limit kept; gate runs BEFORE CardDrawService | integration | `pytest tests/integration/test_safety_gate.py -x` | ❌ W0 | ⬜ pending |
| SAFE-04/05 | refusal/sensitive output avoids banned categorical formulations; uses allowed soft phrasings | unit | `pytest tests/unit/test_safety_routing.py -x` | ❌ W0 | ⬜ pending |
| ANALYTICS-02 | one `generation_logs` row per LLM call with model/tokens/latency/status/version | integration | `pytest tests/integration/test_generation_logs.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_card_draw.py` — READ-02 (count/orientation/CSPRNG)
- [ ] `tests/unit/test_reading_schema.py` — READ-03 (`ReadingOutput` validation)
- [ ] `tests/unit/test_safety_routing.py` — SAFE-01/02/04/05 routing + phrasing
- [ ] `tests/unit/test_brand_guard.py` — SAFE-06 backend ban-list guard
- [ ] `tests/integration/test_readings_flow.py` — success / honest-fail / corrective-retry (mocked LLM)
- [ ] `tests/integration/test_readings_limit.py` — READ-10 consume-only-on-success
- [ ] `tests/integration/test_safety_gate.py` — SAFE-03 / D-06 gate-before-draw
- [ ] `tests/integration/test_generation_logs.py` — ANALYTICS-02
- [ ] `tests/integration/test_readings_auth.py` — READ-01 auth + body validation
- [ ] `tests/integration/conftest.py` (extend) — `fake_llm` / `fake_safety` fixtures + seeded deck/spread/cards fixture (reuse seed loader)
- [ ] Frontend `createReading.test.ts` (update mock → real `apiFetch` POST shape + error mapping; reveal awaits promise D-07; failure surfaces Повторить + Сменить колоду D-08)
- [ ] Prereq: add `anthropic` + `tenacity` to `backend/pyproject.toml`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Same question feels different per deck (tone + focus + signature) | READ-11 / Core Value | Subjective felt-quality; not assertable in code | Run the same question on 2–3 decks; confirm noticeably different tone/focus and a recognizable per-deck signature |
| Real Anthropic call returns valid `ReadingOutput` for all 6 decks / 7 spreads | READ-03/05/06 | Costs money + needs `ANTHROPIC_API_KEY`; env-gated smoke | Set key, run env-gated live smoke test once; confirm valid JSON + plausible copy |
| Ritual covers real latency with no spinner; failure shows Повторить + Сменить колоду | D-07/D-08 | Visual/timing in Telegram | Trigger a slow/failed generation in the Mini App; confirm seamless wait + correct failure actions |
| Crisis question reads as genuinely supportive (not clinical/cold) | SAFE-03 | Tone judgement | Submit a crisis-style question; confirm warm human tone, no cards, points to a real person |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
