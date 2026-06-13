# Phase 4: Real Personal Reading (KEYSTONE) - Research

**Researched:** 2026-06-12
**Domain:** Anthropic Structured Outputs (single-call schema generation) + safety gating + resilient synchronous LLM service inside an async FastAPI service layer
**Confidence:** HIGH (SDK API + schema constraints verified against installed `anthropic==0.109.1` source and official docs; DB schema, TZ prompts, and codebase seams read directly)

## Summary

This phase wires the real generation engine under the existing Phase-3 ritual UI. The technical core is **one** `client.messages.parse()` call that returns every card interpretation + the summary as a single schema-validated Pydantic object, fronted by a mandatory safety gate that short-circuits crisis questions *before* any card draw or limit charge, and wrapped in a tight resilience contract (one corrective retry → timeout → honest fail, limit never consumed on failure).

The three open questions flagged in STATE.md are now resolvable concretely. (1) **Single-call schema** — define a `ReadingOutput` Pydantic model with a variable-length `cards: list[CardInterpretation]` plus a flat `summary: ReadingSummary`; the SDK builds the JSON schema from it via `TypeAdapter`, and constrained decoding guarantees a schema-valid object on a clean `end_turn`. (2) **Safety classifier** — the cleanest approach that honors "gate BEFORE draw/charge" + crisis short-circuit is a **regex pre-filter → tiny Haiku classify call returning a `SafetyVerdict` enum** (also via `messages.parse`); it runs before `CardDrawService`, costs a fraction of a cent, and the 7 TZ §20.4 categories map directly onto a Python `StrEnum`. (3) **Retry/timeout/fallback** — `tenacity` retries exactly once on `pydantic.ValidationError` / `anthropic.APIStatusError` / timeout, escalating Haiku→Sonnet on the retry (D-12); on total failure the reading is marked `failed`, the soft §9.8 copy is returned, and the limit is not decremented (D-09).

Critical verified facts: `messages.parse` is **GA — no beta header**; `output_format=PydanticModel` is accepted directly and translated to `output_config.format`; the typed result is on `response.parsed_output`; **`minLength`/`maxLength` constraints are stripped from the schema before sending** (constrained decoding cannot enforce the §17 `≤140` char limit — that must live in the prompt + a post-validation guard); usage is on `response.usage.input_tokens/output_tokens`; refusal/truncation surface as `stop_reason in {"refusal","max_tokens"}` and may yield non-schema output.

**Primary recommendation:** Build four thin services behind the existing `catalog.py` pattern — `CardDrawService` (CSPRNG via `secrets`), `PromptEngine` (assembles versioned `prompt_templates` into system + user blocks), `LLMService` (the swappable `messages.parse` wrapper with tenacity + usage extraction), and a `SafetyService` (regex + Haiku classify) — composed inside `ReadingService.create_reading()`, which owns the transaction, the gate-before-draw ordering, the `generation_logs` write, and the honest-fail path. Add `anthropic` and `tenacity` to `pyproject.toml` (both currently MISSING) behind a human-verify checkpoint.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions (research the HOW, never propose alternatives)

**Per-deck divergence (Core Value):**
- **D-01:** Divergence = **tone + focus** (deck changes what the reading concentrates on; structure/format stays uniform — see D-11). Source modifiers: TZ §19.1–19.6, already seeded as per-deck `prompt_modifier`; `deck_modifier` template type exists.
- **D-02:** Each deck has a **mandatory signature** — a guaranteed device present in *every* reading even on similar questions (Лесной → always a nature metaphor; Тени → always names a hidden tension/repeating pattern). Difference is guaranteed, not emergent. Exact per-deck signature wording is planner's to derive from §19; the requirement "a visible signature in every reading" is locked.

**Safety:**
- **D-03:** **Crisis** (`crisis_sensitive`: self-harm/violence) → fully break the mystical frame; warm direct human tone; **no cards, no prediction, no reading**. Via template type `refusal`. Short-circuits **before** draw/charge (LOCKED). Limit not consumed.
- **D-04:** Crisis resources → **generic wording, no specific phone numbers**: "обратись к близкому человеку, которому доверяешь, или к специалисту."
- **D-05:** **Sensitive** (`relationship_/financial_/health_/legal_sensitive`) → **silent softening**: a `safety_modifier` added to the prompt; gentler text, **no visible disclaimer/badge** in UI.
- **D-06:** **Abusive/manipulative/junk** (`abusive_or_manipulative`, not crisis) → **gentle in-character redirect**: "колода молчит на это, задай вопрос от сердца." No reading, no draw, limit not consumed.

**Generation wait & failure UX:**
- **D-07:** The real LLM call is **covered by the ritual**; fires on «Начать расклад», ~3s ritual plays during the wait, reveal happens only once schema-valid JSON is ready; if slow the last ritual beat holds/loops softly — **no spinner**. (`createReading()` seam becomes the async `POST /api/readings`.)
- **D-08:** On generation failure (after the one corrective retry): «колода замолчала» offers **Повторить** (same reading) **+ Сменить колоду** (back to selection, question preserved). Error copy: TZ §9.8. Limit not consumed → retry is free.
- **D-09:** "DB-fallback" is resolved as an **honest fail, NOT a templated reading**: on total failure `reading=failed`, soft in-character error, limit **NOT** consumed, **no** stand-in reading from base meanings.

**Reading depth & length:**
- **D-10:** Depth = **short/atmospheric**. `short_meaning` ~1 line (≤140 chars per §17), `interpretation` ~2–3 sentences, tight summary.
- **D-11:** Length is **uniform across all 6 decks**. Differentiation = tone/focus/signature, not volume.

**Model & generation behavior:**
- **D-12:** Sonnet escalates **only on the corrective retry** when Haiku returns invalid JSON (Haiku is the default). Per-deck/per-tier premium escalation is post-MVP.
- **D-13:** Reversals default for a new user = **on, 70/30** (`reversals_enabled=True`). The value arrives in the request; settings persistence is Phase 5.
- **D-14:** Reading language is **always Russian**, regardless of the question's language.

### Claude's Discretion (delegated to research + planner)
- **Safety-classifier mechanism** — separate cheap classify call vs regex pre-filter + a `safety` field in structured output vs classification inside the main call. Product invariant is locked (crisis short-circuits *before* draw/charge); the HOW is for research/planner. **→ This research recommends: regex pre-filter + tiny Haiku classify call (see Architecture Pattern 2).**
- **Single-call JSON schema design** — merging §17 + §18 into one valid `messages.parse` object and mapping onto the DB schema. **→ Recommended concrete schema + mapping in Architecture Pattern 1.**
- Concrete per-deck signature texts, `safety_modifier` text, `refusal` copy — planner from §16/§17/§18/§19/§20.3 + §9.8.
- Exact retry/timeout timings and temperature — planner (this research gives a concrete starting config).

