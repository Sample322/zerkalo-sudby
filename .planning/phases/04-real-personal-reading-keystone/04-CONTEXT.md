# Phase 4: Real Personal Reading (KEYSTONE) - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning

<domain>
## Phase Boundary

The Core Value goes live: the user receives a **real, per-deck personalized reading** where the same question genuinely feels different per deck. This phase wires the real generation under the existing (Phase 3) ritual/reveal/result UI — only the data source changes.

**In scope:**
- Backend `POST /api/readings` (TZ §14.5): limit check → CSPRNG card draw (backend-only, `secrets`) → safety gate → **one** structured LLM call (`messages.parse`) returning all card interpretations + summary as schema-validated JSON → persist `readings` + `reading_cards` → return real reading (READ-01..06, READ-10, READ-11).
- New backend services (TZ §29.1): `ReadingService`, `CardDrawService`, `PromptEngine`, `LLMService` (+ the safety classifier component). `schemas/reading.py`, `api/readings.py`.
- Mandatory safety classifier (SAFE-01..05): classify question → normal / *_sensitive / crisis_sensitive / abusive_or_manipulative; **gates generation BEFORE draw/charge**; crisis short-circuits to a supportive response.
- Resilience: one corrective retry → timeout → honest fail; limit **NOT** consumed on failure (READ-04, READ-10).
- `generation_logs` written every generation: prompt_version, model, tokens, latency, status, error (ANALYTICS-02).
- Frontend: swap the Phase-3 mock `createReading()` seam (Phase 3 D-05) to the real async `POST /api/readings`; failure UX on the existing screens.

**Out of scope (later phases):** history list/detail/soft-delete + settings persistence `PATCH /api/me/settings` (Phase 5); free weekly limit / paywall / atomic decrement (Phase 6 — Phase 4 checks/decrements a limit but the weekly-reset + buckets machinery is Phase 6); Telegram Stars (Phase 7); admin CRUD of prompts/decks + `app_events` analytics + share-card (Phase 8). Card art stays null → CSS/SVG fallback (Phase 2 DECK-05).

</domain>

<decisions>
## Implementation Decisions

### Per-deck divergence (the Core Value)
- **D-01:** Divergence = **tone + focus**. A deck changes not only tone/imagery but **what the reading concentrates on** (Тени → вытесненное / повторяющиеся сценарии; Сердце → чувства и динамика между людьми; Лесной → природный цикл, возвращение к себе; Луна → эмоции/интуиция; Путь → варианты/ресурсы/следующий шаг; Классика → баланс, причины-следствия). The answer's **structure/format stays uniform** across decks (see D-11). Source modifiers: TZ §19.1–19.6 (already seeded as per-deck `prompt_modifier`; `deck_modifier` prompt-template type exists).
- **D-02:** Each deck has a **mandatory signature** — a guaranteed device that marks *that* deck, present in **every** reading even on similar questions (e.g. Лесной → always a nature metaphor; Тени → always names a hidden tension / repeating pattern). Difference is **guaranteed, not emergent**. Exact per-deck signature wording is Claude/planner's to derive from §19 tones; the *requirement* "a visible signature in every reading" is locked.

### Safety — crisis & sensitive (SAFE-01..05)
- **D-03:** **Crisis** (`crisis_sensitive`: self-harm / violence) → **fully break the mystical frame**. The oracle goes silent; direct, warm, human tone; **no cards, no prediction, no reading**. Implemented via prompt-template type `refusal`. Short-circuits **before** draw/charge (locked constraint). Limit not consumed.
- **D-04:** Crisis resources → **generic wording**, **no specific phone numbers**: "обратись к близкому человеку, которому доверяешь, или к специалисту." Avoids the risk of stale/incorrect numbers. *(Note: TZ §20.4 mentions region-dependent помощь-службы; user deliberately chose generic over concrete RU hotlines for MVP.)*
- **D-05:** **Sensitive** (`relationship_/financial_/health_/legal_sensitive`) → **silent softening**: a `safety_modifier` is added to the prompt (SAFE-02); the text is simply gentler, with **no visible disclaimer/badge** in the UI. The ban on categorical wording already lives inside the text (TZ §15, §20.1; SAFE-04/05). TZ §20.3 gives the safe-formulation example to draw from.
- **D-06:** **Abusive / manipulative / junk** question (`abusive_or_manipulative`, not crisis) → **gentle in-character redirect**: "колода молчит на это, задай вопрос от сердца." No reading, no draw, limit not consumed.

