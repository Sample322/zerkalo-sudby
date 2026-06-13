---
phase: 04-real-personal-reading-keystone
verified: 2026-06-13T23:18:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
mode: mvp
human_verification:
  - test: "Per-deck divergence (READ-11 / Core Value, TZ §30): with the backend running + a real ANTHROPIC_API_KEY, submit the SAME question on 2-3 decks (e.g. Тени, Сердце, Лесной)."
    expected: "Noticeably different tone AND focus, plus a recognizable per-deck signature in each (D-02); no result text contains 'AI / нейросеть / модель / ИИ'."
    why_human: "Subjective felt-quality of divergence cannot be asserted programmatically; requires a real LLM call + human judgement."
  - test: "Live-API smoke (READ-03/05/06): set ANTHROPIC_API_KEY and run the env-gated live smoke across the 6 decks / 7 spreads."
    expected: "A schema-valid ReadingOutput comes back for each sample with plausible Russian copy (D-14)."
    why_human: "The automated suite mocks the LLM (no real key in this environment); the live contract holding requires a real Anthropic call."
  - test: "Ritual + failure UX (D-07/D-08): in the Telegram Mini App, trigger a normal reading; then force a failure (bad key / induced timeout)."
    expected: "The ~3s ritual covers the real wait with NO spinner and reveal happens only after JSON is ready; on failure «Колода замолчала…» + Повторить + Сменить колоду appear (question preserved) and the limit is NOT consumed (retry is free)."
    why_human: "Real-time perceived latency and the in-Telegram ritual feel require a running stack + a human; the limit-not-consumed-on-failure path is unit-verified but the end-to-end UX is not."
  - test: "Crisis tone (SAFE-03): submit a crisis-style question against the live stack."
    expected: "A warm, human, supportive response that fully breaks the mystical frame and points to a real person/specialist (generic, no phone number — D-04), with NO cards drawn and NO charge."
    why_human: "Tone/empathy quality of the refusal copy is subjective; the no-draw/no-charge short-circuit is code-verified but the felt supportiveness needs a human."
---

# Phase 4: Real Personal Reading (KEYSTONE) Verification Report

**Phase Goal:** The Core Value goes live — the user receives a real, deeply personalized reading where the same question genuinely feels different per deck. Backed by backend-only crypto card draw, the mandatory safety classifier (crisis short-circuits *before* draw/charge), versioned prompt assembly, and one synchronous structured LLM call returning all card interpretations plus the summary as schema-validated JSON, with retry/timeout/DB-fallback and no limit consumed on failure.

**Verified:** 2026-06-13T23:18:00Z
**Status:** human_needed
**Mode:** mvp (phase goal is the Core Value vertical slice)
**Re-verification:** No — initial verification

## Goal Achievement

All five ROADMAP Success Criteria are achieved at the code level and backed by green unit suites. The phase goal is observably true in the codebase; the only outstanding items are four LIVE UAT checks that require a running stack + a real `ANTHROPIC_API_KEY` (unavailable to the verifier) — these are deferred-to-human by explicit user approval (recorded in 04-06-SUMMARY.md), the same deploy-time "user smoke" pattern that closed Phases 2 and 3.

### Observable Truths (ROADMAP Success Criteria — the contract)