### Deferred Ideas (OUT OF SCOPE — do not build)
- Concrete regional crisis hotline numbers (generic wording for MVP, D-04).
- Per-deck/premium-tier model escalation (Haiku default + Sonnet only on retry, D-12).
- Visible sensitive-topic disclaimer UI (silent softening, D-05).
- History-based personalization (`allow_history_personalization`, `history_context` in §18) — Phase 5; Phase 4 passes it through but does not build the path.
- Weekly-limit reset, buckets, atomic decrement, Redis throttle — Phase 6. Phase 4 only needs "limit consumed on success, not on failure" (READ-10).
- `app_events` reading_started/completed/failed analytics — Phase 8. Phase 4 writes `generation_logs` only (ANALYTICS-02).
- Reduced-motion fallback — Phase 3 D-10.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| READ-01 | `POST /api/readings` (question, topic, deck, spread, reversals) after limit check | `ReadingService.create_reading()` orchestration; router mirrors `decks.py`; request schema mirrors §14.5 |
| READ-02 | Cards drawn on backend with CSPRNG; orientation off→upright, on→70/30; seed/debug_hash saved hidden | `CardDrawService` using `secrets.SystemRandom().shuffle`; orientation per §12.5; hash stored, not in response (Pattern 3) |
| READ-03 | pending→generating; all cards + summary via **one** `messages.parse`, validated by JSON schema | Single `ReadingOutput` Pydantic model; constrained decoding guarantees schema-valid on `end_turn` (Pattern 1) |
| READ-04 | Invalid JSON → one corrective retry; timeout/fail → reading=failed, limit not consumed, soft error | tenacity 1-retry on `ValidationError`/`APIStatusError`/timeout; honest-fail path (Pattern 4) |
| READ-05 | Card interpretation: name, position, orientation, short meaning, deep interpretation, deck mystical accent | `CardInterpretation` sub-model → `reading_cards` columns; deck accent from §17 `mystical_accent` (Pattern 1 mapping) |
| READ-06 | Summary: card linkage, main factor, attention point, soft advice, closing phrase in deck style | `ReadingSummary` sub-model → `readings` columns + JSON-serialized overflow fields (Pattern 1 mapping) |
| READ-10 | Limit consumed only on successful reading creation | Decrement inside the success branch of `create_reading()`, after persist, before commit; never in failure/safety-block branches |
| READ-11 | Result tone/wording matches deck (prompt-modifier) and brand (no AI/нейросеть/модель) | PromptEngine injects `deck_modifier` + signature (D-02); post-validation brand guard reusing SAFE-06 ban-list |
| SAFE-01 | Pre-generation classification (regex pre-filter + classify) gating generation | `SafetyService.classify()` → regex pre-filter then Haiku classify into `SafetyCategory` enum (Pattern 2) |
| SAFE-02 | normal → normal generation; sensitive → safety_modifier added to prompt | PromptEngine conditionally appends the `safety` template fragment (Pattern 2 routing) |
| SAFE-03 | crisis → NOT mystical prediction; supportive safe answer + suggestion to seek a live specialist | `refusal` template, returned before draw/charge; generic resources per D-04 |
| SAFE-04 | Banned: categorical predictions, asserting another's feelings as fact, med/legal/fin advice, fatalistic phrasing | Encoded in system prompt §16 + §15.1 ban-list; post-validation guard can flag obvious violations |
| SAFE-05 | Use allowed soft formulations ("карты указывают/подсвечивают/возможное направление/не приговор") | System prompt §16 allow-list; tone enforced by prompt, not code |
| ANALYTICS-02 | `generation_logs` writes prompt_version, model, tokens, latency, status, error per generation | One `GenerationLog` row per LLM call (incl. the classify call + each generation attempt); fields map 1:1 (Pattern 1 logging) |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Card selection (CSPRNG) | API / Backend | — | TZ §12.4 + §29.2 + PROJECT: backend-only, forgeable on client; `secrets` not `random` |
| Limit check + decrement | API / Backend | Database (PG authoritative) | §29.2 backend-only; Phase 4 reads/decrements, Phase 6 owns reset/buckets |
| Safety classification | API / Backend | LLM (Anthropic) | Must gate before draw/charge; runs server-side inside `ReadingService` |
| Prompt assembly | API / Backend | Database (`prompt_templates`) | Versioned fragments composed server-side; `prompt_version` logged |
| LLM generation (one call) | LLM (Anthropic) | API / Backend (orchestration) | `messages.parse`; backend validates + persists + logs |
| Persistence (`readings`/`reading_cards`/`generation_logs`) | Database | API / Backend | Locked schema from Phase 1; immutable card rows |
| Reveal/result rendering | Browser / Client | Frontend Server (none — SPA) | Phase 3 UI unchanged; only the data-source seam swaps |
| Generation-wait UX (ritual cover) | Browser / Client | — | D-07: ritual covers latency; reveal awaits the promise; no spinner |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | `0.109.1` (floor `>=0.69`) `[VERIFIED: PyPI + installed source]` | Claude API client; `messages.parse` Structured Outputs | Locked provider (CLAUDE.md). `messages.parse` + `output_format=PydanticModel` confirmed present in installed 0.109.1 source. **Currently MISSING from `backend/pyproject.toml` — must be added.** |
| `tenacity` | `9.1.4` (floor `>=9`) `[VERIFIED: PyPI]` | Bounded retry + per-attempt timeout around the single LLM call | CLAUDE.md-locked "tenacity retry+timeout"; replaces a queue (edit #2). **Currently MISSING — must be added.** |
| Claude Haiku 4.5 | model id `claude-haiku-4-5` `[CITED: CLAUDE.md / platform.claude.com pricing]` | Default generation + classify model | $1/$5 per MTok; ~$0.01/reading; Structured Outputs supported `[CITED: structured-outputs doc]` |
| Claude Sonnet 4.6 | model id `claude-sonnet-4-6` `[CITED: CLAUDE.md]` | Corrective-retry escalation ONLY (D-12) | $3/$15 per MTok; used only when Haiku output fails validation |

### Supporting (already present)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pydantic` | `2.13.*` `[VERIFIED: pyproject]` | The `ReadingOutput` / `SafetyVerdict` schemas + request/response models | Output schema for `messages.parse`; `validate_json` raises `ValidationError` on mismatch → retry trigger |
| `sqlalchemy[asyncio]` | `2.0.*` `[VERIFIED: pyproject]` | Persist readings/cards/logs; decrement limit | `AsyncSession`, `select()`, `Mapped[]` — mirror `catalog.py` |
| `redis[hiredis]` | `>=5.2,<6` `[VERIFIED: pyproject]` | (Phase 4: optional) base-card-meaning cache | Not required for the slice; PROJECT lists it as a cache, not a dependency. Keep PG reads simple for MVP. |
| `pytest` + `pytest-asyncio` + `httpx` | `>=8` / `>=0.24` / `>=0.28` `[VERIFIED: pyproject]` | Unit + integration tests with mocked `LLMService` | `asyncio_mode = "auto"` already set; ASGITransport client fixture exists |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `messages.parse` (Structured Outputs GA) | Strict tool use (`tools=[...]`, `tool_choice`) | Tool use works on models lacking SO; SO is simpler, GA, and Haiku 4.5 supports it. CLAUDE.md says **never** prompt-and-`json.loads`. Use `messages.parse`. |
| Separate Haiku classify call (recommended) | One combined call with a `safety` field in `ReadingOutput` | A combined call **cannot** satisfy "gate BEFORE draw/charge" for crisis — the cards are already drawn and the expensive generation already charged by the time you read the field. Separate pre-call is the only design that honors D-03's ordering. |
| `tenacity` decorator | Hand-rolled `for attempt in range(2)` loop | tenacity is locked (CLAUDE.md) and gives clean retry-on-exception-type + stop-after-attempt + wait policy. Use it. |

**Installation (add to `backend/pyproject.toml` `[project].dependencies`):**
```toml
# LLM client + resilience — Phase 4 (KEYSTONE). github.com/anthropics/anthropic-sdk-python
"anthropic>=0.69,<1",
"tenacity>=9,<10",
```
Run behind a `checkpoint:human-verify` task before install (see Package Legitimacy Audit). After adding, also add `"test-anthropic-key"` is already wired in `tests/conftest.py` so config import stays green.

**Version verification performed:**
- `anthropic`: PyPI latest `0.109.1` (verified via `pip index versions`); `messages.parse` + `output_format` + `parsed_output` confirmed in installed source at `anthropic/resources/messages/messages.py:1159` and `anthropic/types/parsed_message.py`.
- `tenacity`: PyPI latest `9.1.4` (verified). Established library, no concerns.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `anthropic` | PyPI | ~3 yrs (since 2023) | very high (official SDK) | github.com/anthropics/anthropic-sdk-python | [OK] | Approved — planner adds `checkpoint:human-verify` before the pyproject edit (consistency with Phase-1 aiogram precedent) |
| `tenacity` | PyPI | ~8 yrs | very high (industry standard) | github.com/jd/tenacity | [OK] | Approved — same checkpoint |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

slopcheck `0.6.1` ran `slopcheck install anthropic tenacity` → both reported `[OK] (pypi)`. Both are also already resolvable in the local environment (anthropic 0.109.1, tenacity 9.1.4) and `anthropic` is the locked provider in CLAUDE.md, so these are `[VERIFIED]`, not `[ASSUMED]`. Per the Phase-1 aiogram precedent (pyproject comment), the planner should still gate the dependency edit behind a human checkpoint so the lock is established once and stays consistent.

## Architecture Patterns

### System Architecture Diagram

```
POST /api/readings  (Bearer JWT, get_current_user)
        │  body: {question, topic, deck_slug, spread_slug, reversals_enabled}
        ▼
┌─────────────────────────── ReadingService.create_reading() ───────────────────────────┐
│ (owns the AsyncSession transaction + ordering + generation_logs + honest-fail)         │
│                                                                                         │
│  1. limit check ──► LimitService.has_quota(user)                                        │
│        │ no quota ──────────────────────────────────► 200 {soft paywall §9.8} (no draw) │
│        ▼ has quota                                                                       │
│  2. SAFETY GATE (BEFORE draw/charge) ──► SafetyService.classify(question)               │
│        │                                    │ regex pre-filter (cheap)                   │
│        │                                    ▼ Haiku classify (messages.parse → enum)     │
│        │                              writes generation_logs(status='classify')          │
│        ├─ crisis_sensitive ──► refusal template ──► 200 {refusal copy} (NO draw,        │
│        │                                              NO generation, limit NOT consumed)  │
│        ├─ abusive_or_manipulative ──► redirect copy ──► 200 (NO draw, limit NOT consumed)│
│        ├─ *_sensitive ──► set safety_modifier flag, continue                             │
│        └─ normal ──► continue                                                            │
│        ▼                                                                                  │
│  3. CardDrawService.draw(deck, spread, reversals_enabled)                               │
│        │ secrets.SystemRandom().shuffle → N cards → orientation 70/30                    │
│        ▼ persist readings(status='pending') + reading_cards (immutable) + seed hash      │
│  4. PromptEngine.build(reading, cards, deck, spread, safety_modifier?)                  │
│        │ assemble system (§16) + deck_modifier (§19) + signature (D-02)                  │
│        │ + per-card position context (§17) + summary instruction (§18) + safety (§20.3)  │
│        ▼ resolves prompt_version from active prompt_templates                            │
│  5. status → 'generating' ; LLMService.generate(prompt, ReadingOutput)                  │
│        │  ONE messages.parse (Haiku) ──► response.parsed_output : ReadingOutput          │
│        │     ├─ ValidationError / APIStatusError / timeout ──► tenacity retry #1 on      │
│        │     │     SONNET (D-12) ─────────────────────────────────────────┐              │
│        │     │                                                            ▼              │
│        │     │                                              still fails ──► honest fail   │
│        │     │                                              reading='failed', limit kept, │
│        │     │                                              200 {§9.8 retry copy} (D-08/09)│
│        │     └─ each attempt writes generation_logs(model, tokens, latency, status, err) │
│        ▼ success                                                                          │
│  6. brand guard (SAFE-06 ban-list) on generated text ─► (flag/log if violated)          │
│  7. persist interpretations onto reading_cards + summary onto readings; status='completed'│
│  8. LimitService.consume(user)   ◄── ONLY here (READ-10)                                 │
│  9. commit                                                                               │
└─────────────────────────────────────────────────────────────────────────────────────────┘
        ▼
  200 {reading_id, status, selected_cards, interpretations, summary, remaining_limits}
        ▼
Frontend: createReading() seam now awaits POST; ritual covers the wait (D-07);
          reveal renders only after schema-valid JSON; failure → Повторить + Сменить колоду (D-08)
```

### Recommended Project Structure
```
backend/app/
├── schemas/
│   └── reading.py        # ReadingCreate (request §14.5), ReadingOut (response),
│                         # + LLM output models: ReadingOutput / CardInterpretation /
│                         #   ReadingSummary, and SafetyVerdict (classify output)
├── services/
│   ├── reading.py        # ReadingService — orchestration, transaction, ordering, logs
│   ├── card_draw.py      # CardDrawService — secrets-based shuffle + orientation
│   ├── prompt_engine.py  # PromptEngine — compose versioned prompt_templates
│   ├── llm.py            # LLMService — messages.parse wrapper + tenacity + usage extract
│   └── safety.py         # SafetyService — regex pre-filter + Haiku classify
├── core/
│   └── llm_client.py     # module-level anthropic.AsyncAnthropic() singleton (reads ANTHROPIC_API_KEY)
└── api/
    └── readings.py       # thin router (mirrors decks.py); mounts in api/__init__.py + main.py
```

### Pattern 1: Single-call `ReadingOutput` schema + DB mapping (resolves Open Question 1)

**What:** ONE Pydantic model passed to `messages.parse(output_format=ReadingOutput)`. A variable-length `cards` list (3–4 per spread) plus a flat summary. Constrained decoding guarantees schema-validity on a clean `end_turn`.

**Verified constraints driving the design** `[CITED: platform.claude.com/docs/en/build-with-claude/structured-outputs]`:
- `list[NestedModel]` of variable length IS supported (only `minItems` 0/1 honored).
- **`minLength`/`maxLength` are STRIPPED from the schema sent to the API** (the SDK transforms them to descriptions and re-validates on the response). So the §17 `short_meaning ≤140` cannot be enforced by constrained decoding — put "до 140 символов" in the field description + prompt, and add a post-validation length guard.
- All non-nullable fields are required by default; use `X | None` for optional.
- Budget limits: ≤24 optional params and ≤16 union-type params total across the schema. This design uses **zero** optional fields and zero unions → comfortably within budget.
- `enum` supported (used by the classify schema, Pattern 2).

```python
# schemas/reading.py — the LLM output contract (fused §17 + §18). Field descriptions are
# load-bearing: with minLength/maxLength stripped, the description is how the model learns
# the length target. Mirror the DB columns so persistence is mechanical.
from pydantic import BaseModel, Field

class CardInterpretation(BaseModel):
    position_index: int = Field(description="0-based slot index, must match the drawn card order")
    short_meaning: str = Field(description="1 короткое предложение, до 140 символов")   # → reading_cards.short_meaning
    interpretation: str = Field(description="2–3 коротких предложения под вопрос")        # → reading_cards.interpretation
    mystical_accent: str = Field(description="1 атмосферная фраза в стиле колоды (deck signature, D-02)")  # → reading_cards.mystical_accent
    soft_advice: str = Field(description="1 мягкий совет без давления")                   # → NO dedicated column (see mapping)

class ReadingSummary(BaseModel):
    summary_short: str = Field(description="короткий итог в 1–2 предложения")             # → readings.summary_short
    connection: str = Field(description="как карты связаны между собой")                  # → readings.summary_full (or JSON)
    main_factor: str = Field(description="главный фактор ситуации")                        # → readings.main_factor
    attention_point: str = Field(description="на что обратить внимание")                   # → NO dedicated column
    advice: str = Field(description="мягкий совет без давления")                           # → readings.advice
    closing_phrase: str = Field(description="атмосферная завершающая фраза в стиле колоды") # → NO dedicated column

class ReadingOutput(BaseModel):
    cards: list[CardInterpretation] = Field(description="ровно по одной на каждую выпавшую карту, в порядке позиций")
    summary: ReadingSummary
```

**Field-count mismatch — concrete recommended mapping.** Three §17/§18 fields have no dedicated DB column (`soft_advice`, `attention_point`, `closing_phrase`; `connection` overlaps with `summary_full`). The locked schema (Phase 1) must not change. Recommended resolution — **do not drop these fields** (they are part of READ-05/06 and the felt quality), persist the overflow as structured JSON inside the existing wide `String` columns:

| LLM field | DB target | Storage strategy |
|-----------|-----------|------------------|
| `CardInterpretation.short_meaning` | `reading_cards.short_meaning` | direct |
| `CardInterpretation.interpretation` | `reading_cards.interpretation` | direct |
| `CardInterpretation.mystical_accent` | `reading_cards.mystical_accent` | direct |
| `CardInterpretation.soft_advice` | — | **Recommended:** append into `reading_cards.interpretation` as a final sentence, OR fold into `mystical_accent`. (No JSON column on `reading_cards`.) Planner decides; appending to `interpretation` keeps it visible on the result screen with zero schema change. |
| `ReadingSummary.summary_short` | `readings.summary_short` | direct |
| `ReadingSummary.main_factor` | `readings.main_factor` | direct |
| `ReadingSummary.advice` | `readings.advice` | direct |
| `ReadingSummary.connection` + `attention_point` + `closing_phrase` | `readings.summary_full` | **Recommended:** serialize the full `ReadingSummary` object to a JSON string into `summary_full` (it is a wide `String`/TEXT). This preserves every §18 field losslessly for the result screen + future history, while `summary_short`/`main_factor`/`advice` stay denormalized for cheap list/preview queries (Phase 5 history). |

This mapping is **lossless** (every §18 field survives), needs **no migration**, and matches the existing frontend `MockReadingSummary` shape (`linkage`/`mainFactor`/`attention`/`softAdvice`/`closingPhrase`) so the response schema can carry all five summary fields the result UI already renders. Flag in the Assumptions Log — the planner/discuss may prefer a leaner mapping, but this one is the safe default.

**Response schema (`ReadingOut`)** must include the full per-card fields + all five summary fields so the frontend result screen (already built) gets everything it renders, plus `reading_id`, `status`, `remaining_limits` (§14.5). Drawn cards' `name`/`position`/`orientation` come from the persisted `reading_cards` join (the model is not asked to echo card names — it gets `position_index` only, names are authoritative server-side).

### Pattern 2: Safety gate — regex pre-filter + tiny Haiku classify (resolves Open Question 2)

**What:** A two-stage `SafetyService.classify(question) -> SafetyCategory` that runs **before** `CardDrawService`. Resolves the PROJECT.md tension ("классификация внутри основного вызова" vs "гейтит до draw/charge") decisively in favor of a separate pre-call — because only a pre-call can short-circuit crisis *before* the cards are drawn and the expensive generation is charged (D-03 is LOCKED on this ordering).

**Why not a `safety` field in the main `ReadingOutput`:** by the time you can read that field, the draw has happened and the full generation has already run and been charged. That violates D-03 ("short-circuits before draw/charge") and wastes the expensive call on crisis questions. Rejected.

**Stage 1 — regex pre-filter (free, instant):** SAFE-01 explicitly says "regex-префильтр + классификация". A small RU/EN keyword regex catches the highest-signal crisis terms (self-harm, suicide, violence) for an instant `crisis_sensitive` short-circuit with zero API cost/latency, and can fast-path obvious `normal`. Empty question (HOME-02) → `normal` without any call.

**Stage 2 — Haiku classify call** for anything the regex doesn't decisively resolve: a second `messages.parse` with a tiny enum-only output schema. Maps directly onto TZ §20.4's 7 categories:

```python
import enum
from pydantic import BaseModel

class SafetyCategory(enum.StrEnum):           # exact TZ §20.4 set
    NORMAL = "normal"
    RELATIONSHIP_SENSITIVE = "relationship_sensitive"
    FINANCIAL_SENSITIVE = "financial_sensitive"
    HEALTH_SENSITIVE = "health_sensitive"
    LEGAL_SENSITIVE = "legal_sensitive"
    CRISIS_SENSITIVE = "crisis_sensitive"
    ABUSIVE_OR_MANIPULATIVE = "abusive_or_manipulative"

class SafetyVerdict(BaseModel):
    category: SafetyCategory                  # enum → constrained decoding guarantees a valid member
```

**Routing (D-03/04/05/06):**
- `crisis_sensitive` → `refusal` template (D-03/04), no draw, no generation, limit kept.
- `abusive_or_manipulative` → in-character redirect (D-06), no draw, limit kept.
- any `*_sensitive` → continue, but PromptEngine appends the `safety` template fragment (`safety_modifier`, §20.3) → silent softening (D-05, no UI badge).
- `normal` → normal generation.

**Cost/latency:** the classify call is ~150–400 input tokens + a single-enum output (a few tokens). At Haiku pricing this is a fraction of a cent (<<$0.001) and typically 300–700ms. It is logged to `generation_logs` (status e.g. `classify`) like every other LLM call (ANALYTICS-02). The regex pre-filter removes the API round-trip entirely for the clearest cases. This is the cheapest design that still satisfies the locked invariant. `[ASSUMED: latency/token figures are estimates from Haiku pricing + prompt size, not measured this session.]`

**Anti-pattern rejected:** doing classification *inside* the generation call. Only viable if D-03's ordering were not locked — it is.

### Pattern 3: CSPRNG card draw (READ-02, §12.4/§12.5)

**What:** `CardDrawService.draw()` — backend-only, cryptographically secure.

```python
import secrets
_rng = secrets.SystemRandom()  # CSPRNG — NEVER `random` (CLAUDE.md anti-pattern; §12.5)

def draw(deck_card_ids: list, position_count: int, reversals_enabled: bool):
    pool = list(deck_card_ids)
    _rng.shuffle(pool)                          # cryptographically secure shuffle
    chosen = pool[:position_count]              # N by positions
    for slot in chosen:
        if not reversals_enabled:
            orientation = "upright"             # off → always upright
        else:
            orientation = "reversed" if _rng.random() < 0.30 else "upright"  # 70/30
    # persist a hidden seed/debug_hash on the reading; NEVER return it (Pattern: not in response)
```
- Draw from the **active deck's** `deck_cards` (the style layer pins which (deck,card) rows exist); join `cards` for the universal meaning the prompt needs.
- `seed/debug_hash` saved hidden (§12.5). The locked `readings` model has **no** dedicated seed column — store the debug hash in an existing field is not ideal; **recommend** the planner logs the draw seed into `generation_logs.error`-adjacent context or accepts that the per-reading reproducibility hash is out of MVP scope (flag in Open Questions). The orientation/card rows themselves are persisted in `reading_cards` (immutable), which is the durable record.
- `reading_cards` rows are written **before** generation (status `pending`), so even a failed generation has the draw recorded — but D-09 says a failed reading is `failed` and the limit is kept; the drawn rows for a failed reading simply remain attached to a `failed` reading (not shown to the user).

### Pattern 4: Resilience contract — tenacity 1-retry + timeout + honest fail (resolves Open Question 3)

**What:** `LLMService.generate()` wraps the single `messages.parse` with exactly one corrective retry that escalates Haiku→Sonnet, a per-attempt timeout, and surfaces total failure as an exception `ReadingService` turns into the honest-fail path.

**How validation failures surface (verified):** `response.parsed_output` is produced by `TypeAdapter(ReadingOutput).validate_json(text)` (`anthropic/lib/_parse/_response.py:19`). On a schema mismatch this raises `pydantic.ValidationError`. With constrained decoding a clean `stop_reason="end_turn"` should always validate; the realistic failure modes are `stop_reason in {"refusal","max_tokens"}` (output may not match schema → `ValidationError` on access) and transient `anthropic.APIStatusError`/`APIConnectionError`/timeout.

```python
import anthropic
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

RETRYABLE = (ValidationError, anthropic.APIStatusError, anthropic.APIConnectionError, TimeoutError)

# One corrective attempt total = 2 tries. Attempt 1 = Haiku; attempt 2 (retry) = Sonnet (D-12).
# Model choice keys off the attempt number — pass it via the retry state or a small wrapper.
@retry(
    stop=stop_after_attempt(2),
    wait=wait_fixed(0.5),
    retry=retry_if_exception_type(RETRYABLE),
    reraise=True,                 # final failure re-raises the real exception
)
def _call(model: str, ...): ...

# messages.parse takes a per-call timeout kwarg (verified in messages.py:1183 signature):
response = client.messages.parse(
    model=model, max_tokens=..., system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}],
    output_format=ReadingOutput,
    temperature=0.7,              # planner tunes; lower = steadier JSON, higher = more atmosphere
    timeout=20.0,                 # per-attempt wall clock; ritual covers ~3s, holds if slower (D-07)
)
result: ReadingOutput = response.parsed_output     # raises ValidationError if schema mismatch
in_tok, out_tok = response.usage.input_tokens, response.usage.output_tokens
```

**Concrete starting config (planner may tune):** `stop_after_attempt(2)`, `wait_fixed(0.5)`, per-attempt `timeout=20.0s`, Haiku then Sonnet, `temperature≈0.7`, `max_tokens≈1500` (D-10 short copy + 3–4 cards). `[ASSUMED: timings/temperature/max_tokens are recommended starting values, not measured.]`

**Feeding the validation error back into the corrective retry:** two valid approaches — (a) **model escalation alone** (D-12's literal reading: Haiku→Sonnet on retry, no prompt change) which is the simplest and is what D-12 specifies; or (b) additionally appending the `ValidationError` message as a corrective user turn ("предыдущий ответ не прошёл валидацию: {err}; верни строго JSON по схеме"). Recommend (a) as the locked baseline (matches D-12); (b) is an optional enhancement the planner can add if Sonnet-retry alone proves insufficient. With constrained decoding, escalation alone is expected to suffice.

**Honest fail (D-09):** when tenacity re-raises after attempt 2, `ReadingService`:
1. sets `reading.status = "failed"`, writes `reading.generation_error` (truncated, server-side detail);
2. writes a final `generation_logs` row (status `failed`, error);
3. **does NOT** call `LimitService.consume` (limit kept — READ-04/10);
4. **does NOT** assemble any templated reading from base meanings (D-09);
5. returns the soft §9.8 copy so the frontend shows «Колода замолчала…» with Повторить + Сменить колоду (D-08).

### Pattern 5: PromptEngine — assemble versioned templates (READ-11, D-01/D-02)

**What:** `PromptEngine.build()` composes the system + user prompt from active `prompt_templates` rows (types `system`, `single_card`, `final_summary`, `deck_modifier`, `safety`, `refusal` — already seeded Phase 1) plus the live deck/spread/card data.

- **System block** = `system` template (§16, the 10 principles + allow/ban formulations) + the active `deck_modifier` for the chosen deck (§19) + the **D-02 signature instruction** ("в каждом раскладе обязательно используй <deck signature device>"). The deck's own `decks.prompt_modifier` column (already seeded) is the per-deck §19 text; the `deck_modifier` template type is the wrapper. Planner derives concrete signature sentences from §19 tones.
- **User block** = the fused §17+§18 task: per-position context (card title, universal `meaning_*`/`keywords_*` from `cards`, deck-specific modifiers from `deck_cards`, `spread_positions.prompt_instruction`, orientation) for every drawn card, plus the summary instruction, plus (if sensitive) the `safety` fragment (§20.3 `safety_modifier`).
- **Versioning:** read `prompt_templates.version` of the active templates and compose a `prompt_version` string (e.g. `system@v1+deck_modifier@v1`) → persist to `readings.prompt_version` and `generation_logs.prompt_template_version` (ANALYTICS-02). CLAUDE.md anti-pattern: don't hardcode a dated model id — log the alias `claude-haiku-4-5` and the resolved version.
- **Language:** always instruct Russian output (D-14) regardless of question language.
- **Caching opportunity (optional):** the large `system` block is identical across readings → a candidate for Anthropic prompt caching (`cache_control: ephemeral`) post-MVP; not required for the slice.

### Pattern 6: Frontend seam swap (D-07, READ-01)

**What:** Replace the body of `frontend/src/reading/createReading.ts` (currently builds a `MockReading` from `cardPool.fixture` + `copy.ts` templates) with an authenticated `POST /api/readings` via the existing `apiFetch` seam, **preserving the exact `MockReading` return type** so the reveal/result UI is untouched (the type module comment says the swap is "mechanical").

- Use the existing `apiFetch("/api/readings", { method: "POST", body: JSON.stringify(...) })` (attaches Bearer JWT automatically).
- This is a TanStack Query **mutation** (server state) — do NOT mirror into Zustand (PROJECT/web rules; Phase-3 D-05 note). Phase 3 currently stuffs the mock into Zustand; Phase 4 moves it to a Query mutation with loading/error states feeding D-07 (ritual cover) and D-08 (failure UX).
- Map the backend `ReadingOut` (per-card + 5 summary fields) onto `MockReading`/`MockReadingCard`/`MockReadingSummary` (field names already mirror READ-05/06). The summary's `connection→linkage`, `attention_point→attention`, `soft_advice/advice→softAdvice`, `closing_phrase→closingPhrase`.
- Reveal awaits the promise; if it resolves before the ritual ends, hold; if after, the last beat loops (D-07, no spinner).
- Failure copy already exists verbatim: `READING_ERROR` in `copy.ts` (§9.8). The "Сменить колоду" path reuses Phase-3 D-04 question-preservation.

### Anti-Patterns to Avoid
- **Classifying inside the main generation call** — cannot gate crisis before draw/charge (D-03). Use a separate pre-call (Pattern 2).
- **Enforcing `≤140` via `max_length` in the schema** — stripped before sending; constrained decoding ignores it. Put it in the field description + prompt + a post-validation guard.
- **`random` for the draw** — must be `secrets`/`SystemRandom` (CLAUDE.md, §12.5).
- **Prompt-"return JSON" + `json.loads`** — CLAUDE.md "never". Use `messages.parse`.
- **Consuming the limit before generation succeeds** — READ-10/D-09 require decrement only on success.
- **Assembling a templated stand-in reading on failure** — D-09 forbids it; honest fail only.
- **Hardcoding a dated model snapshot id everywhere** — use the alias, log the resolved version (CLAUDE.md).
- **Mirroring the reading mutation into Zustand** — it's server state; TanStack Query owns it.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Forcing valid JSON from the LLM | Prompt "return JSON" + `json.loads` + regex repair | `messages.parse(output_format=ReadingOutput)` | Constrained decoding guarantees schema-valid output on `end_turn`; SDK does `validate_json` for you. Repairing fenced/partial JSON is the exact failure SO removes. |
| Retry/backoff/timeout | `for i in range(2): try/except` + manual sleep | `tenacity` `@retry(stop, wait, retry_if_exception_type)` + `messages.parse(timeout=...)` | Locked (CLAUDE.md); clean exception-typed retry + per-attempt deadline. |
| Schema → JSON Schema translation | Hand-writing JSON Schema for the API | Pass the Pydantic class to `output_format` | SDK runs `TypeAdapter(...).json_schema()` + `transform_schema()`, stripping unsupported keywords automatically. |
| Secure shuffle | `random.shuffle` + a seed | `secrets.SystemRandom().shuffle` | §12.5 requires CSPRNG; `random` is the documented anti-pattern. |
| Soft-error envelope | New error JSON in the router | The existing global handler (`core/errors.py`) + an explicit 200 soft body for the in-flow failure/safety cases | INFRA-05 handler already returns in-character JSON; the in-flow §9.8 cases are deliberate 200 responses with a `status` field, not 500s. |
| Brand-voice ban-list | A new RU regex in the backend | Port the canonical SAFE-06 ban-list (frontend `reading/copy.ts` `BANNED_BRAND_TOKENS`) as a backend guard | One source of truth; the Cyrillic-`ИИ` word-boundary logic is already solved. |

**Key insight:** Almost every "hard" part of this phase is a solved problem in a locked library. The genuinely bespoke work is the *orchestration ordering* (gate→draw→generate→consume) and the *schema/DB mapping* — that is where planning effort belongs, not in reimplementing JSON parsing or retries.

## Common Pitfalls

### Pitfall 1: `max_length`/`min_length` silently ignored by constrained decoding
**What goes wrong:** You set `short_meaning: str = Field(max_length=140)` expecting the model to be forced under 140 chars; it isn't.
**Why:** The SDK's `transform_schema` strips numeric/string-length constraints before sending (verified in docs + `messages.py` schema transform path). The model never sees the limit.
**How to avoid:** Encode "до 140 символов" in the field `description` AND the prompt, and add an explicit post-validation length check on `parsed_output` (truncate or treat as a soft validation note — do not fail the whole reading on a slightly-long line).
**Warning signs:** Occasional `short_meaning` longer than the result card was designed for.

### Pitfall 2: Refusal/max_tokens yields non-schema output → `ValidationError` on `parsed_output`
**What goes wrong:** Accessing `response.parsed_output` raises `ValidationError` even though the API call "succeeded" (HTTP 200).
**Why:** On `stop_reason in {"refusal","max_tokens"}` the text may not match the schema; `validate_json` then raises.
**How to avoid:** Check `response.stop_reason` before/with `parsed_output`. Treat `ValidationError` as a retry trigger (Pattern 4). Set `max_tokens` high enough for 3–4 short cards + summary (~1500 start). Note: the **safety pre-call** (Pattern 2) already removes true-crisis prompts before generation, so a model-level refusal during generation should be rare.
**Warning signs:** `generation_logs` showing `failed` with a `ValidationError` and `stop_reason=max_tokens`.

### Pitfall 3: `position_index` drift between drawn cards and model output
**What goes wrong:** The model returns interpretations in a different order/count than the drawn cards, so persistence maps the wrong text to the wrong slot.
**Why:** The model is free-running the array unless anchored.
**How to avoid:** Give each card an explicit `position_index` in the user prompt and require the same index in `CardInterpretation`; persist by **matching on `position_index`**, not by list order. Validate `len(output.cards) == card_count` (treat mismatch as a retry trigger). Card **names/orientations are authoritative server-side** (from `reading_cards`) — never trust the model to echo them.
**Warning signs:** Result screen showing an interpretation that doesn't fit the card/position.

### Pitfall 4: Limit consumed on a failed or safety-blocked reading
**What goes wrong:** User loses a free reading on a crash or a crisis short-circuit.
**Why:** Decrement placed too early (before generation) or in a shared code path.
**How to avoid:** `LimitService.consume()` is called in exactly one place — the success branch, after persisting `completed`, before commit. Every other exit (no quota, crisis, abusive, failed) returns without consuming (READ-10/D-09). Add an integration test per exit path asserting `free_used_this_week` unchanged.
**Warning signs:** Test or manual run where a failed reading decrements the counter.

### Pitfall 5: Greenlet/lazy-load error persisting cards or reading the deck pool
**What goes wrong:** `MissingGreenlet` when serializing or when touching an unloaded relationship inside the async session.
**Why:** SQLAlchemy 2.0 async forbids implicit lazy loads (the catalog service already uses `selectinload` to avoid this — `spread.positions`).
**How to avoid:** Eager-load the spread positions + deck cards needed for the draw/prompt with `selectinload`/explicit `select()`; build the response from already-loaded data (mirror `catalog.py`).
**Warning signs:** Intermittent 500s only under the ASGI server, not in unit tests.

### Pitfall 6: Blocking the event loop with a sync Anthropic client
**What goes wrong:** Under load, the whole FastAPI worker stalls during the LLM call.
**Why:** Using `anthropic.Anthropic()` (sync) inside an async handler blocks the loop.
**How to avoid:** Use `anthropic.AsyncAnthropic()` and `await client.messages.parse(...)` (the async `parse` exists — verified at `messages.py:2612`). tenacity has async support (`AsyncRetrying` / the `@retry` decorator works on coroutines).
**Warning signs:** Latency spikes affecting unrelated endpoints during a generation.

## Code Examples

### `messages.parse` — the single call (verified API shape)
```python
# Source: installed anthropic==0.109.1 — resources/messages/messages.py:1159 (sync) / :2612 (async);
#         types/parsed_message.py (parsed_output property); GA per platform.claude.com structured-outputs.
import anthropic

client = anthropic.AsyncAnthropic()  # reads ANTHROPIC_API_KEY from env (config has it as a required secret)

response = await client.messages.parse(
    model="claude-haiku-4-5",
    max_tokens=1500,
    system=system_prompt,                       # §16 + deck_modifier + signature
    messages=[{"role": "user", "content": user_prompt}],   # fused §17+§18 task + card context
    output_format=ReadingOutput,                # Pydantic class → schema built by the SDK
    temperature=0.7,
    timeout=20.0,
)
reading: ReadingOutput = response.parsed_output             # validated instance (or raises ValidationError)
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
stop_reason = response.stop_reason                          # guard: "refusal" / "max_tokens" → retry
# No beta header. output_format is translated to output_config.format internally.
```

### Mocking the LLM in tests (no real API)
```python
# Source: established pattern; tests/conftest.py provides ASGITransport client + isolated session.
# Override LLMService (or the AsyncAnthropic client) so no network call happens.
import pytest
from app.schemas.reading import ReadingOutput, CardInterpretation, ReadingSummary

@pytest.fixture
def fake_reading_output():
    return ReadingOutput(
        cards=[CardInterpretation(position_index=0, short_meaning="…", interpretation="…",
                                  mystical_accent="…", soft_advice="…")],
        summary=ReadingSummary(summary_short="…", connection="…", main_factor="…",
                               attention_point="…", advice="…", closing_phrase="…"),
    )

# In the test, monkeypatch LLMService.generate to return fake_reading_output (success path),
# or raise ValidationError twice (honest-fail path) / once then succeed (corrective-retry path),
# and assert: status transitions, generation_logs rows, and limit consumed ONLY on success.
```
Recommended: make `LLMService` and `SafetyService` injectable into `ReadingService` (constructor or FastAPI dependency) so tests substitute fakes — never hit Anthropic in unit/integration tests. Keep one *optional*, env-gated live smoke test (skipped without a real key) to catch contract drift.

## Runtime State Inventory

> Greenfield-leaning phase (new backend code + one frontend seam swap). No rename/migration. Included for completeness because it touches stored data.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | New `readings` / `reading_cards` / `generation_logs` rows written at runtime. Schema already exists (Phase 1) — no migration. | code only |
| Live service config | None — no external service config embeds project strings for this phase. | none |
| OS-registered state | None. | none |
| Secrets/env vars | `ANTHROPIC_API_KEY` is already a required secret (config.py, INFRA-04) and present in `tests/conftest.py`. No new secret. | none |
| Build artifacts / installed packages | `anthropic` + `tenacity` must be **added to `backend/pyproject.toml`** (currently absent) and installed. `tests/conftest.py` already sets a dummy `ANTHROPIC_API_KEY`. | dependency add (behind checkpoint) |

**Nothing found** in Live service config / OS-registered state — verified by reading config.py, redis.py, and pyproject.toml.

## Common Pitfalls — DB schema reality check (verified against models)

- `readings` has NO seed/debug_hash column → the §12.5 "save hidden seed" is not directly storable; the durable record is the immutable `reading_cards` rows. Recommend treating per-reading reproducibility hash as out-of-MVP or logging it as context (Open Question).
- `reading_cards` has NO JSON column → `soft_advice` must fold into an existing `String` column (recommend appending to `interpretation`).
- `readings.summary_full` is a wide `String` → recommended carrier for the JSON-serialized full `ReadingSummary` (lossless).
- `generation_logs` fields map 1:1 to what `messages.parse` exposes (`input_tokens`/`output_tokens`/`latency_ms` (compute), `model_name`, `status`, `error`, `prompt_template_version`). One row per LLM call (classify + each generation attempt).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Beta Structured Outputs (`structured-outputs-2025-11-13` header, `output_format`) | **GA**: no beta header; `output_format` → `output_config.format`; old header still works in transition | Structured Outputs went GA (pre-2026-06) | `messages.parse` with `output_format=PydanticModel`, no header — exactly CLAUDE.md's claim. Verified. |
| Prompt-and-parse / strict tool use for JSON | `client.messages.parse` + Pydantic, constrained decoding | GA SO | Simpler, guaranteed-valid; the locked approach. |
| `claude-3-5-haiku` / Sonnet 4.0 (stale skill) | `claude-haiku-4-5` / `claude-sonnet-4-6` (CLAUDE.md) | — | Use CLAUDE.md model ids; the local `claude-api` skill is stale on models and predates `messages.parse`. |

**Deprecated/outdated:**
- The bundled `claude-api` skill: references Sonnet 4 / Haiku 3.5 and has no `messages.parse`. **Do not** use it for model ids or the Structured Outputs API — CLAUDE.md + the verified SDK source are authoritative.
- `thinking.type="enabled"` emits a deprecation warning for some models (use `"adaptive"`); thinking is not needed for this phase — leave it off.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Summary overflow fields (`connection`/`attention_point`/`closing_phrase`) stored as JSON in `readings.summary_full`; `soft_advice` appended to `reading_cards.interpretation` | Pattern 1 mapping | Low — lossless and no migration; planner/discuss may prefer a leaner mapping. Easy to change. |
| A2 | Classify call latency ~300–700ms and cost <<$0.001; generation ~1500 max_tokens | Pattern 2 / Pattern 4 | Low — estimates from Haiku pricing + prompt size, not measured. Tune after first live run. |
| A3 | Starting retry/timeout/temperature: `stop_after_attempt(2)`, `wait_fixed(0.5)`, `timeout=20s`, `temperature≈0.7` | Pattern 4 | Low — explicitly delegated to planner; these are safe defaults. |
| A4 | Model escalation alone (Haiku→Sonnet) suffices for the corrective retry (no corrective prompt-turn needed) | Pattern 4 | Low–Med — matches D-12 literally; with constrained decoding a 2nd attempt should validate. Option (b) is a documented fallback. |
| A5 | Per-reading seed/debug_hash (§12.5) is effectively out-of-MVP because no DB column exists | Pattern 3 / schema check | Low — `reading_cards` is the durable record; reproducibility hash is a debug nicety. Confirm with user if exact reproducibility is required. |
| A6 | Empty question (HOME-02) classifies as `normal` and proceeds (general reading) | Pattern 2 | Low — matches HOME-02 + §9.8 empty-question copy. |

These assumptions are safe defaults flagged for the planner/discuss-phase; none contradict a locked decision.

## Open Questions

1. **Per-reading seed/debug_hash storage (§12.5).**
   - What we know: §12.5 says "save seed/debug_hash hidden"; the locked `readings` model has no such column; `reading_cards` durably records the actual draw.
   - What's unclear: whether exact draw reproducibility is an MVP requirement or a debug nicety.
   - Recommendation: treat as out-of-MVP (the immutable `reading_cards` rows are the record); if reproducibility is wanted later, add a column in a future migration. Do not block Phase 4.

2. **Brand-voice guard severity on generated text (SAFE-06 on output).**
   - What we know: the system prompt forbids AI/brand words; a backend port of `BANNED_BRAND_TOKENS` can detect violations post-generation.
   - What's unclear: whether a detected violation should fail/retry the reading or just log a warning.
   - Recommendation: **log + flag** (don't fail the reading) for MVP — a brand-word slip is rare with the §16 prompt and far less bad than an honest-fail. Planner decides.

3. **Exact per-deck signature wording + `safety_modifier` + `refusal`/redirect copy.**
   - What we know: §19 tones, §20.3 safe-formulation example, §9.8 copy, D-02/D-04/D-06 give the requirements.
   - What's unclear: the literal sentences (delegated to planner per CONTEXT).
   - Recommendation: planner authors them into the `prompt_templates` seed/text, passing the SAFE-06 ban-list and §15.1 allow/ban lists.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `anthropic` SDK | LLMService / SafetyService | ✗ (not in pyproject) | resolvable: 0.109.1 | none — must add to pyproject (Pattern 4) |
| `tenacity` | LLMService retry | ✗ (not in pyproject) | resolvable: 9.1.4 | none — must add to pyproject |
| `ANTHROPIC_API_KEY` (runtime) | live generation | ✓ (required secret, set in tests) | — | tests mock LLMService; live key only for the optional smoke test |
| PostgreSQL 16 | persist readings/cards/logs | ✓ (compose; tests skip if down) | 16 | tests `pytest.skip` when unreachable |
| Redis 7 | (Phase 4 optional cache) | ✓ (compose) | 7 | not required for the slice |
| `pytest`/`pytest-asyncio`/`httpx` | tests | ✓ | 8/0.24/0.28 | — |

**Missing dependencies with no fallback:** `anthropic`, `tenacity` — both MUST be added to `backend/pyproject.toml` (behind the human-verify checkpoint). This is the single hard prerequisite that blocks execution until done.

**Missing dependencies with fallback:** live `ANTHROPIC_API_KEY` for tests — all unit/integration tests mock `LLMService`/`SafetyService`; no real key needed for the green suite.

## Validation Architecture

> Nyquist validation is enabled (no `workflow.nyquist_validation: false` found). Section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"`) + httpx ASGITransport |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`, `testpaths=["tests"]`) |
| Quick run command | `cd backend && pytest tests/unit -x -q` |
| Full suite command | `cd backend && pytest -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| READ-02 | CSPRNG draw: count==positions; reversals off→all upright; on→reversed possible | unit | `pytest tests/unit/test_card_draw.py -x` | ❌ Wave 0 |
| READ-02 | uses `secrets`/`SystemRandom`, not `random` (no `random.shuffle` import in service) | unit | `pytest tests/unit/test_card_draw.py::test_uses_csprng -x` | ❌ Wave 0 |
| READ-03 | `ReadingOutput` schema round-trips fused §17+§18; `validate_json` rejects bad shape | unit | `pytest tests/unit/test_reading_schema.py -x` | ❌ Wave 0 |
| READ-03/05/06 | success path: mocked LLM → readings+reading_cards persisted, status completed, response carries all fields | integration | `pytest tests/integration/test_readings_flow.py::test_success -x` | ❌ Wave 0 |
| READ-04 | invalid JSON twice → reading=failed, soft §9.8 body, limit NOT consumed | integration | `pytest tests/integration/test_readings_flow.py::test_honest_fail -x` | ❌ Wave 0 |
| READ-04 | invalid once then valid → corrective retry escalates to Sonnet, succeeds | integration | `pytest tests/integration/test_readings_flow.py::test_corrective_retry -x` | ❌ Wave 0 |
| READ-10 | limit consumed exactly once on success; unchanged on every non-success exit | integration | `pytest tests/integration/test_readings_limit.py -x` | ❌ Wave 0 |
| READ-11/SAFE-06 | generated/response copy contains no banned brand token (backend ban-list) | unit | `pytest tests/unit/test_brand_guard.py -x` | ❌ Wave 0 |
| SAFE-01/02 | normal→generate; *_sensitive→safety_modifier appended to prompt | unit | `pytest tests/unit/test_safety_routing.py -x` | ❌ Wave 0 |
| SAFE-03 | crisis (regex + classify) → refusal, NO draw, NO generation, limit kept | integration | `pytest tests/integration/test_safety_gate.py::test_crisis_short_circuits_before_draw -x` | ❌ Wave 0 |
| SAFE-01 | gate runs BEFORE CardDrawService (no reading_cards written on crisis) | integration | `pytest tests/integration/test_safety_gate.py::test_no_cards_on_crisis -x` | ❌ Wave 0 |
| D-06 | abusive_or_manipulative → redirect, no draw, limit kept | integration | `pytest tests/integration/test_safety_gate.py::test_abusive_redirect -x` | ❌ Wave 0 |
| ANALYTICS-02 | one generation_logs row per LLM call with model/tokens/latency/status/version | integration | `pytest tests/integration/test_generation_logs.py -x` | ❌ Wave 0 |
| READ-01 | `POST /api/readings` requires Bearer; 401 without JWT; validates body | integration | `pytest tests/integration/test_readings_auth.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/unit -x -q`
- **Per wave merge:** `cd backend && pytest -q`
- **Phase gate:** full suite green before `/gsd-verify-work`; the live-API smoke test is env-gated and skipped by default.

### Wave 0 Gaps
- [ ] `tests/unit/test_card_draw.py` — covers READ-02 (count/orientation/CSPRNG)
- [ ] `tests/unit/test_reading_schema.py` — covers READ-03 (ReadingOutput validation)
- [ ] `tests/unit/test_safety_routing.py` — covers SAFE-01/02 routing
- [ ] `tests/unit/test_brand_guard.py` — covers SAFE-06 backend guard
- [ ] `tests/integration/test_readings_flow.py` — success / honest-fail / corrective-retry (mocked LLM)
- [ ] `tests/integration/test_readings_limit.py` — READ-10 consume-only-on-success
- [ ] `tests/integration/test_safety_gate.py` — SAFE-03 / D-06 gate-before-draw
- [ ] `tests/integration/test_generation_logs.py` — ANALYTICS-02
- [ ] `tests/integration/test_readings_auth.py` — READ-01 auth + body validation
- [ ] Shared fixtures in a `tests/integration/conftest.py` (extend existing) or root conftest: a `fake_llm` / `fake_safety` fixture + a seeded deck/spread/cards fixture (or reuse the seed loader) so the flow has real catalog rows to draw from.
- [ ] Frontend: `createReading.test.ts` already exists (mock) → update to assert the real `apiFetch` POST shape + error mapping (Vitest); add a test that reveal awaits the promise (D-07) and failure surfaces Повторить + Сменить колоду (D-08).
- [ ] Framework install: add `anthropic` + `tenacity` to pyproject (prerequisite, not a test file).

## Security Domain

> `security_enforcement` not disabled in config → included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `get_current_user` Bearer JWT already gates the router (reuse; 401 on missing/invalid) |
| V3 Session Management | yes (inherited) | JWT HS256 from Phase 1; `POST /api/readings` reuses it; no new session surface |
| V4 Access Control | yes | reading is created for the authenticated user only; `user_id` from the JWT, never the body (mirrors auth T-04-01); a user cannot create a reading as someone else |
| V5 Input Validation | yes | Pydantic `ReadingCreate` validates body; question length 10–500 (HOME-01) / empty allowed (HOME-02); deck/spread slugs validated against catalog; `messages.parse` validates LLM output |
| V6 Cryptography | yes | `secrets.SystemRandom` for the draw (CSPRNG, §12.5) — never hand-roll RNG; never `random` |
| V7 Error Handling & Logging | yes | soft in-character error (no stacktrace, INFRA-05); `generation_logs` audit; server-side detail in `generation_error`/logs, never leaked to client |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Client forges card selection or limit state | Tampering | Backend-only CSPRNG draw + backend limit check (§29.2); never trust frontend |
| Prompt injection via the user's question | Tampering / Elevation | User question is data inside a fixed system frame (§16); structured output constrains the response shape; safety pre-classify catches abusive/manipulative; output ban-list guard |
| Crisis question served a fatalistic prediction | (Safety/abuse) | Mandatory pre-gate short-circuits crisis to a supportive refusal **before** generation (D-03/SAFE-03) |
| LLM error leaks stacktrace/internal detail | Information Disclosure | Global soft-error handler + explicit 200 soft body; truncated server-side `generation_error`; threat T-02-03 generation audit in `generation_logs` |
| Spending/abuse via rapid reading creation | DoS / cost | Limit check gates creation; honest-fail keeps the limit (no free infinite retries that also generate — the retry is the *same* failed reading, not a new charge); Redis throttle is Phase 6 |
| API key exposure | Information Disclosure | `ANTHROPIC_API_KEY` from env (required secret, no default); never in code/logs; never echoed in responses |

## Sources

### Primary (HIGH confidence)
- Installed `anthropic==0.109.1` source — `resources/messages/messages.py:1159` (sync `parse`) / `:2612` (async), `:1054`/`1209-1240` (output_format→output_config transform, schema transform), `:1183` (per-call `timeout`); `types/parsed_message.py` (`parsed_output` property); `lib/_parse/_response.py:16-20` (`parse_text` → `TypeAdapter.validate_json`). Ground-truth API surface.
- `platform.claude.com/docs/en/build-with-claude/structured-outputs` — GA (no beta header), `output_format`/`output_config.format`, `parsed_output`, `stop_reason` refusal/max_tokens, model support incl. `claude-haiku-4-5`; schema constraints: `minItems` 0/1 only, `minLength`/`maxLength`/numeric constraints stripped, ≤24 optional params, ≤16 union params, enum support, `additionalProperties:false`.
- Codebase (read directly): `backend/app/models/{reading,prompt,analytics,deck,card,spread,billing,user,enums}.py` (locked schema), `services/{catalog,telegram_auth}.py` (service pattern), `api/{deps,decks}.py`, `core/{config,errors,redis}.py`, `schemas/{auth,catalog}.py`, `tests/conftest.py` + `tests/integration/conftest.py` (fixtures), `frontend/src/reading/{createReading,copy,types}.ts` + `api/client.ts` + `lib/api.ts` (seam).
- `.planning/REFERENCE-TZ.md` §12.3–12.5, §14.5, §15/15.1, §16, §17, §18, §19.1–19.6, §20.1–20.4, §9.8, §29.1/29.2, §30.
- `CLAUDE.md` (locked stack/models/anti-patterns), `04-CONTEXT.md` (D-01..D-14), `REQUIREMENTS.md` (Phase-4 IDs).

### Secondary (MEDIUM confidence)
- `pip index versions anthropic` → 0.109.1; `pip index versions tenacity` → 9.1.4 (PyPI registry).
- `slopcheck 0.6.1 install anthropic tenacity` → both `[OK] (pypi)`.

### Tertiary (LOW confidence)
- WebFetch of the structured-outputs doc returned some hallucinated **model names** (e.g. "Claude Fable 5", "Opus 4.8") in the prose example — **discarded**; only the structural API facts (cross-verified against installed SDK source) were used. Model ids come from CLAUDE.md.

## Metadata

**Confidence breakdown:**
- Standard stack / SDK API: **HIGH** — verified against installed `anthropic==0.109.1` source AND official GA docs; both new packages slopcheck-clean and registry-confirmed.
- Single-call schema + DB mapping: **HIGH** on the schema (verified constraints); **MEDIUM** on the exact overflow-field mapping (A1 — a safe, lossless recommendation the planner may adjust).
- Safety gate design: **HIGH** that a separate pre-call is the only design honoring D-03's locked ordering; **MEDIUM** on cost/latency figures (A2 — estimates).
- Resilience contract: **HIGH** on the failure-surfacing mechanism (`ValidationError` from `validate_json`, verified); **MEDIUM** on exact timings (A3 — delegated to planner).
- Pitfalls / architecture: **HIGH** — grounded in the read codebase patterns and verified SDK/doc behavior.

**Research date:** 2026-06-12
**Valid until:** ~2026-07-12 (anthropic SDK moves fast; re-verify `messages.parse` signature + model ids if the SDK is bumped or models change. DB schema/TZ/decisions are stable.)
