---
phase: 8
slug: admin-analytics-polish-deploy
created: 2026-07-06
mode: lean-slice (mvp — vertical feature slices)
authored: inline (orchestrator — subagents hit provider session limits repeatedly this session)
---

# Phase 8 — Research

Grounds the 08-CONTEXT.md lean-slice decisions (D-01..D-05) against the live codebase. Every claim
below was verified against real files this session. Consumed by the planner.

## Executive summary

Three of the four lean deliverables lean HEAVILY on substrate that already exists — the research
mostly *removes* work rather than adding it:

- **Safety-valve:** the DATA plane is already built. `PromptEngine._active_template` already selects
  `WHERE slug = :s AND is_active IS TRUE` via `scalar_one_or_none()`, and `prompt_version` is already
  persisted to `readings` + `generation_logs`. Only the **admin control plane** (create/activate/
  rollback) + a **multi-version schema tweak** are missing. See §1.
- **Analytics:** `app_events` table exists (`models/analytics.py`) with **zero writers**. Pure add:
  a best-effort server helper + a thin `POST /api/events` + a FE `track()`. See §2.
- **Share-card:** client-canvas, no backend, no new dep. Web Share API + download fallback. See §3.
- **Polish:** gap-audit over the existing copy.ts / errors.py substrate. See §4.

`Mode: mvp` (ROADMAP) → the planner organizes these as **vertical slices**, not horizontal layers.

---

## §1 — Prompt-version safety-valve (D-03) — THE design fork, resolved

### What exists (verified)
- `models/prompt.py`: `PromptTemplate` has `slug` (**UNIQUE**, indexed), `title`, `type` (enum),
  `template_text`, `version` (String), **`is_active`** (Boolean, server_default `true`).
- `services/prompt_engine.py`: `_active_template(session, slug)` runs
  `select(PromptTemplate).where(slug == :s, is_active.is_(True))` → `.scalar_one_or_none()`, raises
  `ValueError` if none. Engine docstring: *"the admin version toggle is the Phase-8 safety valve."*
  `compose_prompt_version()` already stamps `<type>@<version>` into `readings.prompt_version`.
- `seed/loader.py`: prompts upserted `ON CONFLICT (slug) DO UPDATE` (slug is the conflict key).

### The fork
ROADMAP criterion 1 requires *"create/activate/**roll back** prompt-template versions (quick-disable
a bad version)."* But because `slug` is UNIQUE there is exactly ONE row per template, so toggling
`is_active=false` on e.g. `system` doesn't roll back — it makes `_active_template` raise → every
reading honest-fails (D-09). A kill-switch on a REQUIRED template is worse than the bad prompt. So a
literal "toggle" does not satisfy "roll back a bad version." We need multiple versions to coexist.

### Resolved design (recommended — minimal churn, engine UNCHANGED)
Let `prompt_templates` hold **multiple rows per slug, exactly one active**:
1. **Migration 0005 (additive/reversible):** drop `UNIQUE(slug)`; add `UNIQUE(slug, version)`; add a
   **partial unique index** `uq_prompt_active_per_slug UNIQUE (slug) WHERE is_active` (Postgres
   partial index — enforces "≤1 active per slug", exactly the invariant `scalar_one_or_none()`
   relies on); keep the plain `slug` index for lookup. Existing data already satisfies "one active
   per slug" → **no data migration**. Reversible in `downgrade()`.
2. **Seed loader:** change the prompt conflict key `(slug)` → `(slug, version)` so re-seeding
   refreshes the *seeded* version in place and never clobbers an operator-created newer version.
   Seed rows stay `is_active=true` at their `v1`.
3. **Engine:** **UNCHANGED.** `slug AND is_active` already returns the single active version.
4. **Admin endpoints** (behind `require_admin`, in a new `api/admin_prompts.py` or extending
   `api/admin.py`):
   - `GET /api/admin/prompts` — list rows grouped by slug: `{slug, type, versions:[{version,
     is_active, title, updated_at}]}`. (view = criterion-2 "view … generation" slice for prompts.)
   - `POST /api/admin/prompts/{slug}/versions` — body `{version, template_text, title?}`; INSERT a
     new version and activate it atomically (deactivate the current active for that slug in the same
     tx). = **create + activate.**
   - `POST /api/admin/prompts/{slug}/activate` — body `{version}`; activate an existing version,
     deactivate the rest for that slug (atomic `UPDATE … WHERE slug`; the partial-unique index is
     the backstop). = **rollback.**
   - Atomicity: one tx, `UPDATE … SET is_active=false WHERE slug=:s` then `… SET is_active=true
     WHERE slug=:s AND version=:v`; 404 if that (slug,version) doesn't exist.