| #   | Truth (Success Criterion)                                                                                                                                                       | Status     | Evidence                                                                                                                                                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `POST /api/readings` draws cards server-side with a CSPRNG (reversals off→upright; on→70/30), ignoring client cards, returns per-card interpretation + connected summary        | ✓ VERIFIED | `card_draw.py` uses `secrets.SystemRandom()` (line 47), no `import random` (grep: none); `_assign_orientations` 70/30 via `REVERSED_PROBABILITY=0.30` (line 50, 94). Draw is backend-only from `deck_cards` (line 132-138); `reading.py` ignores any client cards. `ReadingOut` carries per-card name/position/orientation/short/interp/accent + 5 summary fields. Unit: `test_card_draw.py` 5/5, `test_reading_schema.py` 6/6 green. |
| 2   | The same question on two decks produces noticeably different tone/imagery/structure; no result text mentions "AI / нейросеть / модель"                                          | ✓ VERIFIED (code) / human pending (felt) | `prompt_engine.build_system_block` injects per-deck `deck_modifier` carrying tone + the mandatory D-02 "Обязательная подпись колоды" signature (all 6 decks in `prompts.json`, v2). Brand guard (`brand_guard.py`) ports the SAFE-06 ban-list + «ии» boundary; applied as LOG+FLAG in `reading.py._brand_guard` (line 542-570). Unit: `test_prompt_engine.py` 9/9, `test_brand_guard.py` 4/4 green. **Subjective divergence = human item 1.** |
| 3   | A crisis question → supportive safe response + real-person/helpline suggestion, never a mystical prediction, NO draw/charge; sensitive → softened reading; no fatalistic copy   | ✓ VERIFIED (code) / human pending (tone) | `reading.py` calls `safety.classify` (line 193) BEFORE `card_draw.draw` (line 209); `route()` → REFUSAL/REDIRECT short-circuit (line 196-200) with NO draw, limit kept. Regex pre-filter catches crisis instantly (`safety.py` line 62-81). Generic refusal copy (`prompts.json` `refusal` v2 — no phone/region, D-04); abusive redirect (`redirect` row, D-06). Sensitive → `SAFETY_MODIFIER` appends §20.3 fragment. Integration `test_safety_gate.py` (crisis/abusive/sensitive) implemented; skips only on no-PG. **Crisis tone feel = human item 4.** |
| 4   | Invalid JSON or timeout → soft in-character error, reading=failed, limit NOT consumed (after exactly one corrective retry, then DB fallback)                                    | ✓ VERIFIED | `llm.py`: `AsyncRetrying(stop_after_attempt(2))` (line 172) = one corrective retry, Haiku→Sonnet via `_model_for_attempt` (line 122-124), per-attempt `timeout=ATTEMPT_TIMEOUT_SECONDS` (line 141), `reraise=True` → `LLMGenerationError` (line 186). `reading.py._honest_fail` (line 619-652): status=FAILED, truncated `generation_error`, NO consume, NO templated stand-in (grep: "templated" only in docstrings stating it is NOT assembled), soft §9.8 body. Unit `test_llm_service.py` 8/8 green. |
| 5   | Every generation writes prompt_version, model, input/output tokens, latency, status, and any error to `generation_logs`                                                        | ✓ VERIFIED | `GenerationLog` model (analytics.py) has all fields incl. `prompt_template_version`/`model_name`/`input_tokens`/`output_tokens`/`latency_ms`/`status`/`error`; `reading_id` is NOT-NULL FK (line 39). `reading.py` writes one row per ACTUAL LLM call: classify (`_log_classify`, line 517, only when `meta is not None`), completed (`_generate`, line 484), failed (`_honest_fail`, line 634). Integration `test_generation_logs.py` implemented. |

**Score:** 5/5 truths verified at the code level (4 carry a live human-confirmation tail).

### Required Artifacts

| Artifact                                  | Expected                                                              | Status     | Details                                                                                                                                  |
| ----------------------------------------- | --------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `backend/app/services/reading.py`         | gate→draw→generate→consume orchestration + honest fail + gen_logs     | ✓ VERIFIED | 731 lines; locked order verified line 180-256; single consume point; imported by `api/readings.py`; substantive (no stubs/TODOs).        |
| `backend/app/services/safety.py`          | regex pre-filter + Haiku classify → SafetyVerdict + routing            | ✓ VERIFIED | 211 lines; `_regex_prefilter` + `messages.parse(output_format=SafetyVerdict)` + total `route()` mapping; used by reading.py.             |
| `backend/app/services/card_draw.py`       | backend-only CSPRNG draw, 70/30 orientation                            | ✓ VERIFIED | 176 lines; `secrets.SystemRandom`; no `random`; returns `DrawnCard` records; used by reading.py.                                         |
| `backend/app/services/llm.py`             | messages.parse + tenacity 1-retry Haiku→Sonnet + timeout + usage       | ✓ VERIFIED | 205 lines; `AsyncRetrying`, aliases (no dated snapshot), `LLMGenerationError`; used by reading.py.                                       |
| `backend/app/services/prompt_engine.py`   | fused single-call prompt + signatures + safety_modifier + prompt_version | ✓ VERIFIED | 425 lines; reads active `PromptTemplate` rows; per-deck signature; Russian + ≤140 restate; `compose_prompt_version`; used by reading.py. |
| `backend/app/core/brand_guard.py`         | SAFE-06 ban-list backend port                                          | ✓ VERIFIED | 42 lines; ports frontend regex incl. «ии» boundary; used by reading.py.                                                                  |
| `backend/app/core/llm_client.py`          | AsyncAnthropic singleton reading ANTHROPIC_API_KEY                     | ✓ VERIFIED | `AsyncAnthropic()` from env, no key passed/logged.                                                                                       |
| `backend/app/schemas/reading.py`          | ReadingOutput/SafetyVerdict/ReadingCreate/ReadingOut + 7 categories    | ✓ VERIFIED | 299 lines; no `max_length` on LLM-output fields; length in descriptions (Pitfall 1); 7-member SafetyCategory.                            |
| `backend/app/api/readings.py`             | POST /api/readings thin router (Bearer, ReadingCreate→ReadingOut)      | ✓ VERIFIED | Thin; `get_current_user` gate; user from JWT not body; ReadingInputError→404; mounted in main.py line 52.                                |
| `backend/app/seed/data/prompts.json`      | D-02 signatures, generic D-04 refusal, D-06 redirect                   | ✓ VERIFIED | 6 `deck_modifier_*` rows v2 with "Обязательная подпись колоды"; `refusal` v2 generic (no phone/region); `redirect` row present.          |
| `frontend/src/reading/createReading.ts`   | real POST /api/readings via apiFetch, ReadingOut→MockReading           | ✓ VERIFIED | `apiFetch('/api/readings', POST)`; documented name map; rejects on non-success; no `any`; store-slot preserved (D-05 guard).             |
| `frontend/src/components/CatalogScreen.tsx` | D-08 failure UX (Повторить + Сменить колоду)                          | ✓ VERIFIED | `startError` state; catch sets it + does NOT advance; renders READING_ERROR + READING_RETRY + READING_CHANGE_DECK; no spinner; setReading before goTo. |

