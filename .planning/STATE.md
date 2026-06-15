---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: executing
last_updated: "2026-06-15T20:24:52.448Z"
last_activity: 2026-06-15
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 31
  completed_plans: 30
  percent: 63
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-06-09)

**Core value:** Один и тот же вопрос ощущается по-разному в разных колодах — красивый мистический ритуал в Telegram, дающий глубокий, но бережный ответ.
**Current focus:** Phase 06 — free-limits-soft-paywall

## Current Position

Phase: 06 (free-limits-soft-paywall) — EXECUTING
Plan: 4 of 4
Status: Ready to execute
Last activity: 2026-06-15

Progress: [██████████] 97%

## Performance Metrics

**Velocity:**

- Total plans completed: 24
- Average duration: — min
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 02 | 3 | - | - |
| 03 | 6 | - | - |
| 04 | 6 | - | - |
| 05 | 7 | - | - |

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
| Phase 05 P01 | 8min | 3 tasks | 8 files |
| Phase 05 P02 | 10min | 2 tasks | 3 files |
| Phase 05 P03 | 5min | 2 tasks | 3 files |
| Phase 05 P04 | 12min | 2 tasks | 2 files |
| Phase 05 P05 | 10min | 2 tasks | 13 files |
| Phase 05 P06 | 40min | 2 tasks | 8 files |
| Phase 05 P07 | 60min | 2 tasks | 9 files |
| Phase 06 P01 | 11 | 3 tasks | 11 files |
| Phase 06 P02 | 12min | 3 tasks | 4 files |
| Phase 06 P03 | 4min | 2 tasks | 4 files |

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
- [Phase 05]: Phase 5 (Plan 01): Wave-0 red substrate — create_completed_reading/make_user_with_limits helpers (FakeSafety+FakeLLM, no Anthropic) drive the real ReadingService keystone so list/detail/delete tests never re-drive POST; every later endpoint slice has an xfail(strict=False)->xpass target; DB-touching tests skip cleanly without Postgres (83 pass/65 skip baseline+1 from the gate-signature lock).
- [Phase 05]: Phase 5 (Plan 01): HIST-05 consent gate locked "by absence" — test_build_has_no_history_parameter (signature introspection, passes today, no DB) is the regression fence so a v2 author cannot wire prior-reading content into PromptEngine.build silently; the 4 load-bearing invariants + cross-user IDOR-404 each exist as named tests; quota-sensitive + IDOR tests mint a Bearer via encode_jwt(sub,telegram_id) for a make_user_with_limits user so the seeded readings match the JWT identity / a distinct victim.
- [Phase 05]: Phase 5 (Plan 02): history list = GET /api/readings -> light ReadingListItemOut (7 §9.6 fields, NO interpretation, distinct from heavy ReadingOut) via ReadingService.list_readings — two-query no-lazy-load page (select(Reading) join Deck/SpreadType titles + ONE explicit select(ReadingCard) join DeckCard thumbnails grouped by position_index; NO Reading.cards relationship, Pitfall 1); COMPLETED-only + deleted_at IS NULL + user_id from JWT (IDOR T-05-01); FREE_HISTORY_CAP=10 display-cap (effective window min(limit, CAP-offset), offset>=cap->[], older rows RETAINED not pruned, exported in __all__ as the Phase-6/7 tier-limit seam); thin GET router mirrors POST (limit ge=1 le=10 / offset ge=0). Turns 05-01 list red tests green (clean-skip without PG).
- [Phase 05]: Phase 5 (Plan 04): backend history CRUD complete — GET /api/readings/{id} (immutable detail) reuses ReadingService._build_response (reads summary_full JSON + persisted reading_cards, rebuilds transient _card_title/_position_title from explicit select(Card.title)/select(SpreadPosition.title), remaining=None, NO regeneration → two GETs byte-identical); DELETE /api/readings/{id} soft-deletes (deleted_at=now(), retain-data D-04); POST /api/readings/{id}/restore nulls deleted_at (D-03 undo, dedicated explicit route — no deleted_at column leaked over the API, RESEARCH OQ1). Every detail/delete/restore is user-scoped where(id, user_id==user.id[, deleted_at IS NULL]); a non-owned OR deleted id → ReadingInputError → 404 (NOT 403 — no existence leak; closes T-05 HIGH IDOR). uuid.UUID path → 422 on malformed (V5). D-09 reversals source: create_reading resolves reversals_enabled=user.reversals_enabled and threads it into BOTH CardDrawService.draw AND _persist_pending (sig extended to record onto readings.reversals_enabled); the crisis/abusive short-circuit FAILED row records the user flag too; ReadingCreate.reversals_enabled stays accepted but the persisted flag wins. No Reading.cards relationship (Pitfall 1). Zero new deps. Turns 05-01 detail/delete/restore + cross-user-IDOR + reversals_source red tests green (clean-skip without PG; full suite 83 pass/65 skip). Pre-existing ruff UP037 in models/spread.py logged to deferred-items.md (out of scope).
- [Phase 05]: Phase 5 (Plan 06): FE reopen + swipe-to-delete/undo — completes the history experience (browse→reopen→delete/undo). REOPEN (HIST-03): useReadingDetail keyed ["readings","detail",id] staleTime:Infinity (immutable, server never regenerates 05-04); ResultScreen detail mode renders the fetched reading via the SINGLE shared mapReadingOutToMock (createReading imports it, no duplicate mapper) with the opacity fade-in + back→History and NONE of the live CTAs (D-11); per-card+summary content from the immutable GET body, meta (question/deck/spread/date) sourced from the tapped ["readings","list"] cache item. DELETE/UNDO (HIST-04/D-03): deleteReading (DELETE /api/readings/{id}) + restoreReading (POST /{id}/restore) apiFetch wrappers; useDeleteReading = canonical TanStack v5 optimistic mutation (onMutate cancel+snapshot+setQueryData-remove-by-reading_id keeping item+index, onError snapshot rollback) on the SINGLE stable key ["readings","list"] (Pitfall 5 / T-05-STALE); useRestoreReading re-inserts the removed item at its ORIGINAL index in the same key then invalidates to reconcile. UndoSnackbar = motion AnimatePresence + self-contained 5s setTimeout (cleared on unmount/undo via open-keyed effect) — NO toast library. HistoryScreen card = motion drag="x"+dragSnapToOrigin, onDragEnd past 96px leftward threshold commits delete; tap-to-open preserved; an accessible delete-button TWIN calls the same handler (swipe stays accessible + gives the headless test a deterministic trigger — assert cache/DOM outcome not drag physics). delete-button aria-label is a local non-visible const (copy.ts locked this plan; snackbar strings already centralized 05-05; brand-safe). AnimatePresence-exit transient UI → assert dismissal with waitFor (let exit drain the DOM), not a sync query. Zero new deps. Full FE suite 95 green (baseline 92 +3 delete/undo), tsc 0, vite build ok (518 modules). 05-07 (Profile/Settings) is the only remaining Wave-4 plan — sibling, zero overlap.
- [Phase 05]: Phase 5 (Plan 05): FE history/profile navigation foundation + History list slice — Step union extended with OFF-FLOW history|profile|readingDetail (goTo/back only, excluded from STEP_ORDER so next('result') stays terminal; NO react-router — extends the Phase-3 D-02 Zustand step-machine); selection store gains detailReadingId + setDetailReadingId (the History→detail writer seam 05-06 reads); FlowRoot registers all three (readingDetail REUSES ResultScreen, D-02). This foundation plan owns ALL shared FE seams (step union, FlowRoot registry, api/readings.ts, useReadings.ts, ALL new copy) so 05-06/07 replace ONLY their own screen file (Phase-3 FlowRoot-stub pattern, no multi-writer conflict). HistoryScreen = reverse-chrono list via useReadingsList against GET /api/readings (server state, stable key ['readings','list'] — no filters D-01, the Pitfall-5 delete-mutation seam), §9.6 empty state, thumbnails reuse CardArtFallback down-scaled into a 44×70 box (empty→CSS fallback A2), back→Home (D-11), tap→setDetailReadingId+goTo(readingDetail). CatalogScreen header icons → goTo(history)/goTo(profile) (D-10, NO bottom tab bar — ritual/reveal/result stay chrome-free); ResultScreen «история» un-stubbed → goTo(history) (D-10 supersedes Phase-3 D-12 inert stub; «сохранить карточку» stays «скоро» Phase 8). Personalization explainer copy (consumed by 05-07) = «история раскладов»/«колода помнит» + privacy note, NEVER the mechanism (SAFE-06/Pitfall 6). Zero new deps. Full FE suite 87 green (baseline 80 +7), tsc 0, vite build ok. -> SettingsPatch (all-optional 3 booleans, NO user_id) + handler applies only model_dump(exclude_unset=True) keys to current_user, commit, return SettingsOut (PROF-02/D-09). Partial-update invariant (omitted flag untouched); JWT-scoped — forged body user_id dropped by closed schema, mutated row is always the JWT sub (T-05-SPOOF); empty body = 200 no-op. GET /api/me / MeResponse UNCHANGED (PROF-01 already satisfied, count/sub hidden by UI D-08) — only a request schema added. HIST-05/D-06 closed BY ABSENCE: lock comment above PromptEngine.build (no history param/fetch/branch added) + test_build_has_no_history_parameter introspection fence; consent flag persisted but history NEVER assembled into §18 prompt — the personalization feature stays v2/ENG-02. Turns 05-01 settings + gate red tests green (clean-skip without PG).