5. **AdminScreen:** a "Промпты" section — per slug, list versions with an active badge + an
   "Активировать/Откатить" button. Minimal (operator is technical); reuse the existing admin fetch
   seam (`api/admin.ts` + `require_admin`).

### Guardrails
- Live edits are **ephemeral vs seed**: a redeploy re-seeds the seeded `(slug,v1)` row. That's fine
  for an emergency valve (buy time), but the admin UI copy should say a permanent fix belongs in the
  seed. New operator-created versions (different `version` label) survive redeploy (conflict key is
  `(slug,version)`), only the seeded label is refreshed.
- The valve must never let the engine find zero active rows for a required slug — the "activate"
  endpoint activates-then the partial index guarantees the old one is the only other; keep both
  UPDATEs in one tx so there is never a window with zero active.
- Brand/SAFE unaffected — templates are DATA; no UI copy leaks "AI/нейросеть/модель".

### Alternative (rejected for lean): live `PATCH template_text`
Editing the single row's text in place is simpler (no migration) but is NOT "rollback" — the
known-good text is lost the moment it's overwritten, and criterion 1 explicitly wants versioned
rollback. The partial-unique multi-version design is the right lean answer and leaves the hot-path
engine query untouched.

---

## §2 — Analytics into `app_events` (D-02)

### What exists (verified)
- `models/analytics.py`: `AppEvent` = `user_id UUID NULL` (bare, not FK — anonymous-capable, survives
  user deletion), `event_name String`, `event_properties JSONB default dict`, `created_at`
  server_default `now()`. **No writers anywhere** (grep clean).
- `main.py` mounts routers with `prefix="/api"`; adding `events.router` is one line.

### Design
- **Server-side helper** `services/analytics.py::record_event(user_id, event_name, properties)` —
  **MUST NOT share the caller's transaction.** A failed INSERT aborts the caller's asyncpg tx (would
  roll back the reading/payment). So the helper opens its **own** short-lived `AsyncSession` (via the
  app `async_sessionmaker`), inserts, commits, and **swallows all exceptions** (logs
  `app_event_write_failed`). Fire-and-forget; best-effort. Callers: `reading_started` /
  `reading_completed` / `reading_failed` in `services/reading.py`; `payment_succeeded` /
  `subscription_started` (+ optional `payment_failed`, `refund`) in the `payments.py` grant path.
  Emit AFTER the core write commits (post-commit) so analytics can never poison the money/reading tx.
- **Client-side sink** `POST /api/events` (new `api/events.py`, Bearer): body `{event_name,
  properties?}`; `user_id` from JWT `sub` ONLY (never body); validate `event_name` against an
  **allowlist** (unknown → drop, return 2xx); write via the same best-effort helper; **always return
  2xx** even on write failure (never break the client). Light abuse cap: reuse the **fail-open**
  Redis throttle pattern (from `deps.py::throttle_gate`, the P6 fix) with a generous per-user cap
  (e.g. 120/min); fail-open on Redis error.
- **FE** `src/api/events.ts::track(eventName, props?)` — fire-and-forget `apiFetch` POST, `.catch(()=>
  {})`, never awaited on a UI path. Wire at emit points.

### Event allowlist (criterion 3 — ~18)
Server: `reading_started`, `reading_completed`, `reading_failed`, `payment_succeeded`,
`subscription_started` (+ `payment_failed`, `refund` optional).
Client: `app_opened`, `onboarding_started`, `onboarding_completed`, `question_entered`,
`topic_selected`, `deck_selected`, `spread_selected`, `card_revealed`, `summary_viewed`,
`history_opened`, `paywall_viewed`, `product_clicked`, `settings_changed`.
`event_properties` kept tiny + **non-PII** (slugs/enums/counts only — never the question text, never
names). e.g. `deck_selected: {deck_slug}`, `reading_completed: {deck_slug, spread_slug, topic}`,
`product_clicked: {product_slug}`, `paywall_viewed: {reason}`.

