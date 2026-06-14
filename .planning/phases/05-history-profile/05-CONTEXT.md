# Phase 5: History & Profile - Context

**Gathered:** 2026-06-13
**Status:** Ready for planning

<domain>
## Phase Boundary

The user can revisit their journey and manage who they are: every completed reading (already auto-persisted in Phase 4) becomes a browsable, paginated **history** with a detail view and soft delete, and a **profile/settings** screen exposes the Telegram identity + the settings toggles — including the explicit opt-in that gates any future history-based personalization. This phase mostly **surfaces data Phase 4 already stores** and adds the profile/settings write path; it does not regenerate readings.

**In scope:**
- Backend: `GET /api/readings` (paginated list — HIST-02), `GET /api/readings/{id}` (immutable detail, no regen — HIST-03), `DELETE /api/readings/{id}` (soft delete via `deleted_at` — HIST-04), extend `GET /api/me` + new `PATCH /api/me/settings` (PROF-01/02), free-retention "last 10" enforcement (HIST-06), the consent gate guaranteeing history is never used without opt-in (HIST-05).
- Frontend: a **History list** screen, a reading **detail** view (reuse `ResultScreen`), a **Profile/Settings** screen, header entry points, and un-stubbing the result-screen «история» action (Phase 3 D-12).
- HIST-01 (auto-save) is already satisfied at the DB level by Phase 4's `ReadingService`; this phase surfaces it.

**Out of scope (later phases):** real history-based personalization / повторный анализ (v2 — ENG-02); weekly free-limit reset / paywall / readings-count logic (Phase 6); Telegram Stars / subscription (Phase 7); share-card / «сохранить карточку» (Phase 8); profile stats / analytics (Phase 8 admin/analytics); filters/search in history (deferred until history grows large under subscription).

</domain>

<decisions>
## Implementation Decisions

### History list & reopen
- **D-01:** History list pagination = **load-more** («Показать ещё»). `GET /api/readings` is paginated (limit/offset); the list is **reverse-chronological with NO filters** in MVP (the free list is ≤10 items — filters are overkill). The API keeps optional `topic`/`deck` params for later; the UI does not surface them.
- **D-02:** Reopening a past reading goes **straight to the result view with a light fade-in** (cards stagger-in via opacity) — NOT a re-ritual / re-reveal. Reuse `ResultScreen`. The reading is served **immutable** (HIST-03 — stored cards/interpretation/summary rendered as originally generated, no regeneration).

### Soft delete & free retention
- **D-03:** Delete UX = **swipe-to-delete on the list card** + an **undo snackbar** (~5s). Backed by soft delete (`deleted_at`); undo simply unsets `deleted_at` within the window. (User chose swipe over a detail-screen button — more mobile-native.)
- **D-04:** HIST-06 "free retains last 10" = **display-cap, retain data**. The free list shows the **last 10**; older readings **stay in the DB** (NOT hard-pruned) so a future subscription can reveal them (reversible). The cap is a query/display concern, not a deletion. Surfacing is quiet or a light "последние 10" note — the subscription **upsell is deferred to Phase 6/7**.

### History-personalization opt-in (privacy)
- **D-05:** Opt-in = a **settings toggle, default OFF** (`allow_history_personalization=False`, the model default), with a short plain-language explanation + a privacy note. Explicit, conscious choice (ТЗ §2.2).
- **D-06:** Phase 5 scope = **consent flag + gate ONLY**. Phase 5 stores the consent and **guarantees history is never fed into the §18 summary prompt unless the flag is ON** (satisfies HIST-05, a *negative* requirement). The actual "feed history into the prompt / повторный анализ динамики" feature is **v2 (ENG-02)** — NOT built here. The toggle is visible in settings (PROF-02). Phase 4's PromptEngine already accepts `allow_history_personalization`/`history_context` but doesn't populate it — keep it that way; just wire the persisted flag and the closed gate.

