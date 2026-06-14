# Phase 5: History & Profile - Research

**Researched:** 2026-06-14
**Domain:** CRUD + UI surfacing — paginated history (list/detail/soft-delete) + profile/settings, on the existing FastAPI + SQLAlchemy 2 async backend and React 19 + Zustand + TanStack Query frontend.
**Confidence:** HIGH — every pattern this phase needs already exists in the codebase (Phases 1–4); this is composition + surfacing, not new technology. No new dependencies.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** History list pagination = **load-more** («Показать ещё»). `GET /api/readings` is paginated (limit/offset); reverse-chronological, **NO filters** in MVP. API keeps optional `topic`/`deck_slug` params; UI does not surface them.
- **D-02:** Reopening a past reading → **straight to the result view with a light fade-in** (cards stagger via opacity), NOT a re-ritual/re-reveal. Reuse `ResultScreen`. Reading served **immutable** (HIST-03 — stored cards/interpretation/summary rendered as originally generated, no regeneration).
- **D-03:** Delete UX = **swipe-to-delete on the list card** + an **undo snackbar (~5s)**. Backed by soft delete (`deleted_at`); undo unsets `deleted_at` within the window.
- **D-04:** HIST-06 "free retains last 10" = **display-cap, retain data**. Free list shows the **last 10**; older readings **stay in the DB** (NOT hard-pruned). Cap is a query/display concern. Subscription upsell deferred to Phase 6/7.
- **D-05:** Opt-in = a **settings toggle, default OFF** (`allow_history_personalization=False`, the model default), with a short plain-language explanation + privacy note.
- **D-06:** Phase 5 scope = **consent flag + gate ONLY**. Stores consent and **guarantees history is never fed into the §18 prompt unless the flag is ON** (HIST-05, a negative requirement). The actual "feed history into the prompt" feature is **v2 (ENG-02)** — NOT built here. Toggle visible in settings (PROF-02). PromptEngine already does NOT populate `history_context` — keep it that way; just wire the persisted flag and the closed gate.
- **D-07:** Profile screen (MVP) = **Telegram identity (name + photo from `GET /api/me`) + the settings toggles** (reversals, history-personalization). No stats block.
- **D-08:** The "available readings count" + subscription block is **hidden in the Phase 5 UI**. `GET /api/me` may return the fields (forward-compat); UI does not surface a count until Phase 6/7.
- **D-09:** Settings now persist **server-side** via `PATCH /api/me/settings` (`reversals_enabled`, `allow_history_personalization`, `onboarding_completed`). The Phase-3 localStorage onboarding flag migrates to the server; the reading request's `reversals_enabled` is now sourced from the persisted user setting (default ON — Phase 4 D-13).
- **D-10:** Entry to History/Profile = **icons in the Home (selection-screen) atmospheric header**. Ritual/reveal/result stay **chrome-free** (no persistent bottom tab bar). The result-screen «история» action (un-stubbed from Phase 3 D-12) also routes to History.
- **D-11:** Back navigation = **in-app back button → Home** (NOT the Telegram native BackButton). History/Profile → Home; reading detail → History.

### Claude's Discretion
- Exact empty-history copy (TZ §9.6 «Пока здесь тихо. Первый расклад появится в истории, когда колода даст ответ.») + the settings/personalization explainer copy — brand-voice clean (no «AI/нейросеть/модель»).
- Whether History/Profile are new `step` values in the existing Zustand step-machine vs a light route layer — planner's call, constrained by D-02/D-10/D-11.
- The "last 10" note wording (or none) — D-04.
- History list-item layout (date / question / deck / spread / card thumbnails / short summary per §9.6 + HIST-02) — reuse existing card/`CardArtFallback` patterns.
- Whether to add a dedicated history/profile service vs extend `ReadingService`/the users router — planner.

### Deferred Ideas (OUT OF SCOPE)
- Real history-based personalization / повторный анализ динамики (feed `history_context` into the §18 prompt) — **v2 (ENG-02)**; Phase 5 only captures consent + keeps the gate closed (D-06).
- Subscription / extended-history reveal + the "available readings" count block — Phase 6 (limits) / Phase 7 (payments).
- History filters / full-text search — when history grows large under subscription; API keeps `topic`/`deck` params now (D-01).
- Profile stats (readings done, favorite deck) — Phase 8.
- Share-card / real «сохранить карточку» export — Phase 8.
- Telegram native BackButton — Phase 3/5 chose in-app back; revisit later if desired.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HIST-01 | Расклад автоматически сохраняется в историю | **Already satisfied at the DB level by Phase 4.** `ReadingService.create_reading` persists `readings` + `reading_cards` on every completed reading. This phase only **surfaces** it (verify in Validation Architecture: a completed POST appears in the list). No new write path. |
| HIST-02 | История: дата/вопрос/колода/расклад/миниатюры/короткий итог (`GET /api/readings`, пагинация) | New `GET /api/readings` (limit/offset). New **light list-item schema** (`ReadingListItemOut`) — NOT the full interpretation. Fields map to existing `readings` columns (`created_at`, `question`, `summary_short`) + `decks`/`spread_types` slug/name joins + `reading_cards` thumbnails (`deck_cards.thumbnail_url`). See "Pattern 1". |
| HIST-03 | Повторное открытие расклада (`GET /api/readings/{id}`), immutable | New `GET /api/readings/{id}` reusing the existing `ReadingOut` shape (the SAME contract `ResultScreen` already renders via `MockReading`). Read from persisted rows + `summary_full` JSON — never regenerate. Reuse `ReadingService._build_response` mapping logic. See "Pattern 2". |
| HIST-04 | Удаление расклада (DELETE, мягкое `deleted_at`) | New `DELETE /api/readings/{id}` → sets `deleted_at = now()`. Plus an **undo path** (D-03): the cleanest design is a restore endpoint or `PATCH` that unsets `deleted_at` within the window. See "Pattern 3" + Open Question 1. |
| HIST-05 | История НЕ используется для персонализации без согласия (`allow_history_personalization`) | **Negative requirement — already structurally guaranteed.** Verified: `history_context` appears NOWHERE in the backend (grep below); `PromptEngine.build` neither accepts nor reads any history. The gate is closed by *absence*. Phase 5's job: persist the consent flag (D-09) and **add a regression test** that asserts history is never in the prompt regardless of the flag. See "Pattern 5" + "Validation Architecture". |
| HIST-06 | Бесплатно хранится история последних 10 раскладов | **Display-cap, retain data (D-04).** The list query caps to the most recent 10 non-deleted readings (`LIMIT 10`, or `offset + limit` bounded by 10 for free tier). Older rows stay in the DB. NOT a prune/delete. See "Pattern 1" + Open Question 2. |
| PROF-01 | Профиль (`GET /api/me`): имя, кол-во раскладов, подписка, настройки | **`GET /api/me` already exists** (returns `MeResponse{user, limits, settings}`). It ALREADY returns everything PROF-01 needs (name/photo in `user`, count in `limits`, settings in `settings`). **Decision: do NOT extend the schema** — the count/subscription fields are present but the **UI hides them** (D-08). No backend change required for PROF-01. See "Pattern 4". |
| PROF-02 | Настройки (`PATCH /api/me/settings`): reversals/personalization/onboarding | New `PATCH /api/me/settings` — partial update of the 3 boolean flags on `User`. Reuse the existing `SettingsOut` schema for the response; add a `SettingsPatch` request schema with all-optional fields. See "Pattern 4". |
</phase_requirements>

## Summary

Phase 5 is a **surfacing + CRUD** phase with an exceptionally low research surface: every technology, pattern, and contract it needs is already established and battle-tested in the codebase. The backend adds three reading endpoints (`GET /api/readings`, `GET /api/readings/{id}`, `DELETE /api/readings/{id}` + an undo path) and one settings endpoint (`PATCH /api/me/settings`); the frontend adds three screens (History list, reading detail via `ResultScreen` reuse, Profile/Settings) and wires header entry points + in-app back.