### Generation wait & failure UX (ties to Phase 3 D-01 smoothness bar)
- **D-07:** The real LLM call is **covered by the ritual**. The call fires on «Начать расклад»; the ~3s ritual plays during the wait; reveal happens **only** once schema-valid JSON is ready. If slow, the last ritual beat **holds/loops softly** — **no spinner**, seamless. (The Phase-3 `createReading()` seam becomes the async `POST /api/readings`.)
- **D-08:** On generation failure (after the one corrective retry), «колода замолчала» offers **Повторить** (same reading) **+ Сменить колоду** (back to selection with the question preserved, like Phase 3 D-04). NOT "just back" as the only option. Error copy source: TZ §9.8 ("Колода замолчала на мгновение…"). Limit not consumed → the retry is free.
- **D-09:** "DB-fallback" (from PROJECT.md / CLAUDE.md) is resolved as an **honest fail, NOT a templated reading**. On total failure: `reading=failed`, soft in-character error, limit **NOT** consumed, **no** stand-in reading assembled from base card meanings. Matches READ-04 and protects the Core Value (never serve cheap non-personal text). *[Resolves the PROJECT.md tension between "DB-fallback" and "reading=failed".]*

### Reading depth & length
- **D-10:** Depth = **short / atmospheric**. `short_meaning` ~1 line (≤140 chars per §17), `interpretation` ~2–3 sentences, tight summary. Matches the brand principle "меньше сухого текста, больше атмосферы" (§1.5) + mobile-first 360–430px + cheaper/faster (fewer tokens → ritual covers latency more easily, D-07).
- **D-11:** Length is **uniform across all 6 decks**. Differentiation comes from tone/focus/signature (D-01/02), **not** from volume. Even layout / predictable cost; consistent with "tone + focus" (not "+ structure").

### Model & generation behavior
- **D-12:** Sonnet escalates **only on the corrective retry** when Haiku returns invalid JSON (Haiku is the default). Per-deck / per-tier premium escalation is post-MVP. Matches CLAUDE.md "auto-escalation on validation failure."
- **D-13:** Reversals default for a new user = **on, 70/30** (model default `reversals_enabled=True`, TZ §8.1; ONB-03 already explains reversed cards). The value arrives in the request; settings persistence is Phase 5.
- **D-14:** Reading language is **always Russian**, regardless of the question's language. The product is Russian-language; this also simplifies the safety classifier and the prompt.

