# Roadmap: Зеркало Судьбы

## Overview

Зеркало Судьбы ships as **vertical-MVP slices** — each phase delivers an end-to-end, user-visible capability through the full stack (React Mini App → FastAPI → service layer → PostgreSQL), never a horizontal technical layer. The journey: stand up a booting platform with Telegram-validated identity (the security spine), give the user real decks and spreads to browse, build the entire ritual UX end-to-end against a *mock* result, then drop in the keystone — a real, personalized reading from one structured LLM call with the mandatory safety classifier gating generation. From there the dependent slices follow: history, free weekly limits, Telegram Stars monetization, and finally the admin panel, analytics, in-character polish, and a legally-gated deploy to timeweb.cloud. Auth gates everything; limits precede payments; safety lives *inside* the generation slice; the bot module first appears with payments; card draw stays backend-only throughout; the IP/legal gate is last.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation & Telegram Auth** - Repo boots end-to-end and the Mini App knows who the user is (validated `initData` → JWT) (completed 2026-06-10)
- [x] **Phase 2: Deck & Spread Catalog** - User browses 6 distinct decks and 7 spreads with topic-based recommendations and per-deck theming (completed 2026-06-11)
- [x] **Phase 3: The Ritual (mock)** - User runs the entire flow — onboarding → question/topic/deck/spread → ritual → reveal — against a mock reading (completed 2026-06-12)
- [x] **Phase 4: Real Personal Reading (KEYSTONE)** - User gets a real, per-deck personalized reading from one structured LLM call, safely gated
 (completed 2026-06-13)
- [ ] **Phase 5: History & Profile** - User revisits, reopens, and soft-deletes past readings, and manages profile/settings
- [ ] **Phase 6: Free Limits & Soft Paywall** - User is bounded to 3 free readings/week with a deterministic reset and an honest paywall
- [ ] **Phase 7: Telegram Stars Payments** - User buys reading packs or a recurring subscription via Stars to unlock more readings
- [ ] **Phase 8: Admin, Analytics, Polish & Deploy** - Operators run the product without code; the app ships polished and legally cleared on timeweb.cloud

## Phase Details

### Phase 1: Foundation & Telegram Auth

**Goal**: The monorepo boots locally via Docker Compose (PostgreSQL + Redis), the schema and seed are migration-ready, and opening the Mini App produces an authenticated session via server-validated `initData` and a JWT — establishing the security spine and the admin-allowlist seam before any user data exists.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05, AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):

  1. Running `docker compose up` brings up PostgreSQL + Redis + the FastAPI backend, and `GET /healthz` returns healthy (failing fast if a required secret — bot token, DB, Redis, LLM key — is missing)
  2. Alembic migrates the full schema (users, decks, cards, deck_cards, spreads, readings, payments, subscriptions, user_limits, prompt_templates, app_events, generation_logs, etc.) and seed data loads 7 topics, 6 decks, 7 spreads, 78 base cards, and base prompt templates
  3. Opening the Mini App POSTs `initData` to the backend, which validates the two-stage HMAC and `auth_date` freshness, upserts the user, and returns a JWT used as Bearer on every later call
  4. A forged `hash` or a stale `auth_date` is rejected (401), and `telegram_id` is derived only from validated `initData` — never from the request body
  5. Admin-only endpoints reject any caller whose validated `telegram_id` is not in `ADMIN_TELEGRAM_IDS` (server-side `require_admin`)

**Plans**: 5 plansPlans:
**Wave 1**

