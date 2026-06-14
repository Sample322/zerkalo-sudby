---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-06-14T10:27:01.042Z"
last_activity: 2026-06-14 -- Phase 05 planning complete
progress:
  total_phases: 8
  completed_phases: 4
  total_plans: 27
  completed_plans: 20
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-09)

**Core value:** Один и тот же вопрос ощущается по-разному в разных колодах — красивый мистический ритуал в Telegram, дающий глубокий, но бережный ответ.
**Current focus:** Phase 5 — history & profile

## Current Position

Phase: 5
Plan: Not started
Status: Ready to execute
Last activity: 2026-06-14 -- Phase 05 planning complete

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 15
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3 | - | - |
| 03 | 6 | - | - |
| 04 | 6 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01 P01 | 35 | 3 tasks | 47 files |
| Phase 01 P02 | 30 | 2 tasks | 14 files |
| Phase 01 P03 | 35 | 2 tasks | 10 files |
| Phase 01 P04 | 40 | 3 tasks | 19 files |
| Phase 01 P05 | 10 | 1 tasks | 13 files |
| Phase 03 P01 | 10 | 3 tasks | 16 files |
| Phase 03 P02 | 5 | 2 tasks | 3 files |
| Phase 04 P01 | 8 | 3 tasks | 14 files |
| Phase 04 P02 | 30 | 2 tasks | 5 files |
| Phase 04 P03 | 25 | 2 tasks | 4 files |
| Phase 04 P04 | 30 | 2 tasks | 3 files |
| Phase 04 P05 | 55min | 2 tasks | 9 files |
| Phase 04 P06 | 5 | 2 tasks | 7 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Build order: vertical-MVP slices — each phase ships an end-to-end user-visible capability, not a horizontal layer.
- Phase 1: aiogram bot is an in-process FastAPI module (not a separate service); bot module first wired in Phase 7 (Payments).
- Phase 1: `initData` two-stage HMAC + `auth_date` freshness is the security spine; `telegram_id` derived only from validated initData.
- Phase 4 (KEYSTONE): one structured LLM call per reading + mandatory safety classifier gating generation (crisis short-circuits before draw/charge); limit never consumed on failure.
- Card draw + limit checks are backend-only (CSPRNG) throughout.
- [Phase ?]: Phase 1: full 17-table schema (16 TZ §13 + topics lookup) locked in one initial Alembic migration 0001; native PG ENUMs for the 9 fixed status/type sets; topics is a lookup only (not a FK target), readings.topic stays a TEXT slug.
- [Phase ?]: Phase 1: slug keys + users.telegram_id + payments.payload UNIQUE constraints are the durable integrity guarantees later phases (auth upsert, payment idempotency) and the admin panel rely on.
- [Phase ?]: Phase 1: MVP seed shipped as JSON files + `python -m app.seed` CLI (not an Alembic data-migration) — re-runnable, content editable independent of schema history (RESEARCH Pattern 6).
- [Phase ?]: Phase 1: idempotent seed via upsert-by-slug (ON CONFLICT DO UPDATE); spread_positions (no single-column unique key) rebuilt per spread via a scoped delete->insert inside the same transaction.
- [Phase ?]: Phase 1: initData validator is hand-rolled to the exact Telegram two-stage HMAC (secret=HMAC_SHA256(b'WebAppData',bot_token), constant-time hmac.compare_digest, auth_date freshness); telegram_id derived ONLY from the validated user blob, never the request body.
- [Phase ?]: Phase 1: JWT is PyJWT HS256 with sub=user UUID + telegram_id claim; decode pins algorithms=['HS256'] so alg:none is rejected; get_current_user is the reusable Bearer gate, require_admin the server-side ADMIN_TELEGRAM_IDS allowlist.
- [Phase ?]: Phase 1: thin routers delegate to services/telegram_auth.authenticate() (TelegramAuthService reused by the bot in Phase 7); INFRA-05 global Exception handler returns soft in-character JSON (no stacktrace leak), Sentry is a no-op seam deferred to Phase 8.
- [Phase ?]: Phase 1: frontend auth wiring complete — getInitData() reads window.Telegram.WebApp.initData with a DEV-only VITE_DEV_INIT_DATA fallback (stripped from prod bundle); useSession (Zustand) holds jwt/user/availableReadings/status; apiFetch is the reusable Authorization: Bearer seam for all later phases; AuthGate renders authenticating/authenticated/error with in-character copy and zero AI-branding.
- [Phase ?]: Phase 3: FlowRoot is the single AnimatePresence step-switch (D-02); Wave-2 plans replace only their own screen stub, never FlowRoot.
- [Phase ?]: Phase 3: ephemeral mock reading lives only in the Zustand store (reading slot + setReading), never TanStack Query; createReading() is the single Phase-4 source-swap seam (D-05).
- [Phase ?]: Phase 3: canonical SAFE-06 BANNED_BRAND_TOKENS helper in reading/copy.ts detects the standalone Cyrillic ИИ token without false-positiving benign words (W-1); all Wave-2 SAFE-06 tests import it.
- [Phase ?]: Phase 4: LLM-output schemas put the length target in Field(description) only — never max_length/min_length (Anthropic SDK strips length constraints, constrained decoding ignores them — RESEARCH Pitfall 1).
- [Phase ?]: Phase 4: ReadingOut surfaces all five §18 summary fields under the frontend MockReading names so the Plan-06 data-source swap is mechanical; the 3 overflow LLM fields persisted losslessly later (Plan 05).
- [Phase ?]: Phase 4: FakeLLM/FakeSafety are injectable async service stand-ins (via app.dependency_overrides) so integration tests never hit Anthropic; seeded_catalog reuses run_seed in the savepoint transaction.
- [Phase 04]: Phase 4 (Plan 02): CardDrawService is backend-only CSPRNG draw — secrets.SystemRandom for shuffle AND the orientation coin, never stdlib random; pure _assign_orientations helper takes an injectable rng so the 70/30 ratio is tested deterministically while production stays CSPRNG.
- [Phase 04]: Phase 4 (Plan 02): CardDrawService writes nothing — returns frozen DrawnCard records (card_id, deck_card_id, position_id, position_index, orientation + joined universal meaning); ReadingService (Plan 05) owns reading_cards INSERT and the transaction; no seed/debug_hash column per A5/OQ1.
- [Phase 04]: Phase 4 (Plan 02): backend core/brand_guard.py is a 1:1 port of frontend BANNED_BRAND_TOKENS (one source of truth, W-1); LOG+FLAG disposition (OQ2) — flags a brand slip on generated text, never fails the reading.
- [Phase 04]: Plan 03: LLMService wraps ONE messages.parse(output_format=ReadingOutput) in tenacity AsyncRetrying (stop_after_attempt(2), reraise) — attempt 1 claude-haiku-4-5, the single corrective retry claude-sonnet-4-6 (D-12) keyed off retry_state.attempt_number; aliases only, no dated snapshot.
- [Phase 04]: Plan 03: RETRYABLE=(ValidationError, anthropic.APIStatusError/APIConnectionError, TimeoutError, _NonSchemaStopReason); refusal/max_tokens stop_reason wrapped retryable (Pitfall 2). Exhaustion raises typed LLMGenerationError → Plan 05 honest-fails (D-09), never templated. GenerationResult carries generation_logs fields (ANALYTICS-02).
- [Phase 04]: Plan 03: SafetyService.classify Stage 1 pure regex returns crisis_sensitive instantly + empty/None→normal (HOME-02), both NO call (meta=None); Stage 2 tiny messages.parse(output_format=SafetyVerdict) Haiku for undecided. Pure route()→SafetyAction (crisis→REFUSAL, abusive→REDIRECT, *_sensitive→SAFETY_MODIFIER, normal→GENERATE); continues_to_draw = gate-before-draw boundary (D-03/04/05/06).
- [Phase 04]: Plan 03: LLMService + SafetyService take an injectable AsyncAnthropic client (default = core/llm_client singleton via local import); unit tests mock messages.parse with AsyncMock — no network, no ANTHROPIC_API_KEY. The Plan-05 + test mock seam.
- [Phase ?]: Phase 4 (Plan 04): PromptEngine.build composes ONE messages.parse prompt from ACTIVE prompt_templates (system §16 + deck_modifier_<slug> §19 carrying the mandatory D-02 signature + fused §17 per-card blocks + §18 summary); safety §20.3 fragment appended ONLY when safety_action==SAFETY_MODIFIER (D-05/SAFE-02); always Russian (D-14) + restated ≤140 short_meaning (D-10).
- [Phase ?]: Phase 4 (Plan 04): prompt_version composed from active template type@version fields (e.g. system@v1+deck_modifier@v2+single_card@v1+final_summary@v1) → readings.prompt_version + generation_logs (ANALYTICS-02/T-04-22); a missing active template raises ValueError (surfaced misconfig, never a degraded prompt).
- [Phase ?]: Phase 4 (Plan 04): D-02 signature seeded into all 6 deck_modifier rows (v2); generic D-04 refusal (no region/phone, v2); D-06 abusive-redirect seeded as a NEW safety-type 'redirect' row (no PromptTemplateType added) — single admin-editable source resolved via PromptEngine.refusal_copy/redirect_copy.
- [Phase ?]: Phase 4 (Plan 05): ReadingService.create_reading is the keystone — owns the AsyncSession transaction + the LOCKED gate->draw->generate->consume order; limit consumed in EXACTLY one place (success branch before commit); crisis/abusive persist a FAILED parent reading first (NOT-NULL generation_logs.reading_id FK) then short-circuit before draw; honest fail (D-09) = status=failed + truncated server-side error + soft section-9.8 200 body, NO consume, NO templated stand-in
- [Phase ?]: Phase 4 (Plan 05): collaborators injected via constructor (default=real services); _normalize_classify/_unpack_generation adapt BOTH the real services (ClassifyResult/GenerationResult) and the bare-value test fakes (SafetyVerdict/ReadingOutput) through one seam; ReadingOutput mapped onto DB by position_index (Pitfall 3), soft_advice folded into reading_cards.interpretation, full ReadingSummary JSON into readings.summary_full; one generation_logs row per ACTUAL LLM call (classify only when classify() returned call-meta)
- [Phase ?]: Phase 4 (Plan 05): seeded_catalog now synthesizes the deck_cards style layer (the seed JSON omits it — deck imagery is a later content task) so the backend-only CSPRNG draw has an active pool; seeded spread_positions.position_index is 1-based not 0-based, so fake LLM outputs echo the actual drawn indices

### Pending Todos

[From .planning/todos/pending/ — ideas captured during sessions]

None yet.

### Blockers/Concerns

[Issues that affect future work]

- Phase 4 flagged for deeper research at plan time: single-call JSON schema design, cheap safety-classifier approach, retry/timeout/fallback contract (highest product+technical risk).
- Phase 7 flagged for research: exact aiogram Stars surface, refund semantics (21-day), native recurring subscription modeling (lock native-recurring vs manual-window before schema usage — choose one, not a hybrid).
- Phase 8: timeweb.cloud deploy specifics deferred by design (MCP only does App Platform git deploy; managed PG/Redis/S3 + VPS provisioned manually); IP/legal review of deck assets required before public launch.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-06-14T09:34:39.674Z
Stopped at: Phase 5 context gathered
Resume file: .planning/phases/05-history-profile/05-CONTEXT.md