### Claude's Discretion (delegated to research + planner)
- **Safety-classifier mechanism** — separate cheap classify call vs regex pre-filter + a `safety` field in structured output vs classification inside the main call — is an **open research question** (the PROJECT.md tension: "классификация внутри основного вызова" vs "гейтит до draw/charge"; already flagged in STATE.md blockers). The **product invariant is locked** (crisis short-circuits *before* draw/charge); the HOW is for research/planner.
- **Single-call JSON schema design** — merging §17 (per-card: `short_meaning` / `interpretation` / `mystical_accent` / `soft_advice`) + §18 (summary: `summary_short` / `connection` / `main_factor` / `attention_point` / `advice` / `closing_phrase`) into **one** valid `messages.parse` object (edit #1), and mapping fields onto the DB schema (`reading_cards.short_meaning/interpretation/mystical_accent`; `readings.summary_short/summary_full/main_factor/advice`). §17/§18 show *separate* prompts — they must be fused into one call. Planner/research.
- Concrete per-deck signature texts, `safety_modifier` text, `refusal` copy — Claude/planner from §16/§17/§18/§19/§20.3 + §9.8.
- Exact retry/timeout timings and temperature — planner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project source-of-truth — `.planning/REFERENCE-TZ.md` (full TZ; the authoritative source)
- §12.3 — high-level reading flow (validate → create user → POST /api/readings → check limits → draw cards → save `pending` → LLM → save result → decrement limit).
- §12.4 / §12.5 — card draw is **backend-only**; random logic = CSPRNG shuffle, N by positions, orientation off→upright / on→70% upright / 30% reversed, save hidden seed/debug_hash.
- §13.8 / §13.9 / §13.10 / §13.16 — `readings`, `reading_cards`, `prompt_templates`, `generation_logs` field shapes (already implemented as models — see code_context).
- §14.5 — `POST /api/readings` request (`question, topic, deck_slug, spread_slug, reversals_enabled`) + response (`reading_id, status, selected_cards, interpretations, summary, remaining_limits`).
- §15 / §15.1 — prompt system: **allowed vs banned formulations** (drives SAFE-04/05). The exact allow/ban lists live here.
- §16 — the master system prompt for the "цифровая гадалка" (10 mandatory principles, style, allowed/forbidden phrasings).
- §17 — single-card prompt + JSON shape (`short_meaning ≤140`, `interpretation`, `mystical_accent`, `soft_advice`).
- §18 — summary prompt + JSON shape (`summary_short`, `connection`, `main_factor`, `attention_point`, `advice`, `closing_phrase`).
- §19.1–19.6 — per-deck prompt modifiers (Классика / Луна / Тени / Сердце / Путь / Лес) — the raw material for D-01 focus + D-02 signatures.
- §20 — **system safety constraints**: §20.1 general bans, §20.2 sensitive-topic list, §20.3 safe-formulation example, §20.4 classifier categories (`normal` / `relationship_/financial_/health_/legal_sensitive` / `crisis_sensitive` / `abusive_or_manipulative`).
- §9.8 — error / empty-state copy in product voice ("Колода замолчала на мгновение…", "Слишком опасный запрос…").
- §29.1 / §29.2 — backend services list + hard rules (don't trust frontend, cards/limits backend-only, validate all LLM by JSON schema, save gen errors, soft error not stacktrace).
- §30 — MVP north star: "один и тот же вопрос ощущается по-разному в разных колодах" = the core to make work.

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — Phase 4 IDs: READ-01..06, READ-10, READ-11, SAFE-01..05, ANALYTICS-02.
- `.planning/ROADMAP.md` → "Phase 4: Real Personal Reading (KEYSTONE)" — goal + 5 success criteria.

### Locked decisions & stack
- `.planning/PROJECT.md` → Key Decisions — edit #1 (single LLM call), edit #3 (safety classifier mandatory), LLMService swappable + `messages.parse`, CSPRNG backend draw, no-queue, safety gates before draw/charge.
- `CLAUDE.md` — LLM layer (Haiku 4.5 default / Sonnet escalation, `messages.parse`, anthropic ≥0.69 Structured Outputs GA), `tenacity` retry+timeout, Redis usage, brand-voice ban list, "Picking cards on backend" / "Python `random` for cards" anti-patterns.

### Prior phase (forward contract now being fulfilled)
- `.planning/phases/03-the-ritual-mock/03-CONTEXT.md` — D-01 (smoothness is a first-class acceptance criterion), D-05 (the mock reading type already mirrors READ-05/06; `createReading()` is the single source-swap seam), D-04 («ещё расклад» preserves question+topic — reused by failure UX D-08).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (already in repo)
- `backend/app/models/reading.py` — `Reading` (status, reversals_enabled, summary_short/summary_full/main_factor/advice, model_name, prompt_version, generation_error, completed_at) + `ReadingCard` (position_index, orientation, short_meaning, interpretation, mystical_accent). **Schema is locked from Phase 1** — the single-call JSON must map onto these columns.
- `backend/app/models/prompt.py` — `PromptTemplate` (slug, type, template_text, version, is_active). `type` ENUM includes `system / single_card / final_summary / deck_modifier / safety / refusal` — base templates seeded in Phase 1; PromptEngine assembles from these.
- `backend/app/models/analytics.py` — `GenerationLog` (prompt_template_version, model_name, input_tokens, output_tokens, latency_ms, status, error) — write one per generation (ANALYTICS-02).
- `backend/app/models/{deck,card,spread,topic}.py` — `decks.prompt_modifier`, `deck_cards.deck_specific_*_modifier`, `cards.meaning_*/keywords_*`, `spread_positions.prompt_instruction` — the inputs PromptEngine feeds the LLM.
- `backend/app/services/catalog.py`, `backend/app/services/telegram_auth.py` — the established service-layer pattern (thin router → service); new `ReadingService`/`LLMService`/`PromptEngine`/`CardDrawService` follow it.
- `backend/app/api/deps.py` — `get_current_user` Bearer gate (reuse to authenticate `POST /api/readings`); `require_admin` exists for later.
- `backend/app/core/{config,errors,redis,logging}.py` — fail-fast settings (ANTHROPIC_API_KEY already a required secret from INFRA-04), global soft-error handler (INFRA-05), Redis seam, structured logging.
- Frontend `createReading()` seam + the ritual/reveal/result screens (Phase 3) — swap the mock builder for the async POST; reveal waits on the promise (D-07).

### Established Patterns
- Backend: SQLAlchemy 2.0 async, `AsyncSession`, `select()`, `Mapped[...]`; native PG ENUMs; soft in-character error JSON (no stacktrace) via the global handler.
- Frontend: client/ephemeral state in Zustand, server state in TanStack Query; the reading mutation belongs to TanStack Query (`POST /api/readings`) with loading/error states — do NOT mirror into Zustand.
- Brand-voice gate: `reading/copy.ts` `BANNED_BRAND_TOKENS` (SAFE-06) — applies to all new generated-result and error copy too.

### Integration Points
- `POST /api/readings` is new (`api/readings.py`) — mounted alongside existing `decks`/`spreads`/`auth`/`users` routers in `api/__init__.py` / `main.py`.
- The reading mutation is the seam where the safety gate, CSPRNG draw, PromptEngine, LLMService, and `generation_logs` all compose inside `ReadingService`.

</code_context>

<specifics>
## Specific Ideas

- The failure copy already exists verbatim in TZ §9.8 — "Колода замолчала на мгновение. Попробуй открыть расклад ещё раз — вопрос уже сохранён." Use it (or a close in-voice variant) for D-08.
- The "Слишком опасный запрос" §9.8 line ("Колода не заменяет помощь специалиста…") is the tonal anchor for D-04/D-05 (sensitive) — not for true crisis, where the frame fully breaks (D-03).
- Carry Phase 3's D-01 felt-quality bar forward: smoothness during the now-real wait is a first-class acceptance criterion (D-07), not polish.

</specifics>

<deferred>
## Deferred Ideas

- Concrete regional crisis hotline numbers — user chose generic wording for MVP (D-04); revisit if a region-aware resources table is added later.
- Per-deck / premium-tier model escalation (deep decks always on Sonnet) — post-MVP; MVP keeps Haiku default + Sonnet only on retry (D-12).
- Visible sensitive-topic disclaimer UI — user chose silent softening (D-05); a visible care-note could be revisited if a regulatory need appears.
- History-based personalization (`allow_history_personalization`, `history_context` in §18 prompt) — Phase 5; Phase 4 passes it through but does not build the personalization path.
- Weekly-limit reset, buckets (free/paid/subscription), atomic decrement, Redis throttle — Phase 6. Phase 4 only needs "limit consumed on success, not on failure" (READ-10).
- `app_events` reading_started/completed/failed analytics — Phase 8 (ANALYTICS-01). Phase 4 writes `generation_logs` only (ANALYTICS-02).
- Reduced-motion fallback — still deferred (Phase 3 D-10).

</deferred>

---

*Phase: 04-real-personal-reading-keystone*
*Context gathered: 2026-06-12*