- [Phase 05]: Phase 5 (Plan 07): FE Profile/Settings + onboarding server-migration — COMPLETES Phase 5 (7/7). me.ts (fetchMe GET /api/me + patchSettings PATCH /api/me/settings over apiFetch, types reused from api/auth.ts); useMe (queryKey ['me'], 60s staleTime) + usePatchSettings = canonical TanStack v5 optimistic mutation on the SINGLE ['me'] key (onMutate cancel+snapshot+merge-patch-into-settings, onError rollback, onSettled invalidate — mirrors the 05-06 delete recipe). ProfileScreen renders the Telegram identity (name+photo, graceful fallback) + reversals/personalization toggles wired to usePatchSettings (only the changed flag PATCHed, optimistic); back→Home (D-11); the readings-count/subscription block is DELIBERATELY omitted even though GET /api/me returns limits (D-08, the component test asserts the count value is absent); personalization explainer brand-safe (SAFE-06, copy from copy.ts, NOT edited). ONBOARDING SERVER-PRIMARY (D-09): FlowRoot gate reads GET /api/me settings.onboarding_completed as the truth, hasSeenOnboarding() localStorage is a BOOT FALLBACK only (no first-paint flash while useMe resolves, direct setState = no phantom back-history), a returning user with a stale-false server flag + localStorage seen triggers EXACTLY ONE reconciling PATCH onboarding_completed=true (reconciledRef-guarded); OnboardingFlow completion (CTA + skip) fires PATCH onboarding_completed=true while keeping markOnboardingSeen() as the boot fallback. REVERSALS SOURCE (D-09): CatalogScreen sources a new reading's reversals_enabled from the persisted GET /api/me flag (useMe), falling back to the local Zustand toggle only until useMe resolves (CTA never network-blocked); backend already enforces this (05-04), client now sends the persisted value for consistency; local toggle retained as a harmless transient fallback. FlowRoot SCREENS registry + CatalogScreen header-icon region (05-05) untouched (disjoint edits, boundary_note honored). Zero new deps. Full FE suite 101 green (baseline 99 +2: onboarding-completion-PATCH + persisted-reversals-source), tsc 0, vite build ok (520 modules). PROF-01/02 already complete (05-03 backend). /gsd-code-review 5 + /gsd-secure-phase 5 remain before phase close (Phase-4 deferral pattern).
- [Phase ?]: Phase 6 (Plan 01): week_start DATE->TIMESTAMP(tz) (A1, user-approved) + UNIQUE(user_id) (A2) in reversible Alembic 0002 (postgresql_using self-heals existing rows). _ensure_user_limits now INSERT ON CONFLICT DO NOTHING with week_start=NULL (D-02, anchors on first reading); _current_week_start removed.
- [Phase ?]: Phase 6 (Plan 01): Wave-0 substrate — committed_seeded_catalog + two_committed_sessions give true cross-connection PG row-lock concurrency (savepoint harness cannot, Pitfall 3). 6 red stubs xfail(strict=False) import Plan-02/03 symbols inside the test body: determine_access/Bucket + ReadingService consume-as-gate+refund + ReadingOut.reason/reset_at (Plan 02); throttle_gate/throttle_ok in app.api.deps (Plan 03). Migration apply = BLOCKING human-verify (no Docker in agent env). Baseline 83 pass preserved (+11 skip +3 xfail).
- [Phase ?]: Phase 6 (Plan 02): atomic free-quota consume = ONE conditional UPDATE user_limits WHERE free_used<limit (OR stale OR null) RETURNING, lazy rolling-7d reset folded in via case() (stale/first_ever/fresh_has_room defined once, reused in WHERE+SET); no-slot via .first() is None (never rowcount), no FOR UPDATE/app lock — the PG row lock IS the success-criterion-3 control.
- [Phase ?]: Phase 6 (Plan 02): consume-as-gate + refund-only-on-honest-fail — safety classify runs BEFORE the atomic consume (crisis/abusive short-circuit pre-gate, zero consume/refund); the consume is the gate before draw; the single post-consume exit (honest-fail) refunds free_used in-transaction so READ-10 holds. All four Phase-4 test_limit_untouched_on_* invariants preserved.
- [Phase ?]: Phase 6 (Plan 02): FE limit-block contract (Plan 04) = HTTP 200 ReadingOut with reason=='paywall' + reset_at=week_start+7d; throttle (Plan 03) is a separate 429 {kind:'throttle'} GATE 0 (D-08, never conflated). determine_access free->subscription->paid; only FREE populated, sub/paid = Phase-7 seam.
- [Phase ?]: 06-03: Redis throttle band locked at 60s window / cap 5 (D-07) — real 30s+ user never throttled; single fixed window, two-tier spacing deferred
- [Phase ?]: 06-03: throttle_gate is GATE 0 on POST /readings only — keys off JWT user.id (T-06), not the DB session, so 429 short-circuits before any Postgres txn

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

Last session: 2026-06-15T20:24:22.792Z
Stopped at: Phase 6 UI-SPEC approved
Resume file: None
Next: 05-07-PLAN.md (FE Profile/Settings — the last Wave-4 / Phase-5 plan; sibling to 05-06, zero overlap)