### Profile & settings
- **D-07:** Profile screen (MVP) = **Telegram identity (name + photo from `GET /api/me`) + the settings toggles** (reversals, history-personalization). No stats block (stats overlap Phase 8 admin/analytics).
- **D-08:** The "available readings count" + subscription block is **hidden in the Phase 5 UI**. `GET /api/me` may return the fields (forward-compat), but the UI does not surface a count until **Phase 6** (weekly-reset makes it real) / **Phase 7** (payments). Avoids showing a non-resetting/misleading number (Phase 4 decrements `free_used_this_week`, but the reset/block logic is Phase 6).
- **D-09:** Settings now persist **server-side** via `PATCH /api/me/settings` (`reversals_enabled`, `allow_history_personalization`, `onboarding_completed`). The Phase-3 localStorage onboarding flag (Phase 3 D-11) **migrates to the server**; the reading request's `reversals_enabled` is now sourced from the persisted user setting (default ON — Phase 4 D-13).

### Navigation
- **D-10:** Entry to History/Profile = **icons in the Home (selection-screen) atmospheric header** (TZ §9.2). The ritual/reveal/result screens stay **chrome-free** (no persistent bottom tab bar — it would fight the immersive ritual + the sticky CTA). The result-screen «история» action (un-stubbed from Phase 3 D-12) also routes to History.
- **D-11:** Back navigation = **in-app back button → Home** (consistent with Phase 3 D-03 — in-app, NOT the Telegram native BackButton). History/Profile → Home; reading detail → History.

### Claude's Discretion
- Exact empty-history copy (TZ §9.6 «Пока здесь тихо. Первый расклад появится в истории, когда колода даст ответ.») + the settings/personalization explainer copy — brand-voice clean (no «AI/нейросеть/модель»).
- Whether History/Profile are new `step` values in the existing Zustand step-machine vs a light route layer — planner's call, constrained by D-02/D-10/D-11.
- The "last 10" note wording (or none) — D-04.
- History list-item layout (date / question / deck / spread / card thumbnails / short summary per §9.6 + HIST-02) — reuse existing card/`CardArtFallback` patterns.
- Whether to add a dedicated history/profile service vs extend `ReadingService`/the users router — planner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project source-of-truth — `.planning/REFERENCE-TZ.md`
- §9.6 — History list contents (date, question, deck, spread, card thumbnails, short summary) + the empty-state copy.
- §14.2 — User API: `GET /api/me` (profile), `PATCH /api/me/settings` (`reversals_enabled`, `allow_history_personalization`, `onboarding_completed`).
- §14.5 — Readings API: `GET /api/readings` (list, query params `limit`/`offset`/`topic`/`deck_slug`), `GET /api/readings/{id}` (detail), `DELETE /api/readings/{id}` (soft delete).
- §13.1 — `users` settings columns; §13.8/§13.9 — `readings`/`reading_cards` (immutable stored content + `deleted_at`).
- §11.1 — free tier "история последних 10 раскладов" (HIST-06).

### Requirements & roadmap
- `.planning/REQUIREMENTS.md` — Phase 5 IDs: HIST-01..06, PROF-01, PROF-02. (HIST-05 is a negative req — see D-06; ENG-02 is the v2 personalization feature.)
- `.planning/ROADMAP.md` → "Phase 5: History & Profile" — goal + 5 success criteria.