### Guardrail
No event write is ever on the critical path or in the caller's tx. This is the same lesson as the P6
throttle fail-open (a best-effort subsystem must degrade, not take down the core flow).

---

## §3 — Privacy-safe share-card (D-04)

### Design (client-canvas, no backend, no new dep)
- On the Result screen (data already loaded: deck, drawn cards, summary), render an offscreen
  `<canvas>`: deck background (deck accent/gradient from the existing per-deck CSS vars), the 3–4 card
  faces (thumbnails already fetched for the reveal), the spread name, and the short summary line.
  **Never draw the question** (privacy — excluded by construction, criterion 4).
- Export `canvas.toBlob()` → share via **Web Share API L2**: feature-detect
  `navigator.canShare?.({files:[file]})` → `navigator.share({files})`; **fallback** to a download
  (`<a download>`) + an in-voice hint ("Карта сохранена — поделитесь из галереи"). This is the
  reliable cross-platform lean path inside the Telegram in-app browser.
- A "Поделиться" affordance on the Result screen (in product voice; no "AI").
- Fonts: use an already-loaded web font; pre-measure to avoid cyrillic clipping; fixed export size
  (e.g. 1080×1350) with `devicePixelRatio` scaling.

### Rejected for lean
Server-side Pillow/PNG render endpoint (nicer output, adds a Python dep + a render route + auth) —
deferred unless client-canvas fidelity proves insufficient for the viral surface.
Telegram Bot-API `savePreparedInlineMessage` + `WebApp.shareMessage` (native share sheet) — more
moving parts (a backend prepare call); the Web-Share+download path ships the value now. Note it as a
future upgrade.

---

## §4 — In-character empty/error/loading polish (D-05)

### Approach
Gap-audit, not rewrite. Verified substrate: `reading/copy.ts` constants (HISTORY_EMPTY/ERROR/LOADING,
READING_ERROR, THROTTLE_MESSAGE), the §9.8 soft-body band, and the global soft-500 handler
`core/errors.py`. Task: sweep every screen (Auth/Catalog/Ritual/Reveal/Result/History/Profile/Admin/
Paywall) + every query error/empty/loading branch; ensure each renders a product-voice copy.ts
constant — no stack trace, no raw slug, no bare spinner. Fill gaps; add missing constants to copy.ts.
`copy.test.ts` banned-token scan (SAFE-06) must still pass. Include the new Phase-8 surfaces
(share-card failure, admin) in the sweep.

---

## Slicing recommendation (MVP vertical slices)
1. **08-01 Safety-valve** — migration 0005 + loader key + admin endpoints + AdminScreen "Промпты".
2. **08-02 Analytics** — `record_event` helper (own-session, post-commit) + server emits + `POST
   /api/events` + FE `track()` + wire ~18 events.
3. **08-03 Share-card** — client-canvas render + Web-Share/download + Result-screen affordance.
4. **08-04 Polish** — empty/error/loading gap-audit + fill; copy.test.ts green.

Deploy+payments (criterion 5) already satisfied (ЮKassa live, 2 real purchases verified); the
legal/IP review is an owner task documented in the phase UAT, not code. Full admin CRUD-UI over
decks/cards/spreads/products (criterion 1's non-prompt clause) is **Deferred** (operator = seed-JSON
+ redeploy), recorded in CONTEXT D-01.

## Sources
- Live code (this session): `models/prompt.py`, `models/analytics.py`, `services/prompt_engine.py`,
  `api/admin.py`, `seed/loader.py`, `main.py`, `api/deps.py` (throttle fail-open), `06-REVIEW.md`.
- `.planning/ROADMAP.md` Phase 8 (criteria 1–5, `Mode: mvp`, req IDs), `08-CONTEXT.md` (D-01..D-05).
- Web Share API L2 (`navigator.canShare({files})`) — standard, feature-detected with download
  fallback (no citation needed; verify support in the Telegram webview at implementation).