The single most important finding is that **HIST-05 is already satisfied by construction**: a grep of the backend confirms `history_context` exists nowhere — `PromptEngine.build` has no history parameter and reads no prior readings. The opt-in flag (`allow_history_personalization`) lives only in the model/schema/migration, never in any prompt assembly. Phase 5's HIST-05 obligation is therefore *negative and defensive*: persist the consent flag and lock the closed gate behind a regression test. Do not build any history-injection path (that is v2/ENG-02).

The second finding: **HIST-01 and PROF-01 require essentially zero new backend code.** Phase 4 already auto-persists every reading; `GET /api/me` already returns the full `{user, limits, settings}` projection PROF-01 specifies. The work is genuinely just surfacing + the write path for settings + delete.

**Primary recommendation:** Slice vertically (MVP_MODE): (1) **list** — `GET /api/readings` + `ReadingListItemOut` + History screen; (2) **detail** — `GET /api/readings/{id}` reusing `ReadingOut`/`ResultScreen`; (3) **delete+undo** — `DELETE` + restore + swipe/snackbar with TanStack Query optimistic update; (4) **settings** — `PATCH /api/me/settings` + Profile screen + the localStorage→server onboarding migration + the HIST-05 regression test. Reuse `ReadingService` patterns, the `apiFetch` Bearer seam, the `copy.ts` brand-safe module, and the `step`-machine. Add no new dependencies.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| History list pagination | API / Backend | DB (indexed `user_id` + `deleted_at` filter) | List is server state; `readings.user_id` is already indexed (Phase 4 model). Ownership stays server-side (forgeable client paging would break the last-10 cap and the user-scoping). |
| Immutable detail render | Frontend (`ResultScreen`) | API (read-only fetch) | Detail is pure presentation of already-persisted rows; backend serves the existing `ReadingOut`, frontend reuses the result UI (D-02). No regeneration tier involved. |
| Soft delete + undo | API / Backend | Frontend (optimistic cache) | `deleted_at` is the source of truth (server). Frontend does an *optimistic* cache update for the 5s snackbar but the server write is authoritative (D-03). |
| Last-10 retention cap | API / Backend | — | Must be a server-side query bound (D-04) — a client-side slice would still leak older rows over the wire and be forgeable. |
| HIST-05 consent gate | API / Backend (PromptEngine) | — | The negative guarantee lives in the prompt-assembly tier (`PromptEngine`), which must never read history unless the flag is ON. Currently it never reads history at all — keep it that way. |
| Profile identity + settings read | API (`GET /api/me`) | Frontend (display) | Identity/settings are server state; `GET /api/me` already owns the projection. |
| Settings write | API (`PATCH /api/me/settings`) | Frontend (optimistic toggle) | Settings persistence is server-side (D-09); frontend optimistically reflects the toggle then reconciles. |
| Navigation (History/Profile destinations) | Frontend (Zustand `step` machine) | — | Pure client UI state — the existing `step` state-machine + `FlowRoot` switch (D-10/D-11). |

## Standard Stack

**No new libraries.** Phase 5 composes the already-pinned, already-used stack. Verified against `frontend/package.json` and `backend/pyproject.toml` (2026-06-14).

### Core (already installed — reuse)
| Library | Version (pinned) | Purpose in Phase 5 | Why Standard |
|---------|------------------|--------------------|--------------|
| `@tanstack/react-query` | `^5` (5.101.x line) `[VERIFIED: frontend/package.json]` | History list query, detail query, delete + restore mutations with optimistic cache updates | Already owns all server state (decks/spreads/me). The list/detail/delete are server state → Query, per the locked architecture rule "React Query owns server state, Zustand holds UI". |
| `zustand` | `^5` `[VERIFIED: frontend/package.json]` | Extend the `step` state-machine with History/Profile/detail destinations (D-10/D-11) | The existing `useSelection` store + `Step` union is the navigation spine (Phase 3 D-02). |
| `motion` | `^12` (import `motion/react-m` under `LazyMotion`) `[VERIFIED: frontend/package.json]` | The D-02 light fade-in on reopen (`opacity` stagger), the undo-snackbar transition, list-item enter | Already the locked animation lib; `ResultScreen` already uses `m.*` + `stagger`. Compositor-friendly props only (web/performance rule). |
| `react` / `react-dom` | `19.2.*` `[VERIFIED: frontend/package.json]` | UI runtime | Established. |
| FastAPI | `0.136.*` `[VERIFIED: backend/pyproject.toml]` | The 4 new endpoints (thin routers → service) | Established pattern (`readings.py`, `users.py`). |
| SQLAlchemy (async) | `2.0.*` `[VERIFIED: backend/pyproject.toml]` | The list/detail/delete queries (`select()` 2.0 style, `AsyncSession`) | Established; `Reading.user_id` + `reading_cards.reading_id` already indexed for these queries. |
| Pydantic | `2.13.*` `[VERIFIED: backend/pyproject.toml]` | `ReadingListItemOut` (new light list schema), `SettingsPatch` (new), reuse `ReadingOut`/`SettingsOut` | Established (`schemas/reading.py`, `schemas/auth.py`). |

### Supporting (already installed — reuse)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` + `pytest-asyncio` + `httpx` ASGITransport | `>=8` / `>=0.24` / `>=0.28` `[VERIFIED: backend/pyproject.toml]` | Integration tests for the 4 endpoints via the existing `auth_client` + savepoint-isolated `auth_session` + `seeded_catalog` fixtures | The whole integration harness already exists (`tests/integration/conftest.py`). |
| `vitest` + `@testing-library/react` | `^3.2.6` / `^16` `[VERIFIED: frontend/package.json]` | Component tests for History/Profile screens; `copy.test.ts` extends to scan the new strings against `BANNED_BRAND_TOKENS` | Established (e.g. `ResultScreen.test.tsx`, `copy.test.ts`). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `useQuery` + manual "load more" (D-01) | `useInfiniteQuery` | `useInfiniteQuery` is the canonical TanStack tool for paginated "load more" and would work — BUT D-01 explicitly chose simple load-more on a ≤10-item free list. A plain `useQuery` keyed by a `limit` that grows on click (or an `useInfiniteQuery` with a single visible "Показать ещё" button) are both fine; **prefer the simplest that satisfies D-01**. `useInfiniteQuery` is the better fit *if* the planner wants real cursor accumulation, but for ≤10 items it is arguably overkill. Planner's call — both are idiomatic. |
| Soft-delete `DELETE` + separate restore endpoint | `DELETE` then re-`POST`/recreate | Never recreate — the reading is immutable and has a stable UUID; undo must unset `deleted_at` on the SAME row (D-03/HIST-03). |
| Cap last-10 in the query (D-04) | Cap in the frontend | Frontend cap leaks older rows over the wire and is forgeable — cap server-side. |

**Installation:** None. `npm install` / `uv sync` unchanged.

## Package Legitimacy Audit