### Prior phases (the contracts this phase surfaces)
- `.planning/phases/04-real-personal-reading-keystone/04-CONTEXT.md` — D-12 (Sonnet-on-retry, n/a here), the `ReadingOut`/`ReadingOutput` shape, and that the §18 prompt accepts but does NOT populate `history_context` (D-06 keeps it that way); reversals default ON (Phase 4 D-13).
- `.planning/phases/03-the-ritual-mock/03-CONTEXT.md` — D-02 (Zustand `step` state-machine + `AnimatePresence`), D-03 (in-app back buttons), D-04 («ещё расклад» preserves question+topic), D-11 (`onboarding_completed` localStorage → now server-side, D-09), D-12 (result «история»/«сохранить» stubs — «история» un-stubbed here).
- `CLAUDE.md` — stack (React 19 + Zustand + TanStack Query + `motion` from `motion/react-m`), brand-voice ban list, mobile-first 360–430px, backend §29.2 rules.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/api/users.py` — `GET /api/me` already exists (returns `MeResponse`, Phase 1). Extend it (settings block) and add `PATCH /api/me/settings`.
- `backend/app/api/readings.py` — currently `POST /api/readings` only (Phase 4). Add `GET` (list), `GET /{id}` (detail), `DELETE /{id}` (soft delete) here.
- `backend/app/services/reading.py` — Phase-4 `ReadingService` (the persistence + mapping patterns to reuse for list/detail; `ReadingOut` mapping already exists).
- `backend/app/models/reading.py` — `Reading` has `deleted_at` (soft delete) + `user_id` indexed (history queries); `ReadingCard` immutable. `backend/app/models/user.py` — `onboarding_completed` / `reversals_enabled` / `allow_history_personalization` already present (defaults: personalization=False, reversals=True).
- `backend/app/schemas/reading.py` — `ReadingOut` (reuse for detail); add a light list-item schema (no full interpretation — date/question/deck/spread/thumbnails/short summary per HIST-02).
- `frontend/src/components/result/ResultScreen.tsx` — reuse for the detail view (D-02); its «история» action is a `«скоро»` stub to un-stub (D-10).
- `frontend/src/stores/selection.ts` — the Zustand `step` state-machine (Phase 3 D-02) to extend with History/Profile destinations.
- `frontend/src/lib/telegram.ts` — Telegram name/photo source for the profile header (D-07).
- `frontend/src/reading/copy.ts` — brand-safe copy module (SAFE-06 guard) for the new history/profile/settings strings + §9.6 empty state.
- `frontend/src/components/{CardArtFallback,DeckCard}.tsx` — card thumbnail patterns for history list items.

### Established Patterns
- Backend: SQLAlchemy 2.0 async, thin router → service, soft in-character errors. Server state in TanStack Query, client/ephemeral in Zustand — the history list + profile are **server state** (TanStack Query), settings writes are mutations (optimistic, with the persisted flag as source of truth).
- The whole authenticated surface lives inside `AuthGate`; History/Profile are new authenticated screens.

### Integration Points
- The `step` state-machine (`App.tsx` flow root) gains History / Profile / detail destinations; back returns to Home (D-11).
- `reversals_enabled` for a new reading is now read from the persisted user setting (D-09), replacing the Phase-3 local toggle.

</code_context>

<specifics>
## Specific Ideas

- The app is an **immersive ritual flow**, not a tabbed app — navigation stays minimal (header icons on Home, chrome-free ritual/reveal/result) to protect the Phase-3 D-01 felt-quality bar (D-10).
- Soft-delete + undo is deliberately low-friction (swipe + 5s undo) because the reading is the user's keepsake — accidental loss should be trivially reversible (D-03).

</specifics>

<deferred>
## Deferred Ideas

- Real history-based personalization / повторный анализ динамики (feed `history_context` into the §18 prompt) — **v2 (ENG-02)**; Phase 5 only captures consent + keeps the gate closed (D-06).
- Subscription / extended-history reveal + the "available readings" count block — Phase 6 (limits) / Phase 7 (payments) (D-04, D-08).
- History filters / full-text search — when history grows large under subscription; the API keeps `topic`/`deck` params now (D-01).
- Profile stats (readings done, favorite deck) — Phase 8 (overlaps admin/analytics) (D-07).
- Share-card / real «сохранить карточку» export — Phase 8.
- Telegram native BackButton — Phase 3/5 chose in-app back; revisit later if desired (D-11).

</deferred>

---

*Phase: 05-history-profile*
*Context gathered: 2026-06-13*
