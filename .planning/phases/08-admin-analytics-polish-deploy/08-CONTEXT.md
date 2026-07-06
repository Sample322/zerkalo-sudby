---
phase: 8
slug: admin-analytics-polish-deploy
name: Admin, Analytics, Polish & Deploy
created: 2026-07-06
status: ready_to_plan
mode: lean-slice
---

# Phase 8 — Context

<domain>
Operator tooling + product analytics + share/polish for the LIVE, monetizing Mini App. Scoped as a
**LEAN high-value slice** (owner decision): build only what a solo operator on a live product needs,
skip the full admin CRUD-UI. Four deliverables: (1) a prompt-version **safety valve**, (2) **analytics
events** into the existing `app_events` table, (3) a privacy-safe **share-card**, (4) **in-character
empty/error/loading** polish across screens.
</domain>

<already_done>
**Do NOT rebuild these — they shipped earlier and are LIVE:**
- **Deploy over HTTPS** (roadmap criterion 5): both NL timeweb apps live (backend `…1210`, frontend
  `…d93d`), auto-migrate + seed on boot. Mini App opens; auth works end-to-end.
- **Payments** (criterion 5 "Stars in test mode"): **superseded by the D-01 ЮKassa pivot** (07-CONTEXT).
  ЮKassa direct is LIVE + **verified with real money** (2 real purchases granted correctly). The
  roadmap's "Stars/XTR" wording predates the pivot — treat criterion 5's payment clause as satisfied
  by the ЮKassa live-verification, NOT Telegram Stars.
- **Metrics dashboard (partial, criterion 2):** `GET /api/admin/stats` (`AdminStatsOut`) + `AdminScreen`
  already render users/readings/completed/failed/today/7d + by_deck/topic/answer_style distributions.
  Extend if cheap; do not rewrite.
- **admin auth:** `require_admin` (ADMIN_TELEGRAM_IDS allowlist) + `/api/admin/ping` exist.
</already_done>

<decisions>

### D-01 — Scope: LEAN slice, skip full admin CRUD-UI
Build the 4 deliverables below ONLY. **Skip** in-app CRUD editors for decks/cards/deck_cards/spreads/
products (ADMIN-01/02 full form) — the operator is technical + solo and edits the **seed JSON +
redeploys** (the loader `upsert_by_slug` is `ON CONFLICT DO UPDATE`, so a redeploy re-applies edited
catalog/prices — already proven with the 10₽ price change). Full CRUD-UI → **Deferred** (own future
phase if a non-technical operator ever needs it). Legal/IP review of deck assets (criterion 5) =
**owner task**, documented, not code.

### D-02 — Analytics: write the funnel to the existing `app_events` table
The `app_events` model (`models/analytics.py`, §13.15: `user_id` bare int + `event_name` +
`event_properties` JSONB) already exists — Phase 8 just WRITES to it. Split by origin:
- **Server-emitted (reliable, inline in the services, fire-and-forget):** `reading_started`,
  `reading_completed`, `reading_failed`, `payment_succeeded`, `subscription_started` (+ refund/cancel
  if trivial). Emitted where the event truly happens (reading service / payment webhook grant).
- **Client-emitted via a NEW thin `POST /api/events`** (Bearer, user_id from JWT `sub` ONLY — never
  body; event_name validated against an allowlist; single fire-and-forget insert): `app_opened`,
  `onboarding_started`/`onboarding_completed`, `question_entered`, `topic_selected`, `deck_selected`,
  `spread_selected`, `card_revealed`, `summary_viewed`, `history_opened`, `paywall_viewed`,
  `product_clicked`, `settings_changed`.
- **HARD RULE:** analytics writes are BEST-EFFORT — they must NEVER block, slow, or break the core
  flow. Wrap every emit in try/except (server) / a non-awaited fetch that ignores failure (client).
  A down/slow analytics insert must not 500 a reading or a payment (mirrors the throttle fail-open
  lesson from the P6 review).
- ~15 events total (criterion 3 list, trimmed to the meaningful funnel). Aggregation/dashboards over
  these events beyond the existing stats = out of scope (raw events are enough for a solo founder to
  query).