**Not applicable — Phase 5 installs ZERO new packages.** Every dependency it uses is already pinned and human-approved in `frontend/package.json` and `backend/pyproject.toml` (verified 2026-06-14). No registry lookup, slopcheck, or `checkpoint:human-verify` gate is required. If the planner discovers a genuinely new need (it should not), run the Package Legitimacy Gate before adding it.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────── FRONTEND (React 19) ───────────────────────────┐
                         │                                                                            │
  Home header icons ─────┼──► goTo("history")  ──► HistoryScreen                                      │
  (D-10, on selection)   │                          │                                                │
                         │                          │  useReadingsList()  ── useQuery/Infinite ──┐    │
  ResultScreen «история» ┼──► goTo("history")  ─────┘                                            │    │
  (un-stubbed D-10)      │                          │  «Показать ещё» (D-01) grows limit/page   │    │
                         │                          │                                            │    │
                         │   tap list card ─────────┼──► goTo("readingDetail", id)               │    │
                         │                          │      useReadingDetail(id) ── useQuery ──────┼──┐ │
                         │                          │      ResultScreen (reused, D-02 fade-in)    │  │ │
                         │   swipe list card ───────┼──► useDeleteReading() optimistic ──────────┼┐ │ │
                         │                          │      undo snackbar ~5s → useRestoreReading()││ │ │
                         │                          │                                            ││ │ │
  Home header icons ─────┼──► goTo("profile")  ──► ProfileScreen                                 ││ │ │
                         │                          │  GET /api/me (existing) → name/photo/toggles││ │ │
                         │                          │  toggle → usePatchSettings() optimistic ───┼┼┐│ │
                         │   in-app back ───────────┼──► back() → Home (D-11)                     │││││
                         └──────────────────────────┼───────────────────────────────────────────┼┼┼┼┘
                                                     │ apiFetch (Bearer JWT seam, existing)       │││││
  ═══════════════════════════════════════════════════════════════════════════════════════════════════
                         ┌─────────────────────────── BACKEND (FastAPI) ─────────────────────────┼┼┼┼┐
                         │  get_current_user (Bearer gate, existing) — user from JWT, never body │││││
                         │                                                                       ▼▼▼▼│
   GET /api/readings  ───┼──► readings router ──► list service:  select(Reading)                     │
   ?limit&offset         │      (thin)              .where(user_id == jwt.user, deleted_at IS NULL)   │
                         │                          .order_by(created_at DESC).limit/offset           │
                         │                          + last-10 cap (D-04/HIST-06)                       │
                         │                          → ReadingListItemOut[] (light: NO interpretation)  │
                         │                                                                             │
   GET /api/readings/{id}┼──► readings router ──► detail service: select(Reading + cards)              │
                         │                          .where(id, user_id == jwt.user, deleted_at IS NULL)│
                         │                          → ReadingOut (reuse _build_response, immutable)     │
                         │                                                                             │
   DELETE /readings/{id} ┼──► readings router ──► set deleted_at = now() (own the row, user-scoped)    │
   (+ restore/undo path) │                          undo: unset deleted_at  (D-03)                     │
                         │                                                                             │
   PATCH /api/me/settings┼──► users router ────► partial-update reversals/personalization/onboarding   │
                         │                          → SettingsOut                                       │
                         │                                                                             │
   POST /api/readings ───┼──► ReadingService (Phase 4, UNCHANGED) ──► PromptEngine.build               │
   (existing)            │        reversals_enabled now sourced from persisted User flag (D-09)        │
                         │        PromptEngine reads NO history (HIST-05 gate closed by absence)        │
                         │                                                                             │
                         │  PostgreSQL: readings (user_id idx, deleted_at), reading_cards (reading_id   │
                         │  idx), deck_cards.thumbnail_url, users (settings flags)                      │
                         └─────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities
