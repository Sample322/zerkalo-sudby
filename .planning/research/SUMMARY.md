# Project Research Summary

**Project:** Зеркало Судьбы — Telegram Mini App for AI tarot readings
**Domain:** Telegram Mini App — concealed-LLM tarot/oracle ritual with per-deck "personality" and Telegram Stars monetization
**Researched:** 2026-06-09
**Confidence:** HIGH

## Executive Summary

This is a **content-and-prompt-driven Telegram Mini App** that dresses a single LLM call up as a mystical ritual. The expert way to build it is well-established and the four research tracks converge cleanly: a thin async **FastAPI** backend (with the **aiogram** bot running *in-process*, not as a separate service), a small **React 19 + Vite + Tailwind v4 + Zustand + TanStack Query** SPA, **PostgreSQL** for all durable state, **Redis** for rate-limits/cache only (no queue), and **Claude Haiku 4.5** as the default model behind a swappable LLMService. The reading is produced by **one structured LLM call** (Anthropic Structured Outputs, now GA via messages.parse) returning all card interpretations plus the summary as one validated JSON object — roughly 4-5x cheaper and faster than per-card calls, and it eliminates cross-card tone drift. The whole high-value path is **synchronous**: the ritual animation masks 2-6s of latency over data that is already complete.

The recommended approach is **vertical-MVP slicing** — each phase ships an end-to-end, user-visible capability rather than a horizontal layer. Auth gates everything; seed/catalog APIs precede the selection UX; the UX ritual is built end-to-end against a *mock* result first, then the real LLM call is dropped in. The **real-reading slice is the keystone** that history, limits, payments, and admin all depend on. Two things make this product defensible and the roadmap exists to protect them: (1) **6 decks that genuinely change the same answer** (the Core Value — driven by per-deck prompt_modifier + theming + microcopy, not just a skin), and (2) **AI concealed inside a ritual** rather than sold as "AI tarot."