### Key Link Verification

| From                       | To                            | Via                                                | Status   | Details                                                                                          |
| -------------------------- | ----------------------------- | -------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------ |
| `api/readings.py`          | `services/reading.py`         | thin router delegates to ReadingService            | ✓ WIRED  | `service.create_reading(session, user, body)` (line 60) via `get_reading_service` dependency.    |
| `services/reading.py`      | `services/safety.py`          | safety gate BEFORE CardDrawService (locked order)  | ✓ WIRED  | `self._safety.classify` line 193 precedes `self._card_draw.draw` line 209 (grep-confirmed order).|
| `services/reading.py`      | `models/analytics.py`         | writes a GenerationLog row per LLM call            | ✓ WIRED  | `GenerationLog(...)` written in `_log_classify`/`_generate`/`_honest_fail`.                       |
| `main.py`                  | `api/readings.py`             | include_router mounts POST /api/readings           | ✓ WIRED  | `app.include_router(readings.router, prefix="/api")` line 52.                                     |
| `services/llm.py`          | `core/llm_client.py`          | calls AsyncAnthropic singleton's messages.parse    | ✓ WIRED  | `self._client.messages.parse(...)` line 134; client defaults to singleton.                       |
| `services/prompt_engine.py`| `models/prompt.py`            | reads active PromptTemplate rows                   | ✓ WIRED  | `_active_template` selects active rows; `compose_prompt_version` from `t.version`.               |
| `createReading.ts`         | `api/client.ts`               | apiFetch attaches Bearer JWT                       | ✓ WIRED  | `apiFetch("/api/readings", {method:"POST", ...})` line 108.                                       |
| `CatalogScreen.tsx`        | `reading/createReading.ts`    | CTA awaits createReading then setReading→goTo      | ✓ WIRED  | `await createReading(...)` line 82, `setReading` line 90 before `goTo("ritual")` line 91.         |

### Data-Flow Trace (Level 4)

| Artifact            | Data Variable        | Source                                       | Produces Real Data | Status     |
| ------------------- | -------------------- | -------------------------------------------- | ------------------ | ---------- |
| `ReadingOut` (API)  | cards / summary      | persisted `reading_cards` + `summary_full` from the real `ReadingOutput` of `LLMService.generate` (live) or `FakeLLM` (tests) | ✓ (live path) / mocked in tests | ✓ FLOWING (code) |
| `createReading.ts`  | MockReading          | `apiFetch('/api/readings')` real POST response | ✓ (depends on live backend) | ✓ FLOWING |
| `CatalogScreen.tsx` | reading store slot   | `createReading(...)` real call               | ✓ | ✓ FLOWING |

Note: the LLM data source itself is a real Anthropic `messages.parse` call in production; in the test substrate it is a `FakeLLM` returning a fully-populated `ReadingOutput`. Whether the live API returns plausible Russian copy across all decks is human verification item 2 (live-API smoke).

### Behavioral Spot-Checks