| File (new or extend) | Responsibility |
|----------------------|----------------|
| `backend/app/api/readings.py` (extend) | Add `GET /readings`, `GET /readings/{id}`, `DELETE /readings/{id}` (+ restore) as thin routers delegating to the service. User from `get_current_user`, never the body (T-04-23). |
| `backend/app/services/reading.py` (extend) OR new `history_service.py` (planner's call, D) | List/detail/delete/restore query logic. Detail reuses `_build_response`. |
| `backend/app/schemas/reading.py` (extend) | New `ReadingListItemOut` (light), reuse `ReadingOut` for detail. |
| `backend/app/api/users.py` (extend) | Add `PATCH /me/settings`. |
| `backend/app/schemas/auth.py` (extend) | New `SettingsPatch` (all-optional booleans); reuse `SettingsOut` for the response. |
| `frontend/src/flow/steps.ts` (extend) | Add `"history" | "profile" | "readingDetail"` to the `Step` union + `STEP_ORDER`. |
| `frontend/src/flow/FlowRoot.tsx` (extend) | Register the 3 new screens in `SCREENS`. |
| `frontend/src/stores/selection.ts` (extend) | Hold the selected `detailReadingId` (which reading the detail screen renders). |
| `frontend/src/components/history/*` (new) | `HistoryScreen` (list) + list-item card (reuse `CardArtFallback`). |
| `frontend/src/components/profile/*` (new) | `ProfileScreen` (identity + toggles). |
| `frontend/src/components/result/ResultScreen.tsx` (extend) | Un-stub the «история» action (D-10); accept a reading from either the Zustand slot (live) or the detail query (history) — planner decides the seam. |
| `frontend/src/hooks/useReadings*.ts` (new) | `useReadingsList`, `useReadingDetail`, `useDeleteReading`, `useRestoreReading`, `usePatchSettings`. |
| `frontend/src/api/readings.ts` + `me.ts` (new/extend) | `apiFetch` wrappers for the new endpoints. |
| `frontend/src/reading/copy.ts` (extend) | New history/profile/settings strings + §9.6 empty state (SAFE-06 gate). |

### Pattern 1: Paginated, user-scoped, soft-delete-excluding, last-10-capped list query
**What:** `GET /api/readings` returns a light list (date/question/deck/spread/thumbnails/short summary — §9.6/HIST-02), newest-first, excluding soft-deleted rows, scoped to the JWT user, capped to the last 10 for the free tier (D-04/HIST-06).
**When to use:** The History list slice.
**Backend query shape (SQLAlchemy 2.0 async — mirrors `ReadingService._resolve_deck` style):**
```python
# Source: pattern composed from backend/app/services/reading.py (existing select() style)
# + backend/app/models/reading.py (user_id + deleted_at columns, both index-backed).
stmt = (
    select(Reading)
    .where(
        Reading.user_id == user.id,            # user from JWT, never the body (T-04-23)
        Reading.deleted_at.is_(None),          # exclude soft-deleted (HIST-04)
        Reading.status == ReadingStatus.COMPLETED,  # only completed readings in history
    )
    .order_by(Reading.created_at.desc())       # reverse-chronological (D-01)
    .options(selectinload(Reading.cards)...)   # eager-load cards for thumbnails (Pitfall: no lazy load)
    .offset(offset)
    .limit(min(limit, FREE_HISTORY_CAP - offset))  # last-10 cap (D-04); see Open Question 2
)
```
> NOTE: `Reading` has no declared `cards` relationship in the current model (`reading_cards.reading_id` is an FK + index but no `relationship()`). The planner must either add a `relationship` or issue a second `select(ReadingCard)` keyed by the page's reading ids (the codebase currently uses explicit `select(ReadingCard)` in `_persist_output` — that is the established style; prefer it over adding a lazy relationship to avoid async lazy-load footguns).

**Light list-item schema (NEW — do NOT reuse the heavy `ReadingOut`):**
```python
# Source: new schema, modeled on schemas/reading.py conventions (from_attributes, RU descriptions)
class ReadingListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reading_id: str
    created_at: datetime            # §9.6 дата
    question: str | None            # §9.6 вопрос (None/"" → general)
    deck_name: str                  # §9.6 колода (join decks.name/slug)
    spread_name: str                # §9.6 расклад (join spread_types.name/slug)
    card_thumbnails: list[str]      # §9.6 миниатюры (deck_cards.thumbnail_url, may be empty → CSS fallback)
    summary_short: str | None       # §9.6 короткий итог (readings.summary_short — NOT the full interpretation)
```
**Why light:** §9.6 explicitly lists "короткий итог", not the full per-card interpretation. Sending the full `ReadingOut` for every list row wastes bandwidth and conflates list vs detail. The full interpretation is fetched only on detail (HIST-03).

### Pattern 2: Immutable detail — reuse `ReadingOut` + `_build_response`, never regenerate
**What:** `GET /api/readings/{id}` returns the EXACT `ReadingOut` contract `ResultScreen` already renders (via `MockReading`), read from the persisted `readings` + `reading_cards` + `summary_full` JSON. No LLM call.
**When to use:** The detail slice.
**Key insight:** `ReadingService._build_response(reading, cards, remaining)` already does precisely this mapping (reads `summary_full` JSON back into the 5 summary fields, maps `reading_cards` → `ReadingCardOut`). The detail endpoint is mostly: load the reading + its cards (user-scoped, not deleted), reconstruct the authoritative card titles/positions (the `_card_title`/`_position_title` transient labels via the `cards`/`spread_positions` joins), call the same builder.
```python
# Source: backend/app/services/reading.py _build_response (lines 687-722) — reuse the mapping.
# Detail differs from POST only in: (a) no draw/generate, (b) titles come from the persisted
# joins not a fresh DrawnCard, (c) remaining_limits can be omitted/None (not a fresh consume).
```
**Frontend (D-02 fade-in):** `ResultScreen` already staggers the summary panel via `motion`. For the history-reopen entrance, wrap the card list in the same `opacity`-stagger variant (the existing `summaryContainer`/`summaryItem` pattern) so reopen is a "light fade-in, no re-ritual" (D-02). Reuse, don't rebuild.

### Pattern 3: Optimistic soft-delete + 5s undo (TanStack Query)
**What:** Swipe a list card → optimistically remove it from the cached list, show an undo snackbar ~5s; `DELETE` sets `deleted_at`; undo (within the window) calls a restore endpoint that unsets `deleted_at`; if the user does nothing, the optimistic removal stands.
**When to use:** The delete+undo slice (D-03).
**Canonical TanStack v5 optimistic-mutation shape:**
```typescript
// Source: TanStack Query v5 optimistic-updates pattern (tanstack.com/query/v5 — "Optimistic Updates"
// via cache). Mirrors the codebase's existing useQuery hooks (useDecks/useSpreads) for keys.
function useDeleteReading() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      apiFetch(`/api/readings/${id}`, { method: "DELETE" }).then(okOrThrow),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["readings"] });      // stop in-flight refetch
      const prev = qc.getQueryData(["readings"]);               // snapshot for rollback
      qc.setQueryData(["readings"], (old) => removeById(old, id)); // optimistic remove
      return { prev };
    },
    onError: (_e, _id, ctx) => qc.setQueryData(["readings"], ctx?.prev), // rollback
    // Deliberately DO NOT invalidate on the undo-window path; invalidate on settle only after
    // the window closes, OR rely on the snapshot. See Open Question 1 for the undo interaction.
  });
}
```
**Undo interaction with the cache:** the snackbar holds the snapshot; "Отменить" calls `useRestoreReading(id)` which `PATCH`es `deleted_at = NULL` and restores the cached row (re-set `prev` or re-insert the item at its position). After 5s with no undo, optionally `invalidateQueries(["readings"])` to reconcile with the server (the row is now genuinely `deleted_at`-filtered out). See Open Question 1 for whether the restore endpoint is a dedicated `POST /readings/{id}/restore` or a `PATCH`.
**Snackbar:** a `motion` `AnimatePresence` element with a 5s timer (`setTimeout` cleared on unmount/undo). No new library — build it with the existing `motion` primitives (web/patterns: do not add a toast library for one snackbar).

### Pattern 4: Settings — `GET /api/me` unchanged, new `PATCH /api/me/settings` (partial)
**What:** Read settings from the existing `GET /api/me` `settings` block; write via a new partial `PATCH /api/me/settings`.
**When to use:** The settings slice (PROF-01/02/D-09).
**`GET /api/me` requires NO change** — it already returns `MeResponse{user, limits, settings}` where `settings` is the 3 flags (`schemas/auth.py SettingsOut`). PROF-01's "count/subscription" fields are in `limits`, present but **hidden by the UI** (D-08). Do not extend `MeResponse`.
**`PATCH` request schema (NEW — all fields optional so any subset can be patched):**
```python
# Source: new schema on schemas/auth.py conventions. All-optional → partial update; exclude_unset
# on the inbound model so only provided keys are written (the standard FastAPI PATCH idiom).
class SettingsPatch(BaseModel):
    reversals_enabled: bool | None = None
    allow_history_personalization: bool | None = None
    onboarding_completed: bool | None = None
```
**Handler:** load `current_user`, apply only `model_dump(exclude_unset=True)` keys to the `User` row, `commit`, return `SettingsOut`. User from `get_current_user`, never the body.
**Frontend optimistic toggle:** `usePatchSettings` mutates the `["me"]` query cache optimistically (same `onMutate`/rollback shape as Pattern 3). The toggle reflects instantly; the persisted flag is the source of truth on reconcile.
**localStorage → server onboarding migration (D-09):** Phase 3 stored `onboarding_completed` in localStorage (`useOnboardingSeen`). Phase 5 makes the server authoritative. Migration approach: on auth/boot, if the server `settings.onboarding_completed` is the truth, drive `FlowRoot`'s initial-step gate from it instead of `hasSeenOnboarding()`; when onboarding completes, `PATCH onboarding_completed: true`. Keep a one-time best-effort: if localStorage says seen but the server says false (returning user from before this phase), fire the `PATCH` once to reconcile. The planner should treat the localStorage read as a fallback only, server as primary. See Open Question 3.
**`reversals_enabled` source change (D-09):** the reading request's `reversals_enabled` now comes from the persisted `User.reversals_enabled` (default ON, Phase 4 D-13), not the Phase-3 local toggle. The frontend should send the persisted value (read from `GET /api/me` settings) on `POST /api/readings`. `createReading.ts` already accepts `reversalsEnabled` in its params — the caller (CatalogScreen) just sources it from the settings query instead of the local Zustand toggle.

### Pattern 5: HIST-05 — the consent gate is closed by ABSENCE (defensive, not additive)
**What:** History must never enter the §18 prompt without `allow_history_personalization`. Today, history never enters the prompt at all.
**Verification (grep of `backend/`):**
```
allow_history_personalization → app/models/user.py, app/schemas/auth.py, alembic/0001 (column only)
history_context               → ZERO matches anywhere in backend/app
```
`PromptEngine.build(session, deck, spread, draw_records, question, topic, safety_action)` has **no history parameter** and reads no prior readings. `ReadingService.create_reading` never loads history. The gate is closed by construction.
**Phase 5's obligation (D-06):**
1. Persist the consent flag (already a column; `PATCH /api/me/settings` writes it).
2. **Add a regression test** that asserts the prompt contains no history even when `allow_history_personalization=True` — this locks the negative requirement so a future v2 author cannot accidentally wire history in without the gate. See Validation Architecture.
3. **Do NOT** add any `history_context` parameter, any "fetch last N readings", or any prompt branch. That is v2/ENG-02.

### Anti-Patterns to Avoid
- **Returning the full `ReadingOut` for every list row.** The list is "короткий итог" only (§9.6). Use the light `ReadingListItemOut`. (Bandwidth + concern-mixing.)
- **Adding a `relationship()` to `Reading` for cards just for the list, then lazy-loading it in async.** The codebase uses explicit `select(ReadingCard)` (see `_persist_output`); follow that to avoid `MissingGreenlet` async lazy-load errors. If a relationship is added, always `selectinload` it.
- **Hard-pruning readings beyond 10.** D-04 is display-cap-retain-data; deleting rows is irreversible and breaks the future subscription reveal. Cap the query, never delete.
- **Recreating a reading on undo.** Undo unsets `deleted_at` on the same immutable row (stable UUID). Never re-`POST`.
- **Trusting a body/path `user_id`.** Every endpoint scopes by `get_current_user` (the JWT `sub`). A `GET /api/readings/{id}` for another user's reading must 404 (user-scoped `where`), not 200.
- **Wiring `history_context` "while we're here."** HIST-05 is satisfied by absence — adding the plumbing (even unused) creates the exact footgun the negative requirement guards against.
- **Showing the readings count / subscription in Phase 5 UI.** D-08 — hidden until Phase 6/7 (the count does not reset yet; showing it misleads).
- **A persistent bottom tab bar.** D-10 — header icons on Home only; ritual/reveal/result stay chrome-free.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Optimistic list updates + rollback on delete | A bespoke "pending delete" array + manual re-render | TanStack Query `onMutate`/`onError`/`setQueryData` (Pattern 3) | Query owns the cache; the snapshot/rollback recipe is battle-tested and already the project's server-state tool. |
| Pagination state | A custom page-state reducer in Zustand | `useQuery`(growing limit) or `useInfiniteQuery` | Query handles caching, dedup, and stale data; duplicating it in Zustand violates the locked "no server state in Zustand" rule. |
| Bearer auth on the new fetches | Re-reading the JWT per call | The existing `apiFetch` seam | Already the single Bearer-attachment point. |
| Immutable detail mapping (`reading_cards` → response) | A new mapper | Reuse `ReadingService._build_response` | The exact mapping (incl. `summary_full` JSON round-trip) already exists and is tested. |
| In-app back/navigation | A router library (react-router) | Extend the existing Zustand `step` machine + `history[]` | The project deliberately uses a `step` state-machine (D-02/D-10/D-11), not a URL router; adding react-router fights that and the chrome-free ritual. |
| Undo snackbar | A toast library (react-hot-toast/sonner) | A `motion` `AnimatePresence` element + `setTimeout` | One snackbar does not justify a dependency; `motion` is already the animation lib. |
| Brand-safety on new copy | Ad-hoc regex per string | `containsBannedBrandToken` / `BANNED_BRAND_TOKENS` from `copy.ts` | The single SAFE-06 source (W-1); `copy.test.ts` already scans the module. |
| Soft-delete semantics | A new `is_deleted` boolean | The existing `readings.deleted_at` timestamp | The column exists (Phase 1 schema); a timestamp also records *when* (audit) and undo just nulls it. |

**Key insight:** This phase's correctness comes almost entirely from *reusing* Phase 1–4 seams (apiFetch, ReadingService mapping, the step-machine, copy.ts, the integration fixtures). The temptation to introduce new infrastructure (a router, a toast lib, a history-personalization pipeline) is the main risk — resist all three.

## Runtime State Inventory

> Phase 5 is **not** a rename/refactor/migration phase — it adds endpoints and screens. The one migration-shaped concern is the **localStorage → server onboarding flag** (D-09), inventoried here for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `readings`/`reading_cards` rows already persisted by Phase 4 (HIST-01) — Phase 5 reads them, no migration. | None — surfacing only. |
| Live service config | None — no external service config embeds Phase-5 state. | None — verified by scope (no n8n/Datadog/etc. in this project). |
| OS-registered state | None. | None. |
| Secrets/env vars | None new. `VITE_API_BASE`/JWT already wired (Phase 1). | None. |
| Build artifacts | None. | None. |
| **Client-stored state (the one real item)** | Phase-3 `onboarding_completed` lives in **browser localStorage** (`frontend/src/hooks/useOnboardingSeen.ts`), read by `FlowRoot`'s initial-step gate. D-09 moves the source of truth to the server (`User.onboarding_completed` via `PATCH /api/me/settings`). | **Code edit + one-time reconcile:** drive the initial-step gate from the server `settings.onboarding_completed` (from `GET /api/me`); on completion `PATCH onboarding_completed: true`; for users who already have the localStorage flag set but a server `false`, fire the `PATCH` once to reconcile. See Open Question 3. |

## Common Pitfalls

### Pitfall 1: Async lazy-load on `reading_cards` for list thumbnails
**What goes wrong:** Adding a `Reading.cards` relationship and accessing `reading.cards` in an async list handler raises `MissingGreenlet` / a lazy-load error under asyncio.
**Why it happens:** SQLAlchemy async forbids implicit lazy loads; the current model has NO `cards` relationship (only the FK + index).
**How to avoid:** Follow the established codebase style — issue an explicit `select(ReadingCard).where(reading_id.in_(page_ids))` (as `_persist_output` does) and group thumbnails in Python; OR add a relationship and ALWAYS `selectinload` it. Never bare-access a relationship in async.
**Warning signs:** `MissingGreenlet`, `sqlalchemy.exc.InvalidRequestError` about lazy loading in tests.

### Pitfall 2: Detail/delete not user-scoped → cross-user data leak
**What goes wrong:** `GET /api/readings/{id}` or `DELETE` that filters only by `id` lets user A read/delete user B's reading.
**Why it happens:** Forgetting the `user_id == current_user.id` clause.
**How to avoid:** EVERY reading query/mutation includes `Reading.user_id == user.id` AND `deleted_at IS NULL`. A non-owned or deleted id → 404 (not 403 — don't reveal existence). Mirror the `ReadingInputError`→404 pattern.
**Warning signs:** A test fetching another user's reading id returns 200. (Add this test — see Validation Architecture.)

### Pitfall 3: The last-10 cap interacting with load-more/offset
**What goes wrong:** `offset` paging that ignores the cap lets a free user page past 10 (offset=10 returns rows 11+), defeating HIST-06.
**Why it happens:** Treating limit/offset as unbounded.
**How to avoid:** Bound the effective window to `FREE_HISTORY_CAP` (10) server-side: `limit = min(requested_limit, CAP - offset)`, and if `offset >= CAP` return empty. Keep the cap a single named constant. Subscription (Phase 6/7) later lifts it — leave a clear seam. See Open Question 2.
**Warning signs:** A test creating 12 completed readings and paging to offset=10 returns rows for a free user.

### Pitfall 4: Soft-deleted readings reappearing in list or detail
**What goes wrong:** The list or detail query omits `deleted_at IS NULL`, so a deleted reading still shows.
**Why it happens:** Soft delete only matters if every read filters it.
**How to avoid:** `deleted_at.is_(None)` on the list AND the detail AND (implicitly) the new reading flow. The restore (undo) is the ONLY path that touches a non-null `deleted_at`.
**Warning signs:** Delete-then-list shows the row; delete-then-GET-detail returns 200.

### Pitfall 5: Optimistic cache key mismatch
**What goes wrong:** The delete mutation's `setQueryData(["readings"])` key doesn't match the list query's actual key (e.g. the list is keyed `["readings", {limit}]`), so the optimistic update silently no-ops.
**Why it happens:** Paginated/filtered queries carry params in the key; the mutation must target the same key (or use a partial-match invalidation).
**How to avoid:** Pick a stable list key strategy up front (e.g. `["readings", "list"]` for the single MVP list, since there are no filters per D-01) and reuse it in both the hook and the mutation. With no filters, a single key is cleanest.
**Warning signs:** Swipe removes nothing visually until a refetch; the snapshot/rollback targets stale data.

### Pitfall 6: Re-introducing brand-banned copy in new strings
**What goes wrong:** New history/profile/settings copy (esp. the personalization explainer) slips an «ИИ/модель/нейросеть» token.
**Why it happens:** Settings explainers tempt "this uses AI to…" phrasing.
**How to avoid:** ALL new strings go in `copy.ts`; extend `copy.test.ts` to scan them via `BANNED_BRAND_TOKENS`. The personalization explainer must describe it as "история раскладов"/"колода помнит", never the mechanism.
**Warning signs:** `copy.test.ts` fails; a string mentions the LLM.

## Code Examples

### `GET /api/readings` thin router (mirrors existing `readings.py` / `users.py`)
```python
# Source: backend/app/api/readings.py (existing POST) + users.py (existing GET) conventions.
@router.get("/readings", response_model=list[ReadingListItemOut])
async def list_readings(
    limit: int = Query(10, ge=1, le=10),     # free-tier cap (D-04/HIST-06)
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),    # user from JWT, never the body
    session: AsyncSession = Depends(get_session),
    service: ReadingService = Depends(get_reading_service),
) -> list[ReadingListItemOut]:
    return await service.list_readings(session, user, limit=limit, offset=offset)
```

### `PATCH /api/me/settings` (partial update, exclude_unset)
```python
# Source: backend/app/api/users.py + schemas/auth.py conventions.
@router.patch("/me/settings", response_model=SettingsOut)
async def patch_settings(
    body: SettingsPatch,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SettingsOut:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(user, field, value)            # only provided keys
    await session.commit()
    return SettingsOut.model_validate(user)     # from_attributes
```

### `DELETE` soft-delete (user-scoped) + restore
```python
# Source: composed on the ReadingInputError→404 pattern in services/reading.py.
async def soft_delete(self, session, user, reading_id) -> None:
    reading = (await session.execute(
        select(Reading).where(Reading.id == reading_id, Reading.user_id == user.id)
    )).scalar_one_or_none()
    if reading is None or reading.deleted_at is not None:
        raise ReadingInputError("reading not found")     # → 404 (no existence leak)
    reading.deleted_at = datetime.now(UTC)
    await session.commit()

async def restore(self, session, user, reading_id) -> None:   # undo (D-03)
    reading = (await session.execute(
        select(Reading).where(Reading.id == reading_id, Reading.user_id == user.id)
    )).scalar_one_or_none()
    if reading is None:
        raise ReadingInputError("reading not found")
    reading.deleted_at = None
    await session.commit()
```

### Frontend list hook (mirrors `useDecks`/`useSpreads`)
```typescript
// Source: frontend/src/hooks/useDecks.ts + useSpreads.ts (existing useQuery style).
export function useReadingsList() {
  return useQuery({
    queryKey: ["readings", "list"],         // single stable key — no filters (D-01)
    queryFn: () => fetchReadings(),         // apiFetch("/api/readings?limit=10")
    staleTime: 30_000,
  });
}
```

### Extending the `step` union (mirrors `flow/steps.ts`)
```typescript
// Source: frontend/src/flow/steps.ts (existing union; NOT an enum, per TS rules).
export type Step =
  | "onboarding" | "selection" | "ritual" | "reveal" | "result"
  | "history" | "profile" | "readingDetail";   // new destinations (D-10/D-11)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `useQuery({ keepPreviousData: true })` (boolean) | `placeholderData: keepPreviousData` (helper) | TanStack Query v5 | Already adopted in `useSpreads.ts` — use the v5 helper if a filtered/paged list ever needs "keep old while fetching". |
| Optimistic updates via `onMutate` returning context | Same `onMutate`/`onError`/`onSettled` (v5) — still the cache-update recipe; v5 also offers a UI-only `variables` approach | TanStack Query v5 | Pattern 3 uses the cache approach (matches the project's existing cache usage). The `variables`-only approach is an option for the snackbar UI if the planner prefers not to touch the cache until settle. |
| `framer-motion` import | `motion` package, `import * as m from "motion/react-m"` under `LazyMotion` | motion 12 rename | Already locked project-wide (`FlowRoot`, `ResultScreen`). New screens MUST use `m.*`, never a stray `motion.*` inside `LazyMotion` (Pitfall in FlowRoot comment). |

**Deprecated/outdated:** None relevant — the stack is current (verified 2026-06-14).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `decks` and `spread_types` expose a human `name` (or at least `slug`) to surface in the list item (§9.6 "колода"/"расклад"). | Pattern 1 | LOW — if only `slug` exists, the list shows the slug (the existing `ResultScreen` already shows `deckSlug`/`spreadSlug` as the value, so this is consistent). Planner should confirm the catalog model fields when writing `ReadingListItemOut`. |
| A2 | `deck_cards.thumbnail_url` is the thumbnail source for list miniatures (the integration conftest synthesizes `thumbnail_url`). | Pattern 1 | LOW — if thumbnails are absent, the `CardArtFallback` CSS/SVG fallback (DECK-05) covers it; the list still renders. |
| A3 | The undo window is a pure client timer (~5s) and the restore is a server call only if the user clicks "Отменить"; if not, the optimistic removal + server `deleted_at` already agree. | Pattern 3 / OQ1 | LOW — alternative (server-side TTL/scheduled hard-delete) is explicitly out of scope (D-04 retains data forever). |
| A4 | `GET /api/me` needs NO schema change for PROF-01 (count/subscription already in `limits`, hidden by UI per D-08). | Pattern 4 | LOW — confirmed by reading `schemas/auth.py` (`MeResponse` already has `limits` + `settings`). |
| A5 | History shows only `COMPLETED` readings (failed/crisis/abusive `readings` rows exist from Phase 4 short-circuits but should not appear as "history"). | Pattern 1 | MEDIUM — if the product wants failed attempts visible, drop the `status == COMPLETED` filter. Recommend COMPLETED-only (a failed reading has no cards/summary to show). **Planner/discuss should confirm.** |

**Note:** All A-items are LOW/MEDIUM and resolvable at plan time by reading the catalog models (`decks`, `spread_types`) — they do not block planning.

## Open Questions

1. **Undo endpoint shape: dedicated `POST /readings/{id}/restore` vs `PATCH /readings/{id}` (or reuse DELETE's inverse)?**
   - What we know: undo must unset `deleted_at` on the same row within ~5s (D-03); the row is immutable otherwise (HIST-03).
   - What's unclear: REST shape. A dedicated `POST .../restore` is explicit and testable; a `PATCH` with `{deleted_at: null}` is RESTful but exposes the column.
   - Recommendation: **`POST /api/readings/{id}/restore`** — explicit intent, no column leakage, trivially tested. The frontend undo button calls it; after the 5s window the snackbar dismisses and no call is made.

2. **Last-10 cap: enforce in the query for free tier now, or just `LIMIT 10` with the offset bounded?**
   - What we know: D-04 = display last 10, retain older rows; subscription (Phase 6/7) later reveals more.
   - What's unclear: whether to gate the cap on a tier flag now (none exists until Phase 6) or hardcode 10.
   - Recommendation: **Hardcode a `FREE_HISTORY_CAP = 10` constant** and bound the effective window to it (`min(limit, CAP - offset)`, empty past CAP). Leave a clear seam comment so Phase 6 swaps the constant for a tier-derived limit. No tier plumbing in Phase 5.

3. **localStorage → server onboarding migration: how aggressive?**
   - What we know: D-09 makes the server authoritative; Phase 3 used localStorage (`useOnboardingSeen`).
   - What's unclear: whether to one-time-reconcile existing localStorage flags or just switch to server truth.
   - Recommendation: **Server is primary; localStorage is a boot fallback only.** Drive `FlowRoot`'s initial-step gate from `GET /api/me` `settings.onboarding_completed`. On onboarding completion, `PATCH onboarding_completed: true`. For a returning user whose server flag is still `false` but localStorage says seen, fire one reconciling `PATCH`. Keep it minimal — no data migration script (this is a brand-new feature, the user base is tiny/pre-launch).

4. **One history/profile service vs extend `ReadingService` + users router? (CONTEXT marks this planner's discretion.)**
   - Recommendation: **Extend in place.** Add `list_readings`/`get_reading_detail`/`soft_delete`/`restore` to `ReadingService` (it already owns the reading aggregate + the `_build_response` mapper); add `PATCH` to the users router (tiny, no service needed). A separate `HistoryService` would duplicate the deck/spread/limit resolution helpers. Keep cohesion high.

## Environment Availability

> Phase 5 has no NEW external dependencies. The environment is the same one Phases 1–4 already run in (Postgres + the FastAPI app + the Vite/React frontend). No new tool/service probing is required.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | All reading/settings queries | ✓ (Phase 1+; integration tests skip cleanly if down via `_db_ready`) | 16.x (managed/container) | Integration tests auto-skip when unreachable (existing harness) |
| FastAPI app + existing fixtures | Endpoint tests | ✓ | 0.136.* | — |
| Vite/Vitest frontend | Screen tests | ✓ | vite 7.3.* / vitest 3.2.6 | — |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None new.

**Tooling note (from MEMORY):** Backend deps run in a `uv` venv — use `uv run pytest` (not bare `pytest`). `pnpm` is NOT on PATH on this machine; frontend scripts run via the configured runner per the project's established commands. The planner should keep test commands consistent with what Phases 1–4 used.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is REQUIRED. It drives VALIDATION.md / Nyquist Dimension 8.

### Test Framework
| Property | Value |
|----------|-------|
| Framework (backend) | `pytest` >=8 + `pytest-asyncio` (auto mode) + `httpx` ASGITransport — in-process, no live server |
| Framework (frontend) | `vitest` ^3.2.6 + `@testing-library/react` ^16 |
| Config file (backend) | `backend/pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode=auto, testpaths=tests) |
| Config file (frontend) | `frontend` vitest config (existing — `vitest run`) |
| Quick run command (backend) | `uv run pytest backend/tests/integration/test_readings_list.py -x` (per-slice file) |
| Quick run command (frontend) | run vitest on the new screen test file (per the project's established runner) |
| Full suite command (backend) | `uv run pytest` (current baseline: 82 pass / 49 skip per MEMORY) |
| Full suite command (frontend) | `vitest run` (current baseline: 80 pass per MEMORY) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HIST-01 | A completed `POST /api/readings` then appears in `GET /api/readings` | integration | `uv run pytest backend/tests/integration/test_readings_list.py -k auto_save -x` | ❌ Wave 0 |
| HIST-02 | List returns light items (date/question/deck/spread/thumbnails/short summary), newest-first; NO full interpretation | integration | `... test_readings_list.py -k shape_and_order -x` | ❌ Wave 0 |
| HIST-03 | `GET /api/readings/{id}` returns the immutable `ReadingOut` (same cards/summary as created); a 2nd call returns identical content (no regen) | integration | `... test_readings_detail.py -k immutable -x` | ❌ Wave 0 |
| HIST-04 | `DELETE` sets `deleted_at`; the row no longer appears in the list AND `GET /{id}` 404s; **restore** unsets it and it reappears | integration | `... test_readings_delete.py -x` | ❌ Wave 0 |
| HIST-04 | Soft-deleted reading is EXCLUDED from list (the core soft-delete invariant) | integration | `... test_readings_delete.py -k excluded_from_list -x` | ❌ Wave 0 |
| HIST-05 | **The prompt contains NO history even when `allow_history_personalization=True`** (negative req / closed gate) | integration | `... test_history_personalization_gate.py -x` | ❌ Wave 0 |
| HIST-06 | A free user with 12 completed readings sees only the last 10; older rows remain in the DB (queryable by id directly, not via list) | integration | `... test_readings_list.py -k last_ten_cap -x` | ❌ Wave 0 |
| HIST-02/04 | Cross-user isolation: user B's reading id → 404 on `GET /{id}` and `DELETE` | integration | `... test_readings_auth.py -k cross_user -x` (extend existing file) | ⚠️ extend |
| PROF-01 | `GET /api/me` returns `{user, limits, settings}` with name/photo + settings (no schema change) | integration | extend `backend/tests/integration/test_me.py` | ⚠️ extend |
| PROF-02 | `PATCH /api/me/settings` partial-updates each flag; round-trips via `GET /api/me`; unknown/forged user_id ignored (JWT-scoped) | integration | `... test_settings_patch.py -x` | ❌ Wave 0 |
| PROF-02 | `reversals_enabled` for a new reading is sourced from the persisted user flag (D-09) | integration | `... test_settings_patch.py -k reversals_source -x` | ❌ Wave 0 |
| HIST-02 | History list-item layout renders date/question/deck/spread/thumbnails/short summary; empty state shows §9.6 copy | component (vitest) | vitest on `HistoryScreen.test.tsx` | ❌ Wave 0 |
| HIST-04 | Swipe → optimistic remove + undo snackbar; undo restores the item in the cache | component (vitest) | vitest on `HistoryScreen.delete.test.tsx` | ❌ Wave 0 |
| HIST-03 | Reopen → `ResultScreen` renders the detail with the fade-in (no ritual chrome) | component (vitest) | vitest on `ResultScreen` detail test | ⚠️ extend |
| PROF-02 | Settings toggles optimistic-update and call `PATCH`; the readings-count/subscription block is NOT rendered (D-08) | component (vitest) | vitest on `ProfileScreen.test.tsx` | ❌ Wave 0 |
| SAFE-06 | All new history/profile/settings copy passes the `BANNED_BRAND_TOKENS` scan | unit (vitest) | extend `frontend/src/reading/copy.test.ts` | ⚠️ extend |

### Sampling Rate
- **Per task commit:** the slice's own test file (e.g. `uv run pytest backend/tests/integration/test_readings_list.py -x` for the list slice; the screen's vitest file for the FE slice).
- **Per wave merge:** full backend suite `uv run pytest` + full frontend `vitest run` green (baseline 82/49 skip + 80 pass; new tests added on top).
- **Phase gate:** full suite green before `/gsd-verify-work`.

### The 4 load-bearing invariants (must each have a dedicated automated test)
1. **Soft-deleted excluded from list** (HIST-04) — delete then list must omit the row.
2. **Last-10 cap** (HIST-06) — 12 completed readings → list returns 10, the 11th/12th still fetchable by id (data retained, not pruned).
3. **Settings round-trip** (PROF-02) — `PATCH` then `GET /api/me` reflects the change; partial patch leaves other flags untouched.
4. **Consent gate keeps history out of the prompt** (HIST-05) — the assembled prompt contains no prior-reading content even with `allow_history_personalization=True`. (Today trivially true because no history path exists; the test LOCKS it.)

### Wave 0 Gaps
- [ ] `backend/tests/integration/test_readings_list.py` — HIST-01/02/06 (auto-save visible, light shape + order, last-10 cap). Reuses `auth_client` + `seeded_catalog` + a helper that creates N completed readings via the fakes-backed `ReadingService` (the `fake_service` pattern in `test_readings_auth.py`).
- [ ] `backend/tests/integration/test_readings_detail.py` — HIST-03 immutability (two GETs identical; deleted → 404).
- [ ] `backend/tests/integration/test_readings_delete.py` — HIST-04 soft-delete + restore + excluded-from-list.
- [ ] `backend/tests/integration/test_history_personalization_gate.py` — HIST-05 negative-requirement lock (prompt has no history with flag ON). Can assert at the `PromptEngine.build` level (it has no history param) and/or that no history is loaded in `create_reading`.
- [ ] `backend/tests/integration/test_settings_patch.py` — PROF-02 partial update + round-trip + reversals-source.
- [ ] Extend `backend/tests/integration/test_me.py` — PROF-01 (settings block present, no schema change).
- [ ] Extend `backend/tests/integration/test_readings_auth.py` — cross-user 404 on detail/delete.
- [ ] `frontend/src/components/history/HistoryScreen.test.tsx` (+ delete/undo test) and `frontend/src/components/profile/ProfileScreen.test.tsx` — render + empty state + optimistic delete/undo + count-hidden.
- [ ] Extend `frontend/src/reading/copy.test.ts` — scan the new strings.
- [ ] **Shared test helper:** a `create_completed_reading(session, user, ...)` integration helper (lives alongside the existing `_output_for_indices`/`_spread_position_indices` in `test_readings_flow.py`) so list/detail/delete tests don't each re-drive the full POST. Reuse `fake_service` (FakeSafety+FakeLLM) so no Anthropic call.
- Framework install: none — pytest + vitest already configured.

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: high` in config. Required.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (reuse) | Existing `get_current_user` Bearer-JWT gate on every new endpoint (HS256, `algorithms` pinned, `alg:none` rejected — Phase 1). No new auth surface. |
| V3 Session Management | no (unchanged) | JWT issuance is Phase 1; Phase 5 only consumes the existing Bearer. |
| V4 Access Control | **yes (PRIMARY risk)** | **Object-level authorization**: every reading query/mutation scoped by `Reading.user_id == current_user.id`; non-owned id → 404 (no existence leak). Settings patch targets only `current_user`. This is the #1 thing to test (cross-user isolation). |
| V5 Input Validation | yes | Pydantic validates `limit`/`offset` (bounded `ge=1,le=10` / `ge=0`), the `{id}` path is a UUID (422 on malformed), `SettingsPatch` is a closed 3-boolean schema. No free-text into queries — `select()` parameterization throughout (no f-string SQL). |
| V6 Cryptography | no | No new crypto. (Card draw CSPRNG is Phase 4; not touched.) |

### Known Threat Patterns for {FastAPI + SQLAlchemy async + React/Telegram Mini App}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| IDOR — reading another user's reading via `GET /api/readings/{id}` | Information Disclosure / Elevation | `where(user_id == current_user.id)`; non-owned → 404. **Dedicated test (Wave 0).** |
| IDOR — deleting another user's reading | Tampering | Same user-scoped `where` on `DELETE`/restore. |
| Forged `user_id` in settings PATCH body | Spoofing / Elevation | User from `get_current_user` (JWT `sub`), never the body — mirror the `test_post_readings_user_from_jwt_not_body` pattern. |
| Existence-leak via 403-vs-404 | Information Disclosure | Return **404** (not 403) for non-owned/deleted ids — don't confirm a reading exists. |
| Privacy: history used without consent | Information Disclosure / Privacy | HIST-05 closed gate — history never enters the prompt (verified absent); locked by regression test. The personalization toggle defaults OFF (D-05). |
| SQL injection via list filters | Tampering | `topic`/`deck_slug` params (if ever wired) go through `select().where(... == value)` parameterization, never string-built SQL. (D-01: not surfaced in UI anyway.) |
| Sensitive-data exposure in list/detail | Information Disclosure | Light list omits internals; detail reuses `ReadingOut` which already excludes `generation_error`/`prompt_version`/`model_name`/`debug` (threat T-04-08/27, Phase 4). Do not add internal columns to the list/detail schemas. |
| Soft-delete bypass (deleted rows leaking) | Information Disclosure | `deleted_at IS NULL` on every read path (Pitfall 4). |

## Sources

### Primary (HIGH confidence)
- **Codebase (authoritative for this phase):**
  - `backend/app/api/readings.py`, `backend/app/api/users.py` — thin-router pattern, existing `POST /api/readings` + `GET /api/me`.
  - `backend/app/services/reading.py` — `ReadingService`, `_build_response` mapper (reuse for detail), soft-error/200 conventions.
  - `backend/app/services/prompt_engine.py` — confirmed NO history parameter (HIST-05 gate closed).
  - `backend/app/models/reading.py` — `deleted_at`, `user_id` index, `reading_cards` (no `cards` relationship → use explicit select).
  - `backend/app/models/user.py` — `onboarding_completed`/`reversals_enabled`/`allow_history_personalization` flags (defaults present).
  - `backend/app/schemas/reading.py`, `backend/app/schemas/auth.py` — `ReadingOut`/`SettingsOut`/`MeResponse` (reuse), conventions for new schemas.
  - `backend/tests/integration/conftest.py`, `test_readings_auth.py` — the `auth_client`/`auth_session`(savepoint)/`seeded_catalog`/`FakeLLM`/`FakeSafety` harness + the `fake_service` override pattern.
  - `frontend/src/flow/steps.ts`, `flow/FlowRoot.tsx`, `stores/selection.ts` — the `step` state-machine + `AnimatePresence` switch (navigation spine).
  - `frontend/src/hooks/useDecks.ts`, `useSpreads.ts`, `lib/queryClient.ts`, `main.tsx` — TanStack Query v5 patterns (`useQuery`, `keepPreviousData` helper, single `QueryClient`).
  - `frontend/src/api/client.ts` — `apiFetch` Bearer seam.
  - `frontend/src/reading/copy.ts`, `copy.test.ts` — `BANNED_BRAND_TOKENS` (SAFE-06 gate).
  - `frontend/src/components/result/ResultScreen.tsx`, `reading/types.ts`, `reading/createReading.ts` — the `ReadingOut`→`MockReading` mapping + result UI to reuse for detail.
  - `frontend/package.json`, `backend/pyproject.toml` — pinned versions (verified 2026-06-14): React 19.2, TanStack Query ^5, Zustand ^5, motion ^12, Vitest 3.2.6; FastAPI 0.136, SQLAlchemy 2.0, Pydantic 2.13, pytest >=8.
- **`.planning/REFERENCE-TZ.md`** §9.6 (history list contents + empty-state copy «Пока здесь тихо…»), §14.2 (`GET /api/me`, `PATCH /api/me/settings` — exact 3 fields), §14.5 (`GET /api/readings` query params limit/offset/topic/deck_slug, `GET /api/readings/{id}`, `DELETE` soft delete).
- **`.planning/phases/05-history-profile/05-CONTEXT.md`** — the 11 locked decisions (D-01..D-11).
- **`.planning/REQUIREMENTS.md`** — HIST-01..06, PROF-01/02 + traceability.

### Secondary (MEDIUM confidence)
- TanStack Query v5 optimistic-update + invalidation patterns (Pattern 3) — corroborated by the project's existing v5 usage (`useSpreads` `keepPreviousData` helper, `queryClient` config); `[CITED: tanstack.com/query/v5 — Optimistic Updates / Mutations]`. The cache `onMutate`/`onError` recipe is stable across v5.

### Tertiary (LOW confidence)
- None — this phase needed no unverified web research; every claim is grounded in the codebase or the TZ.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — zero new deps; all versions verified against the lockfiles. The phase reuses existing, tested libraries.
- Architecture: **HIGH** — the endpoint pattern (thin router→service), the navigation spine (step-machine), and the server-state ownership (TanStack Query) are all established and directly applicable. The 4 slices map cleanly onto existing seams.
- HIST-05 gate: **HIGH** — verified by grep that `history_context` is absent and `PromptEngine` has no history parameter; the negative requirement is satisfied by construction and only needs a regression lock.
- Pitfalls: **HIGH** — drawn from the actual model/async constraints (no `cards` relationship; async lazy-load) and the locked decisions (cap interaction, user-scoping).
- Open Questions: 4, all LOW-impact and resolvable at plan time (REST shape of restore; cap constant; migration aggressiveness; service placement). None block planning.

**Research date:** 2026-06-14
**Valid until:** 2026-07-14 (stable stack; the only fast-moving surface is TanStack Query minor versions, which do not affect the v5 patterns used). Re-verify lockfile versions if the phase is planned after a dependency bump.