The dominant risks are concentrated and known. **Safety is first-class and mandatory**: a cheap regex pre-filter plus a safety_category field in the structured call must gate generation; crisis topics short-circuit *before* any draw/charge into a supportive response, never a mystical forecast. **initData HMAC validation and Stars idempotency** are the security spine — a spoofed telegram_id or a double-granted payment is catastrophic, and both have exact, verified algorithms that must be implemented precisely (the two-stage HMAC and the successful_payment-only, payload-UNIQUE grant). **LLM robustness** (low temperature, one corrective retry, hard timeout, DB fallback, and never consuming the user's limit on failure) turns the single-call design from fragile to production-grade. Get these right and the rest is conventional Mini App engineering.

## Key Findings

### Recommended Stack

The stack is the one locked in PROJECT.md, version-pinned and verified against official docs/registries as of June 2026. Two corrections changed earlier assumptions and must be carried into the roadmap. **framer-motion no longer exists under that name** — install **motion@12** and import { motion } from "motion/react". And **native recurring Telegram Stars subscriptions ARE available** (subscription_period=2592000 = exactly 30 days), so the recommendation is native recurring billing *with* a server-side 30-day entitlement window as the source of truth — superseding the "manual renewal if API unavailable" hedge in decision #7. See STACK.md for exact install commands, the hand-rolled initData HMAC, the Stars flow, and the messages.parse structured-output pattern.

**Core technologies:**
- **React 19.2 + Vite 7 + TypeScript 5.7 + Tailwind v4** — small SPA; Tailwind v4 CSS-first @theme tokens map cleanly to the 6-deck palette requirement. (Use Vite 7, not 8/Rolldown, until plugin compat is confirmed post-MVP.)
- **motion 12** (ex-framer-motion) — flip/shuffle/reveal animation; compositor-friendly props only.
- **Zustand 5 + TanStack Query 5** — client/draft state vs server state; never duplicate server state into Zustand.
- **FastAPI 0.136 + Python 3.12 + SQLAlchemy 2.0 async + asyncpg + Alembic + Pydantic 2.10** — async-native API; the whole reading flow is async I/O.
- **aiogram 3.27** — Telegram bot framework with full Stars support; runs **in-process** inside FastAPI via feed_webhook_update, not as a separate service.
- **PostgreSQL 16 + Redis 7** — Postgres is the source of truth (15-16 tables); Redis for weekly-limit counters, throttle, and catalog/card-meaning cache only — **no Celery/RQ/Arq**.
- **anthropic SDK >=0.69 + Claude Haiku 4.5 (default, ~0.01 USD/reading)** — behind a swappable LLMService; escalate to **Sonnet 4.6** for premium/deep decks or as an automatic retry on validation failure. Use **Structured Outputs** (messages.parse(output_format=PydanticModel)) for one validated JSON; GA, no beta header needed.
- **tenacity** (bounded retry + timeout, replaces the queue), **PyJWT** (session bearer after initData), **ruff/pytest/Vitest/Playwright** (quality).

### Expected Features

FEATURES.md categorizes the locked TZ scope against the wider market. The field is crowded with single-voice tarot apps and overtly-"AI psychic chat"; the two scarce, defensible wedges here are **multiple decks that meaningfully change the same answer** and **AI concealed inside a ritual**.

**Must have (table stakes):**
- Frictionless Telegram auth (no registration) — the "fast first impression" thesis and the root all gated features hang off.
- Main selection flow: question -> topic -> deck -> spread -> recommendation -> start.
- Per-card interpretation + connected overall summary (one structured LLM call).
- Server-side secure card draw + 70/30 reversed mechanic (toggleable).
- Reading history (list/detail/soft-delete); free weekly limit (3/week) + honest soft paywall.
- Telegram Stars: 1/3/10 packs + subscription; invoice -> pre_checkout -> successful_payment -> grant; refunds; idempotency.
- Admin panel (CRUD decks/cards/spreads/prompts/products, toggles, view users/readings/payments/gen-logs) — **first-class**, since the differentiator is *edited here*.
- Analytics events + core metrics (needed day 1 to validate the core hypothesis).
- **Safety classifier + crisis handling + no-categorical-predictions + disclaimers** — promoted to mandatory (decision #3); duty-of-care, not optional polish.

**Should have (competitive / differentiators):**
- **6 decks with distinct prompt modifiers + theming (the product)** — per-deck tone/structure/vocabulary, not a reskin; the one acceptance criterion the whole roadmap protects.
- Ritual reveal sequence + per-deck atmosphere engine (the anti-"AI chat" lever).
- Privacy-safe share-card (question hidden by default) — organic growth without a social graph.

**Defer (v1.x / v2+):**
- Region-aware crisis resources, "report answer" UI surfaced prominently, pricing experiments, reading thumbs, bespoke per-deck art (slots already supported).
- Push "card of the day", deep 5-7 card spreads, premium/seasonal decks, voice/post-reading chat, cross-reading memory, referrals, marketplace — all post-PMF and several are explicit **anti-features** (social feed, public profiles, on-the-fly art generation, background queue, external acquiring, native apps).

### Architecture Approach

ARCHITECTURE.md translates the spec into **one deployable backend process** hosting the REST API, the in-process aiogram dispatcher, and the guarded admin API, with a **thin-routers / thick-services** split so the same PaymentService/LimitService serve REST, webhook, and admin entry points. The data model deliberately splits **universal card meaning (cards)** from **deck-specific style (deck_cards)** — this is what enables "same card, different deck" *and* keeps IP clean. Build order is **vertical-MVP slices**, each an end-to-end capability.

**Major components:**
1. **React Mini App** — all UI, ritual animation, progressive reveal over already-ready data.
2. **REST API (thin) + in-process aiogram dispatcher** — HTTP contract + Telegram payment updates, both delegating to services; Telegram POSTs to one secret-token-guarded webhook route.
3. **Service layer (thick)** — TelegramAuth, CardDraw (CSPRNG), Reading (orchestrates the single transaction + single LLM call), PromptEngine (versioned DB templates), Safety (gates generation), LLMService (swappable), Limit, Payment/Subscription, Analytics.
4. **PostgreSQL** (all durable state) + **Redis** (throttle/cache, not a queue) + **LLM provider** (synchronous in-request call).

### Critical Pitfalls

Top risks from PITFALLS.md, each with a verified prevention:

1. **initData validation done wrong -> auth bypass.** Never trust initDataUnsafe/body telegram_id. Implement the two-stage HMAC exactly (secret = HMAC_SHA256("WebAppData", bot_token), sorted key=value joined by newline excluding hash, constant-time compare), reject stale auth_date, derive id only from validated initData. Test with forged-hash and stale-date fixtures.
2. **Stars double-grant / wrong-event grant.** Grant entitlement **only** in successful_payment (never pre_checkout), idempotent via payments.payload UNIQUE + indexed telegram_payment_charge_id, in one transaction. pre_checkout_query must answer within **10s** with fast indexed checks only.
3. **Crisis question gets a mystical reading.** Prompt-only safety is unreliable. Regex pre-filter short-circuits crisis *before* draw/charge into a safe supportive template; the structured call also emits safety_category; banned-phrase post-filter as a final net. Ships *inside* the generation slice, not later.
4. **LLM cost/JSON blowup.** One structured call per reading (not per card), low temp + max_tokens + per-field caps, base meanings passed in from DB (not re-derived), **token logging in generation_logs from day one**. On invalid JSON: one corrective retry -> DB fallback -> soft error, and **never consume the user's limit on failure**.
5. **Frontend card draw / non-CSPRNG / non-atomic limits.** Draw + orientation backend-only via secrets; POST /api/readings ignores client-supplied cards. Make check+decrement atomic (UPDATE ... WHERE used < limit RETURNING), anchor the weekly reset to a stored week_start (ISO week, UTC).

(Also tracked: brand-voice leaks via output filter, deck-IP separation enforced in schema + legal gate before public launch, reversed-card anxiety via 70/30 + reframing, subscription model clarity, iOS viewport/safe-area insets.)

## Implications for Roadmap

Research strongly endorses a **vertical-MVP slice** structure (each phase = an end-to-end user capability). The TZ stage plan (section 23) and the architecture build order agree. Suggested phases:

### Phase 0: Walking Skeleton
**Rationale:** Every slice rides on a booting platform; cheap to stand up, expensive to retrofit.
**Delivers:** Repo boots — Mini App opens, /healthz answers, Postgres + Redis up via Docker Compose, Alembic ready.
**Uses:** Docker Compose, FastAPI shell, Vite SPA shell.
**Avoids:** Late discovery of timeweb manual-provisioning / HTTPS constraints (flag deploy details now, decide at Phase 9).

### Phase 1: It knows who I am (Auth)
**Rationale:** Auth gates everything — no identity, no per-user reads/limits/payments. This is the security spine.
**Delivers:** Open Mini App -> authenticated -> profile via /api/me; JWT issued; require_admin allowlist seam established.
**Uses:** Telegram WebApp SDK, hand-rolled initData HMAC, PyJWT.
**Avoids:** Pitfall 1 (initData spoofing) — forged-hash + stale-auth_date rejection tests are acceptance criteria here.

### Phase 2: I can browse decks and spreads (Catalog + Seed)
**Rationale:** The home flow needs real decks/spreads to render; recommendation needs deck_spread_compatibility. Seed data is the Core-Value substrate.
**Delivers:** 6 decks, 7 spreads, topic-based recommendation; per-deck theming tokens land here.
**Implements:** Deck/Spread services; cards vs deck_cards separation; seed scripts.
**Avoids:** Pitfall 7 (IP) — enforce style-free cards, original names only, no RWS/commercial references in seed.

### Phase 3: I can run the whole ritual (mock) (UX shell)
**Rationale:** Deliberate vertical-slice move — lock the ritual UX + animation contract *before* wiring the LLM, de-risking animation-timing-vs-latency independently of prompt tuning.
**Delivers:** Onboarding, home, question/topic/deck/spread selection, ritual prep + reveal screens against a mock result.
**Uses:** motion 12, Zustand reading-draft store, per-deck palettes.
**Avoids:** Pitfall 11 (reversed-card anxiety — explainer + toggle) and viewport/safe-area iOS issues.

### Phase 4: I get a real, personal reading — KEYSTONE
**Rationale:** The Core Value and the highest product+technical risk. Everything downstream assumes a working readings write path.
**Delivers:** Real POST /api/readings — CardDraw (CSPRNG) + Reading orchestration + PromptEngine + **Safety classifier (incl. crisis short-circuit)** + LLMService + JSON-schema validation, one synchronous structured call, per-deck voice.
**Uses:** anthropic messages.parse, Haiku 4.5 default, tenacity timeout/retry.
**Avoids:** Pitfalls 4 (crisis safety — ships *inside* this slice), 5 (single call + token logging), 6 (retry/timeout/fallback, no limit-consume on failure), 8 (backend-only draw), 10 (output brand-voice filter).

### Phase 5: I can revisit past readings (History)
**Rationale:** Immediately follows generation; reads immutable reading_cards, never regenerates.
**Delivers:** History list/detail/soft-delete + opt-in personalization toggle.

### Phase 6: I am limited to 3 free/week (Limits + Paywall)
**Rationale:** A paywall is meaningless until free access is bounded; must precede payments.
**Delivers:** LimitService (atomic check+decrement, deterministic weekly reset, Redis throttle) + honest soft paywall UI.
**Avoids:** Pitfall 9 (weekly-reset bugs, TOCTOU over-spend).

### Phase 7: I can buy more / subscribe (Telegram Stars)
**Rationale:** First slice needing the in-process bot module; depends on limits (what to top up) and products.
**Delivers:** Products + PaymentService + create-invoice (REST) + in-process aiogram webhook (pre_checkout/success/refund) + **native recurring 30-day subscription** with server-side entitlement window + tariffs UI.
**Avoids:** Pitfalls 2 (double-grant idempotency), 3 (10s pre_checkout), 12 (recurring-vs-window subscription modeling — choose native recurring, model it exactly).

### Phase 8: Operators can run it without code (Admin)
**Rationale:** Admin reads payments/generation-logs (must exist) and its prompt/deck toggles are the production safety valves for the generation path.
**Delivers:** Admin routers behind allowlist + admin UI for decks/cards/prompts/products, generation-logs, dashboards, toggles.

### Phase 9: Polish and Deploy
**Rationale:** Cross-cutting hardening once features exist.
**Delivers:** In-character error/empty/loading states, mobile pass, Sentry/metrics, timeweb.cloud deploy, Stars test-mode verification, Telegram theme reactivity, **IP/legal gate before public launch**.

### Phase Ordering Rationale

- **Auth -> Catalog -> Mock-UX -> Real-reading** is dependency-forced *and* risk-optimal: it stands up the security spine first, then de-risks the ritual UX before the LLM, so the keystone slice is fill-in-real-data.
- **Generation is the keystone:** history, limits, payments, and admin all require a working readings write path; the schema and services they touch are introduced here.
- **Limits before Payments:** a paywall only matters once free usage is capped (TZ stages 7 -> 8 confirm).
- **Safety is folded into Phase 4, not trailed:** retrofitting crisis handling is the classic divination-app failure; it is cheap inside the single structured call and liability-critical.
- **Admin after Payments:** it reads payment/generation tables and provides the operational kill-switches (toggle deck/spread, swap active prompt version).

### Research Flags

Phases likely needing deeper research during planning (/gsd-plan-phase --research-phase N):
- **Phase 4 (Real reading):** prompt engineering + JSON-schema design for a single combined call (all cards + summary), the cheap safety-classifier approach (regex pre-filter vs. folding safety_category into the call), and the retry/timeout/fallback contract. Highest product + technical risk.
- **Phase 7 (Payments):** exact aiogram Stars surface for the in-process webhook, refund semantics (21-day window), and **native recurring** subscription modeling (subscription_period=2592000, is_recurring renewals, editUserStarSubscription cancel-at-period-end).
- **Phase 1 (Auth):** Telegram-validated CSP / connect-src for the WebView and JWT-in-WebView storage (light, but worth confirming).

Phases with standard patterns (can likely skip research-phase):
- **Phase 0 (Skeleton), Phase 2 (Catalog CRUD/seed), Phase 5 (History CRUD), Phase 8 (Admin CRUD):** conventional FastAPI + SQLAlchemy + React patterns, well-documented.
- **Phase 6 (Limits):** the *pattern* is standard; the atomicity + weekly-reset *details* are already specified in PITFALLS — implement to that.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against official docs / npm / PyPI / Telegram Bot API as of June 2026; LLM verified on platform.claude.com. The framer-motion to motion rename and native recurring Stars are confirmed. |
| Features | HIGH | Table stakes + monetization + safety verified against live apps, Telegram docs, and tarot-ethics sources. Differentiator framing MEDIUM-HIGH (validated by tarot-community sources on deck personality). |
| Architecture | HIGH | Component boundaries, data flows, vertical build order grounded in TZ sections 12/13/14/23/29 and verified Telegram/aiogram patterns (feed_webhook_update single-process viability confirmed). |
| Pitfalls | HIGH | Telegram protocol pitfalls (initData, Stars, subscriptions) HIGH against official docs; LLM-cost/JSON and viewport/CSS MEDIUM (practitioner sources + official viewport docs); IP/safety MEDIUM (domain reasoning grounded in TZ sections 5/20). |

**Overall confidence:** HIGH

### Gaps to Address

- **Per-deck differentiation strength is the product existence proof, but unverified empirically.** The Core Value assumes 6 decks *feel* meaningfully different on the same question. Handle during Phase 4 planning: treat decks-feel-different as a cross-cutting acceptance criterion (generation + theming + reveal), and plan A/B/blind testing of deck outputs (TZ section 25.2) plus a reading-rating signal in v1.x.
- **Single-call latency under concurrency.** The synchronous LLM call holds a worker open; fine at MVP scale but the first bottleneck. Mitigation order is known (response-length caps + token logging -> provider concurrency tuning -> only then revisit no-queue). Wire token/latency logging in Phase 4; do not pre-build a queue.
- **Subscription model decision must be made before schema usage.** Research recommends **native recurring** (now confirmed available), but the roadmap/Phase-7 plan must lock native-recurring-vs-manual-window explicitly and model exactly one — not a hybrid.
- **iOS viewport/safe-area inside Telegram is MEDIUM-confidence.** env(safe-area-inset-*) is unreliable in the Telegram WebView; verify SDK insets + viewportStableHeight on a notched device during Phase 3/9 (bottom CTA / Pay reachability with keyboard open).
- **timeweb.cloud deploy specifics deferred by design.** MCP only does App Platform git deploy; managed PG/Redis/S3 + VPS are provisioned manually. Resolve at Phase 9; keep Docker Compose as the local-dev source of truth for parity.

## Sources

### Primary (HIGH confidence)
- platform.claude.com/docs — Structured Outputs GA (messages.parse, output_config.format), Haiku 4.5 1/5 USD and Sonnet 4.6 3/15 USD per MTok, model support.
- core.telegram.org/bots/webapps — initData HMAC algorithm (secret = HMAC_SHA256(WebAppData, bot_token)), auth_date freshness, initDataUnsafe warning, themeParams, viewport/safe-area.
- core.telegram.org/bots/payments-stars + /api/subscriptions + /bots/api-changelog — Stars flow, answerPreCheckoutQuery 10s rule, telegram_payment_charge_id, refundStarPayment (21-day), subscription_period=2592000, is_recurring/is_first_recurring/subscription_expiration_date, editUserStarSubscription.
- docs.aiogram.dev (3.27) — create_invoice_link (XTR, empty provider_token, single LabeledPrice), pre_checkout_query, refund_star_payment, edit_user_star_subscription, feed_webhook_update (single-process viability).
- motion.dev — package rename framer-motion to motion, import { motion } from motion/react.
- npm / PyPI registries (June 2026) — React 19.2, TanStack Query 5, Zustand 5, Vite 7/8, Tailwind v4, FastAPI 0.136, SQLAlchemy 2.0, asyncpg 0.30, Pydantic 2.10.
- .planning/REFERENCE-TZ.md + PROJECT.md — source of truth for scope, data model (15-16 tables), API, prompt system, safety (section 20), stages (section 23), services (section 29), MVP (sections 24/30), and locked decisions 1-7.

### Secondary (MEDIUM confidence)
- Tarot/oracle app baselines (Labyrinthos, Tarotoo, Aura, Co-Star) — table-stakes feature set and freemium/a-la-carte monetization.
- Telegram Mini Apps monetization guides (Merge, OmiSoft, Nadcab) — consumables/subscriptions, soft paywall, bundle uplift, weekly-over-annual conversion (vendor blogs, directionally consistent).
- LLM structured-output reliability (apxml, dev.to) — low temp + one corrective retry lifts parse success ~60-70% to ~95-97%; truncation/enum/refusal edge cases.
- Telegram Mini App viewport/keyboard/safe-area iOS quirks (telegram-mini-apps docs + Telegram-iOS issues) — env() insets unreliable; use viewportStableHeight.

### Tertiary (LOW confidence)
- Deck personality / same-cards-feel-different (Lightwands) — supports the Core-Value hypothesis but is community/anecdotal; validate empirically post-launch.
- Tarot IP separation (meanings/structure not protectable vs. specific deck art) — domain reasoning grounded in TZ section 5, not formal legal advice; legal review required before public launch.

---
*Research completed: 2026-06-09*
*Ready for roadmap: yes*