| Behavior                                  | Command                                                                 | Result                          | Status |
| ----------------------------------------- | ----------------------------------------------------------------------- | ------------------------------- | ------ |
| Backend full suite (unit + integration)   | `uv run pytest -q`                                                      | 82 passed, 49 skipped, 0 fail   | ✓ PASS |
| Backend unit suite (keystone code)        | `uv run pytest -q tests/unit/`                                         | 81 passed, 0 fail               | ✓ PASS |
| Frontend full suite                       | `node node_modules/vitest/vitest.mjs run`                              | 80 passed (15 files), 0 fail    | ✓ PASS |
| Frontend createReading + copy             | `vitest run src/reading/createReading.test.ts src/reading/copy.test.ts` | 16 passed                       | ✓ PASS |
| Frontend D-08 failure UX                  | `vitest run src/components/CatalogScreen.failure.test.tsx`             | 5 passed (retry/change-deck/no-advance/preserve-question) | ✓ PASS |
| card_draw uses CSPRNG not random          | grep `import random\|random.shuffle\|random.random` in card_draw.py    | no matches; `secrets.SystemRandom` present | ✓ PASS |
| llm aliases not dated snapshots           | grep `-20\d{6}\|-19\d{6}` in llm.py                                    | no matches; aliases present     | ✓ PASS |
| Live backend integration (5 files)        | requires Docker/Postgres                                                | SKIPPED (no PG on Windows host) | ? SKIP → human (item 2/3) |

The 49 backend skips are the established Phase-1/2/3 convention: integration tests + DB-touching draw tests skip cleanly when Postgres is unreachable. The 04-05-SUMMARY documents that the full orchestration + HTTP path were additionally exercised against an ephemeral in-memory SQLite shim (all paths passed) as offline confidence; that scaffolding was not committed. Live-PG confirmation is rolled into the human items.

### Probe Execution

No probe convention exists in this project (`find scripts -path '*/tests/probe-*.sh'` → none; no probe references in PLAN/SUMMARY). N/A for this phase.

### Requirements Coverage

Union of all 6 plans' `requirements` frontmatter == the 14 ROADMAP Phase-4 IDs exactly. No orphaned requirements (every ROADMAP Phase-4 ID is claimed by ≥1 plan; SUMMARY `requirements-completed` matches).

| Requirement   | Source Plan(s)        | Description                                                        | Status      | Evidence                                                                 |
| ------------- | --------------------- | ----------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------ |
| READ-01       | 04-05, 04-06          | POST /api/readings after limit check                              | ✓ SATISFIED | `api/readings.py` + `createReading.ts`; `test_readings_auth.py` 401/422/200/JWT. |
| READ-02       | 04-02                 | Backend CSPRNG draw; reversals off→upright, on→70/30              | ✓ SATISFIED | `card_draw.py`; `test_card_draw.py` 5/5.                                  |
| READ-03       | 04-01/03/04/05        | One structured LLM call validated by schema                       | ✓ SATISFIED | `llm.py` single `messages.parse(output_format=ReadingOutput)`.           |
| READ-04       | 04-03, 04-05          | Invalid JSON → one retry; timeout/fail → failed, limit not spent  | ✓ SATISFIED | `llm.py` retry + `reading.py._honest_fail`; `test_llm_service.py`.        |
| READ-05       | 04-01/04/05           | Per-card: name, position, orientation, short, deep, deck accent   | ✓ SATISFIED | `CardInterpretation` + `ReadingCardOut`; persisted authoritative fields. |
| READ-06       | 04-01/04/05           | Summary: linkage, main factor, attention, soft advice, closing    | ✓ SATISFIED | `ReadingSummary` (6 fields) + `ReadingSummaryOut` (5 fields).            |
| READ-10       | 04-05                 | Limit consumed only on success                                    | ✓ SATISFIED | `_consume_limit` called once (line 252); every non-success exit skips it.|
| READ-11       | 04-02/04/05/06        | Tone matches deck + brand (no AI words)                           | ✓ SATISFIED | per-deck modifier+signature; backend + frontend brand guards.            |
| SAFE-01       | 04-01/03/05           | Pre-generation classify gates generation                          | ✓ SATISFIED | `safety.py` regex + Haiku classify; gate in `reading.py`.                |
| SAFE-02       | 04-03/04/05           | normal→generate; sensitive→safety modifier                       | ✓ SATISFIED | `route()` SAFETY_MODIFIER; `prompt_engine` appends §20.3 fragment.       |
| SAFE-03       | 04-04/05              | Crisis → supportive safe response, not prediction                 | ✓ SATISFIED | REFUSAL short-circuit + generic refusal copy; `test_safety_gate.py`.     |
| SAFE-04       | 04-02/03/04           | No categorical/fatalistic predictions                             | ✓ SATISFIED | §16/§15.1 bans in system+single_card templates; brand guard.            |
| SAFE-05       | 04-02/03/04           | Allowed soft formulations used                                    | ✓ SATISFIED | Deck modifiers use «может указывать/подсвечивает»; safety fragment.      |
| ANALYTICS-02  | 04-05                 | generation_logs writes version/model/tokens/latency/status/error | ✓ SATISFIED | `GenerationLog` + one row per actual LLM call; `test_generation_logs.py`.|