- [x] 01-01-PLAN.md — Walking Skeleton: docker-compose (Postgres 16 + Redis 7) + FastAPI fail-fast config + /healthz + Wave-0 test harness + Vite/React shell (INFRA-01, INFRA-04)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — SQLAlchemy 2 models + one initial Alembic migration for all 17 tables (16 TZ §13 + topics) (INFRA-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 01-03-PLAN.md — Idempotent seed CLI: 7 topics, 6 decks, 7 spreads+positions, 78 cards, base prompt templates (INFRA-03)
- [x] 01-04-PLAN.md — Security spine: initData two-stage HMAC + JWT + auth endpoint + user upsert + Bearer dep + admin allowlist + soft-error handler (AUTH-01..05, INFRA-05)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 01-05-PLAN.md — Frontend auth wiring: initData → JWT → authenticated state + real-Telegram verify checkpoint (AUTH-01)

### Phase 2: Deck & Spread Catalog

**Goal**: The user can browse the Core-Value substrate — 6 genuinely distinct decks and 7 spreads — with a topic-aware recommendation and per-deck visual theming, served from seeded, IP-clean data (universal `cards` meaning kept separate from deck `deck_cards` style).
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: DECK-01, DECK-02, DECK-03, DECK-04, DECK-05, SPREAD-01, SPREAD-02, SPREAD-03, SPREAD-04, UI-02
**Success Criteria** (what must be TRUE):

  1. The user sees all 6 free decks in a carousel — each with its own name, atmosphere, tone, "for which questions", and preview — backed by `GET /api/decks` and `GET /api/decks/{slug}`
  2. Selecting a deck visibly changes the app's background, accent, microcopy, and particles (per-deck palette from the 6 themes)
  3. The user sees all 7 spreads (3–4 cards) with positions, and choosing a topic surfaces a recommended spread (with a reason) via `GET /api/spreads` and `/api/spreads/recommend`, honoring deck↔spread compatibility
  4. A card with no uploaded art still renders with an atmospheric CSS/SVG fallback in its image/thumbnail/back slots (no broken images)
  5. Seed data contains only original deck names and style-free universal card meanings — no RWS/commercial deck references

**Plans**: 3 plans
Plans:

**Wave 1** *(parallel — zero file overlap; execute-phase runs them sequentially)*

- [x] 02-01-PLAN.md — Backend catalog: SpreadType.positions relationship + seed deck_spread_compatibility from §7 + Pydantic schemas + CatalogService + GET /api/decks, /api/decks/{slug}, /api/spreads, /api/spreads/recommend + DB tests (DECK-01..04, SPREAD-01..04)
- [x] 02-02-PLAN.md — Frontend foundation: mount QueryClientProvider + Zustand selection store + per-deck theming (data-deck + 6 CSS-var palettes) + DECK-05 CSS/SVG null-art fallback + RTL test harness (UI-02, DECK-05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-03-PLAN.md — Frontend catalog UI: TanStack Query hooks + DeckCard carousel/SpreadCard/TopicChip + CatalogScreen (selection + live theming + recommendation) wired into App (DECK-01/03, SPREAD-01/03, UI-02)

**UI hint**: yes

### Phase 3: The Ritual (mock)

**Goal**: The user can complete the entire emotional journey — skippable onboarding, the question→topic→deck→spread selection flow, the shuffling-ritual prep screen, and the staggered flip-reveal of cards — end to end against a *mock* reading, locking the UX and animation contract before any LLM is wired in.
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: ONB-01, ONB-02, ONB-03, ONB-04, HOME-01, HOME-02, HOME-03, HOME-04, HOME-05, HOME-06, HOME-07, READ-07, READ-08, READ-09, SAFE-06, UI-01, UI-03, UI-04
**Success Criteria** (what must be TRUE):

  1. On first launch the user sees a 3–4 screen onboarding (including a plain-language, non-scary reversed-cards explainer) that can be skipped and is not shown again once completed
  2. The user enters a question in their own words (10–500 chars, or empty for a general reading), picks one of 7 topics, a deck, and a spread, with gentle prompts when something is missing or too short
  3. Tapping "Начать расклад" plays the ritual prep ("hears the question / shuffling / near you") with dimming, particles, and a completion haptic, then reveals cards one by one with flip animation and "open all" after the first
  4. The result screen shows question/topic/deck/spread/date, card cards, an overall summary, and "save card / another reading / history" actions — all populated from a mock result
  5. The premium-dark mobile-first UI (360–430px) with a sticky bottom CTA adapts to Telegram light/dark theme and safe-area insets (via SDK insets), and no UI string contains "AI / нейросеть / модель / сгенерировано ИИ"

**Plans**: 6 plans
Plans:

**Wave 1**

- [x] 03-01-PLAN.md — Flow spine: Zustand step-machine (D-02/03/04/13) + FlowRoot (MotionConfig reducedMotion=never + LazyMotion + AnimatePresence) + telegram.ts theme/safe-area/haptics (UI-04) + MockReading type + createReading() seam (D-05) + card-pool fixture (D-06) + reversals draw (D-07) + copy module (SAFE-06) + onboarding flag (ONB-04) + 4 screen stubs (HOME-01/02/07, READ-08/09, UI-03/04, SAFE-06, ONB-04)

**Wave 2** *(parallel — zero file overlap; all depend on 03-01)*

- [x] 03-02-PLAN.md — Onboarding: 3–4 skippable slides + reversed-cards explainer + first-reading CTA (ONB-01/02/03/04, SAFE-06)
- [x] 03-03-PLAN.md — Selection: question input (10–500/empty-valid/too-short hint) + topic/deck/spread + recommendation + gated «Начать расклад» → createReading → ritual; keyboard-safe sticky CTA (HOME-01..07, UI-01/04, SAFE-06)
- [x] 03-04-PLAN.md — Ritual prep: ~3s 3-beat timeline + dimming + compositor-only particles + completion haptic + tap-to-skip + art preload (READ-07, UI-01/03)
- [x] 03-05-PLAN.md — Flip-reveal: 3D rotateY FlipCard + tap-to-flip + «Раскрыть все» stagger + per-card phrase + per-flip haptic (READ-08, UI-01/03)
- [x] 03-06-PLAN.md — Result: question/topic/deck/spread/date + per-card glass cards + summary panel + «Ещё расклад» wired (D-04) + save/история stubbed (D-12) (READ-09, UI-01/03, SAFE-06)

**UI hint**: yes

### Phase 4: Real Personal Reading (KEYSTONE)

**Goal**: The Core Value goes live — the user receives a real, deeply personalized reading where the same question genuinely feels different per deck. Backed by backend-only crypto card draw, the mandatory safety classifier (crisis short-circuits *before* draw/charge), versioned prompt assembly, and one synchronous structured LLM call returning all card interpretations plus the summary as schema-validated JSON, with retry/timeout/DB-fallback and no limit consumed on failure.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: READ-01, READ-02, READ-03, READ-04, READ-05, READ-06, READ-10, READ-11, SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, ANALYTICS-02
**Success Criteria** (what must be TRUE):

  1. `POST /api/readings` draws cards server-side with a CSPRNG (reversals off → all upright; on → 70/30 upright/reversed), ignoring any client-supplied cards, and returns a real reading with per-card interpretation (name, position, orientation, short + deep meaning, deck mystical accent) and a connected summary
  2. The same question on two different decks produces noticeably different tone, imagery, and structure — and no result text mentions "AI / нейросеть / модель"
  3. A crisis question (self-harm, violence) returns a supportive safe response with a suggestion to reach a real person/helpline — never a mystical prediction, and with no card draw or charge; sensitive topics get a softened safety-modified reading; no categorical or fatalistic predictions appear
  4. When the model returns invalid JSON or times out, the user sees a soft in-character error, the reading is marked failed, and the user's limit is NOT consumed (after exactly one corrective retry, then DB fallback)
  5. Every generation writes `prompt_version`, model, input/output tokens, latency, status, and any error to `generation_logs`

**Plans**: 6 plans
Plans:

**Wave 0**

- [x] 04-01-PLAN.md — Foundation: add anthropic+tenacity (legitimacy checkpoint) + schemas/reading.py contracts (ReadingOutput/SafetyVerdict/ReadingCreate/ReadingOut) + AsyncAnthropic client + 9 Wave-0 test stubs + fake_llm/fake_safety/seeded_catalog fixtures (READ-03/05/06, SAFE-01)

**Wave 1** *(parallel — zero file overlap; all depend on 04-01)*

- [x] 04-02-PLAN.md — CardDrawService (backend-only CSPRNG draw, 70/30 orientation, D-13) + backend brand guard (SAFE-06 port) (READ-02, READ-11, SAFE-04/05)
- [x] 04-03-PLAN.md — LLMService (messages.parse + tenacity 1-retry Haiku→Sonnet + timeout + usage) + SafetyService (regex pre-filter + Haiku classify → SafetyVerdict + routing) (READ-03/04, SAFE-01/02/04/05)
- [x] 04-04-PLAN.md — PromptEngine (fused §17+§18 single-call prompt + D-02 per-deck signatures + safety_modifier + prompt_version) + prompts.json content (generic D-04 refusal, D-06 redirect, signatures) (READ-03/05/06/11, SAFE-02/03/04/05)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-05-PLAN.md — ReadingService.create_reading orchestration (gate→draw→generate→consume, honest fail D-09, generation_logs, DB mapping) + POST /api/readings router (READ-01/03/04/05/06/10/11, SAFE-01/02/03, ANALYTICS-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 04-06-PLAN.md — Frontend seam swap (createReading → POST /api/readings via apiFetch, ReadingOut→MockReading) + failure UX (Повторить + Сменить колоду, D-07/D-08) + manual UAT (per-deck felt-quality, live smoke, crisis tone) (READ-01, READ-11)

**UI hint**: yes

### Phase 5: History & Profile

**Goal**: The user can revisit their journey — every reading auto-saves to a browsable, paginated history with detail view and soft delete (reading immutable stored cards, never regenerating) — and can manage their profile and settings, including the explicit opt-in before any history-based personalization.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: HIST-01, HIST-02, HIST-03, HIST-04, HIST-05, HIST-06, PROF-01, PROF-02
**Success Criteria** (what must be TRUE):

  1. Each completed reading appears automatically in history showing date, question, deck, spread, card thumbnails, and a short summary, via `GET /api/readings` with pagination/filters
  2. The user can reopen any past reading in full detail (`GET /api/readings/{id}`) and the displayed content matches what was originally generated (no regeneration)
  3. The user can delete a reading (soft delete via `deleted_at`) and it disappears from the list
  4. The user sees their profile (`GET /api/me`: Telegram name, available-readings count, subscription, settings) and can change settings (`PATCH /api/me/settings`: reversals toggle, history-personalization consent, onboarding flag)
  5. History is not used for personalization unless `allow_history_personalization` is explicitly enabled, and free history retains the last 10 readings

**Plans**: 7 plans
Plans:

**Wave 0**

- [x] 05-01-PLAN.md — Wave-0 test substrate: shared `create_completed_reading` helper + 5 new red test files + cross-user(IDOR)/`/me` extensions (HIST-01..06, PROF-01/02)

**Wave 1** *(parallel — zero file overlap; all depend on 05-01)*

- [x] 05-02-PLAN.md — Backend history list: `ReadingListItemOut` + `ReadingService.list_readings` (user-scoped, soft-delete-excluding, COMPLETED-only, `FREE_HISTORY_CAP=10`) + `GET /api/readings` (HIST-01/02/06)
- [x] 05-03-PLAN.md — Backend settings + consent gate: `SettingsPatch` + `PATCH /api/me/settings` (partial, JWT-scoped) + HIST-05/D-06 closed-gate lock (PROF-01/02, HIST-05)

**Wave 2** *(blocked on Wave 1)*

- [x] 05-04-PLAN.md — Backend detail/delete/restore: immutable `GET /api/readings/{id}` (reuse `_build_response`) + soft-delete `DELETE` + `POST /{id}/restore` + IDOR 404 + D-09 reversals-source (HIST-03/04, PROF-02)

**Wave 3** *(blocked on 05-02; FE foundation + first FE slice)*

- [x] 05-05-PLAN.md — FE foundation + History list: step-machine + FlowRoot stubs + `useReadingsList`/`fetchReadings` + all brand-safe copy + History screen + Home/Result entry points (HIST-01/02/06)

**Wave 4** *(parallel — zero file overlap; depend on 05-05 + their backend)*

- [x] 05-06-PLAN.md — FE reopen + delete/undo: `ResultScreen` detail mode (immutable, fade-in) + swipe-to-delete + `UndoSnackbar` (optimistic delete/restore) (HIST-03/04)
- [ ] 05-07-PLAN.md — FE Profile/Settings: identity + toggles (optimistic `PATCH`, count hidden D-08) + onboarding localStorage→server migration + reversals-source (PROF-01/02)

**UI hint**: yes

### Phase 6: Free Limits & Soft Paywall

**Goal**: Free usage is bounded so monetization becomes meaningful — the user gets 3 free readings per week with a deterministic, anchored weekly reset and atomic check+decrement (no over-spend under concurrency), a Redis throttle against abuse, and an honest, non-pushy paywall surface when free access is exhausted.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: LIMIT-01, LIMIT-02, LIMIT-03, LIMIT-04, LIMIT-05
**Success Criteria** (what must be TRUE):

  1. After 3 free readings in a week the user is blocked from a 4th free reading and instead sees a soft, in-character paywall (no fear or pressure)
  2. The free counter resets based on a stored `week_start` (ISO week, UTC), so a user at the boundary gets exactly 3 per week — not extra
  3. Two concurrent reading requests at the limit boundary cannot both succeed (atomic check+decrement); free, paid-balance, and subscription quotas are counted as three independent buckets
  4. Burst spamming of reading creation is throttled via Redis before it reaches Postgres
  5. Before each reading the backend determines access (free / paid balance / subscription) and only consumes from the correct bucket

**Plans**: TBD
**UI hint**: yes

### Phase 7: Telegram Stars Payments

**Goal**: The user can pay to keep reading — buying 1/3/10-reading packs or a native recurring 30-day "Лунный доступ" subscription through Telegram Stars. This is the first slice using the in-process aiogram bot module; entitlement is granted only after a Telegram-confirmed `successful_payment`, idempotently by `payload`, with a fast pre-checkout, refunds, and a server-side entitlement window as the source of truth.
**Mode:** mvp
**Depends on**: Phase 6
**Requirements**: PAY-01, PAY-02, PAY-03, PAY-04, PAY-05, PAY-06, PAY-07, PAY-08
**Success Criteria** (what must be TRUE):

  1. The user sees products/tariffs (`GET /api/products`: 1/3/10 packs + subscription), taps one, and receives a Telegram Stars (XTR) invoice carrying a `payload` (user_id, product_id, purchase_type, idempotency_key)
  2. After a successful Stars payment the user's `paid_spreads_balance` or subscription is granted and immediately usable, with `telegram_payment_charge_id` stored; `pre_checkout_query` is answered within 10s using fast indexed checks only
  3. The same `successful_payment` delivered twice grants access exactly once (`payload`/`charge_id` UNIQUE); entitlement is never granted on invoice creation or pre-checkout
  4. The subscription is a native recurring Stars subscription (`subscription_period=2592000`) backed by a server-side 30-day entitlement window; renewals (`is_recurring`) extend it idempotently and cancellation keeps access until period end; refunds (21-day window) flip the payment to refunded and adjust access
  5. The user sees clear tariff and success UI, and on failure gets an understandable message that stars were not charged / access was not granted

**Plans**: TBD
**UI hint**: yes

### Phase 8: Admin, Analytics, Polish & Deploy

**Goal**: Operators can run and tune the product without code — allowlisted admin CRUD over decks/cards/prompts/spreads/products with versioned prompt toggles (the production safety valve for generation), views of users/readings/payments/generation-logs, and a metrics dashboard — and the app ships polished: full analytics event coverage, in-character error/empty states, a privacy-safe share-card, deployed over HTTPS to timeweb.cloud behind a legal/IP review gate before public launch.
**Mode:** mvp
**Depends on**: Phase 4, Phase 7
**Requirements**: ADMIN-01, ADMIN-02, ADMIN-03, ADMIN-04, ADMIN-05, ADMIN-06, ADMIN-07, ADMIN-08, ADMIN-09, ANALYTICS-01, UI-05, UI-06
**Success Criteria** (what must be TRUE):

  1. An allowlisted operator can, via the admin UI, CRUD decks/cards/deck_cards/spreads/products and toggle decks/spreads on/off, and create/activate/roll back prompt-template versions (quick-disable a bad version)
  2. The operator can view users, readings, payments, and generation logs/errors, and a dashboard shows users total/today, readings today/week, payment conversion, revenue (Stars), popular deck/topic, generation error rate, and average latency
  3. Key product events (app_opened, onboarding_*, question/topic/deck/spread_selected, reading_started/completed/failed, card_revealed, summary_viewed, history_opened, paywall_viewed, product_clicked, payment_*, subscription_started, settings changes) are logged to `app_events`
  4. The user can generate a privacy-safe share-card (deck background, 3–4 cards, spread name, short summary) that excludes the personal question by default, and every empty/error/loading state is rendered in product voice (no stack traces)
  5. The app is deployed and reachable over HTTPS on timeweb.cloud (Mini App opens, bot webhook reachable), with Stars verified in test mode and a documented legal/IP review of deck assets completed before public launch

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Telegram Auth | 5/5 | Complete   | 2026-06-10 |
| 2. Deck & Spread Catalog | 3/3 | Complete    | 2026-06-11 |
| 3. The Ritual (mock) | 6/6 | Complete    | 2026-06-12 |
| 4. Real Personal Reading (KEYSTONE) | 6/6 | Complete    | 2026-06-13 |
| 5. History & Profile | 5/7 | In Progress|  |
| 6. Free Limits & Soft Paywall | 0/TBD | Not started | - |
| 7. Telegram Stars Payments | 0/TBD | Not started | - |
| 8. Admin, Analytics, Polish & Deploy | 0/TBD | Not started | - |