### D-03 — Prompt-version safety valve (the highest-value admin feature)
The operator must be able to **quick-disable a bad generation prompt version WITHOUT a redeploy**
(criterion 1's "roll back a bad version" — the production safety valve for generation). Mechanism:
- `prompt_templates` gets/uses an `is_active` flag per (type, version) — add a migration if the column
  is absent. `PromptEngine.build` selects only the **active** version for each template type.
- Admin endpoints (behind `require_admin`): list prompt-template versions per type + `POST
  .../activate` / `.../deactivate` (or a single toggle) to flip which version is live. Atomic:
  activating a version deactivates the previously-active one for that type.
- A minimal toggle surface in `AdminScreen` (list versions, one tap to activate/roll back). Minimal
  UI — the operator is technical; no rich editor.
- **NB:** this is the ONE piece of "admin CRUD" kept from the full scope, because a bad prompt version
  degrades every live reading and re-seeding requires a redeploy (slow). Everything else re-seeds fine.

### D-04 — Share-card: CLIENT-side canvas, privacy-safe
Render the share-card **client-side (HTML canvas → image)** — NO new backend dependency (KISS, matches
the no-heavy-dep ethos; server-side Pillow/PNG deferred unless quality demands it). Content: the deck
background + 3–4 card faces + spread name + a short summary line. **EXCLUDES the personal question by
default** (privacy — criterion 4). Built from the reading data already on the result screen; shared via
the Telegram share affordance (download / `openLink` a share URL / prepared inline message — the exact
Telegram mechanism is a research question). Brand-safe (SAFE-06): no «AI/нейросеть/модель» on the card.

### D-05 — In-character empty/error/loading polish
Audit every screen; ensure every empty / error / loading state renders **product-voice copy from
copy.ts** — never a stack trace, a raw slug, or a bare spinner (criterion 4). Most of this is already
done (HISTORY_EMPTY/ERROR/LOADING, READING_ERROR, the soft-body §9.8 band, the global soft-500 handler
`core/errors.py`). Phase 8 = a gap-audit + fill, not a rewrite. No banned brand tokens (copy.test.ts
scan still passes).

</decisions>

<deferred>
- **Full admin CRUD-UI** over decks/cards/deck_cards/spreads/products (ADMIN-01/02 rich editors) — the
  operator uses seed-JSON + redeploy now; build only if a non-technical operator is onboarded.
- **Admin data views** for users/readings/payments/generation-logs as browsable tables (criterion 2's
  "view" clause beyond the aggregate stats) — a solo founder can query the DB directly; revisit if the
  ops load grows.
- **Server-side share-card image** (Pillow/PNG render endpoint) — only if the client-canvas quality is
  insufficient for the viral surface.
- **Extended dashboard** (payment conversion %, revenue, avg latency, error-rate charts) beyond the
  current stats — nice-to-have; the raw `app_events` + existing stats cover the founder's needs.
</deferred>

<canonical_refs>
- `.planning/ROADMAP.md` — Phase 8 goal + 5 success criteria (NB: criterion 5 "Stars/XTR" predates the
  ЮKassa pivot; criterion 5 deploy+payments already satisfied).
- `.planning/REQUIREMENTS.md` — ADMIN-01..09, ANALYTICS-01, UI-05, UI-06 (map lean deliverables to
  these; the deferred ones stay uncovered by-design).
- `.planning/REFERENCE-TZ.md` — §13.15 `app_events` schema, §13.10 `prompt_templates`, §20/§21 voice.
- `.planning/phases/07-telegram-stars-payments/07-CONTEXT.md` — D-01 ЮKassa pivot (supersedes Stars in
  criterion 5).
- Code: `backend/app/models/analytics.py` (`app_events`), `backend/app/models/prompt.py` +
  `backend/app/services/prompt_engine.py` (version selection), `backend/app/api/admin.py` +
  `backend/app/schemas/*` (AdminStatsOut) + `frontend/src/components/admin/AdminScreen.tsx` (extend),
  `backend/app/seed/loader.py` (upsert-by-slug re-seed on redeploy).
</canonical_refs>

<code_context>
Reusable / integration points:
- `app_events` table exists (sink ready) — need writers, not a schema.
- `require_admin` + `AdminScreen` + `GET /api/admin/stats` exist — extend for the prompt-version toggle.
- `PromptEngine.build` composes the prompt from `prompt_templates` by type — this is where the active-
  version selection must gate (D-03).
- `apiFetch` Bearer seam + the FE flow screens (Catalog/Ritual/Reveal/Result/History/Profile) are the
  emit points for the client analytics events (D-02).
- `core/errors.py` global soft-500 handler + `reading/copy.ts` constants = the polish substrate (D-05).
- Payment events already flow through `PaymentService.grant_for_provider_payment` (server-emit point).
</code_context>

<open_questions_for_research>
- Exact `POST /api/events` contract: single vs small-batch; the event_name allowlist + per-event
  `event_properties` shape; rate-limit/throttle need (probably reuse the fail-open pattern, low cap).
- Is `prompt_templates.is_active` already a column, or is a migration needed? What does
  `PromptEngine.build` currently select (latest version? by slug?) — how to gate on active-version.
- Telegram share mechanism for the card: `WebApp.openLink` a share URL vs a prepared inline message
  vs a plain image download — which is reliably supported in the current Bot API.
- Client canvas fidelity for the card (fonts/cyrillic, deck bg, card thumbnails already loaded) — good
  enough, or does the viral surface justify a server PNG (deferred D-04)?
</open_questions_for_research>