SAFE-06 (brand-voice ban in UI) is mapped to Phase 3 in REQUIREMENTS.md; the Phase-4 work ports it as a backend output guard (`brand_guard.py`) and reuses it — consistent, not an orphan.

### Anti-Patterns Found

| File                  | Line | Pattern                          | Severity | Impact                                                                                          |
| --------------------- | ---- | -------------------------------- | -------- | ----------------------------------------------------------------------------------------------- |
| (none)                | —    | TODO/FIXME/XXX/HACK/PLACEHOLDER  | —        | grep across `app/services` → none. "templated/stand-in reading" appears only in docstrings asserting the D-09 NO-fallback behaviour. |

No debt markers, no stub returns, no empty implementations in any Phase-4 module. Two documented "deviations" in 04-05-SUMMARY (conftest `deck_cards` synthesis; 1-based `position_index` test hardening) are test-substrate fixes, not production-code defects — production code was correct. 04-06 notes orphaned Phase-3 mock fixtures (`cardPool.fixture.ts`, unused `copy.ts` constants) as optional cleanup (INFO only — they do not affect the goal and the suite is green with them present).

### Human Verification Required

Four LIVE UAT checks require a running stack + a real `ANTHROPIC_API_KEY` (unavailable to the verifier). These are deferred-to-human by explicit user approval recorded in 04-06-SUMMARY.md (Task 3, `checkpoint:human-verify`), mirroring how Phases 2-3 closed.

#### 1. Per-deck divergence (Core Value, READ-11 / TZ §30)

**Test:** With the backend running + a real key, submit the SAME question on 2-3 decks (e.g. Тени, Сердце, Лесной).
**Expected:** Noticeably different tone AND focus, a recognizable per-deck signature in each (D-02); no result text contains "AI / нейросеть / модель / ИИ".
**Why human:** The felt quality of divergence is the MVP north-star and is subjective — it cannot be asserted programmatically.

#### 2. Live-API smoke (READ-03/05/06)

**Test:** Set `ANTHROPIC_API_KEY`, run the env-gated live smoke across the 6 decks / 7 spreads.
**Expected:** A schema-valid `ReadingOutput` returns for each with plausible Russian copy (D-14).
**Why human:** The automated suite mocks the LLM; the live contract holding needs a real Anthropic call.

#### 3. Ritual + failure UX (D-07 / D-08)

**Test:** In the Mini App trigger a normal reading; then force a failure (bad key / induced timeout).
**Expected:** The ~3s ritual covers the real wait with NO spinner; reveal happens only after JSON is ready; on failure «Колода замолчала…» + Повторить + Сменить колоду (question preserved) and the limit is NOT consumed.
**Why human:** Perceived real-time latency and in-Telegram feel require a running stack + a human.

#### 4. Crisis tone (SAFE-03)

**Test:** Submit a crisis-style question against the live stack.
**Expected:** A warm, human, supportive response that fully breaks the mystical frame, points to a real person/specialist (generic, no phone — D-04), with NO cards drawn and NO charge.
**Why human:** The empathy/tone quality of the refusal is subjective; the no-draw/no-charge short-circuit is code-verified, but the felt supportiveness needs a human.

### Gaps Summary

No gaps. Every must-have is verified in source, every locked invariant holds, every ROADMAP Phase-4 requirement is satisfied with code evidence, and both unit suites are green (backend 82 passed / 0 fail; frontend 80 passed / 0 fail). The phase is code-complete and the Core Value is wired end-to-end (Mini App → POST /api/readings → gate→draw→one structured call→persist → unchanged ritual/reveal/result UI). Status is `human_needed` solely because the four subjective live-stack checks require a real API key + running stack and were deferred to a human by user approval — not because anything is missing or wrong in the code.

---

_Verified: 2026-06-13T23:18:00Z_
_Verifier: Claude (gsd-verifier)_
