# Phase 6: Free Limits & Soft Paywall - Context

**Gathered:** 2026-06-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Bound free usage so monetization becomes meaningful: 3 free readings per rolling week with a deterministic reset, an atomic check+decrement (no over-spend under concurrency), a Redis throttle against burst abuse, and an honest, non-pushy paywall surface when free access is exhausted. This phase **completes the limit machinery** Phase 4 started (Phase 4 has the `_get_limits`/`_has_quota`/`_consume_limit` seam that already blocks + decrements `free_used_this_week`, but has no weekly reset, no atomicity, no buckets, no throttle) and adds the frontend paywall + remaining-count surfaces.

**In scope:**
- Backend: per-user rolling weekly reset (LIMIT-02), atomic check+decrement under concurrency (LIMIT-03), the `determine_access` bucket seam free/subscription/paid (LIMIT-04), a Redis throttle gate before Postgres (LIMIT-05), the 3-free-then-block paywall response (LIMIT-01), and a `user_limits` row created at auth.
- Frontend: a soft inline/sheet paywall on the selection screen, a remaining-count surface (selection + un-hidden profile block), and the distinct throttle message.

**Out of scope (later phases):** the Telegram Stars purchase flow (invoice → `successful_payment` → grant), the real tariffs screen, and populating `paid_spreads_balance` / subscription buckets — all **Phase 7**. Phase 6 builds the bucket seam but only the `free` bucket is ever non-zero. Admin/analytics — Phase 8.

</domain>

<decisions>
## Implementation Decisions

### Weekly reset
- **D-01:** Free weekly limit = **per-user rolling 7-day window**, anchored at the **first reading of each window** (`week_start` = timestamp of the first reading after a reset), NOT a fixed ISO-Monday calendar week. **This deliberately OVERRIDES ROADMAP success-criterion-2's literal "ISO week, UTC"** — the criterion's *intent* (exactly 3 per week, deterministic, no extra) is fully preserved; the anchor is per-user for fairness (every user gets a full 7 days from their first reading, not a partial calendar week). Reset is **lazy-on-read**: on the next reading request, if `now − week_start ≥ 7 days`, reset `free_used_this_week = 0` and re-anchor `week_start = now` — NO cron (no queue, PROJECT edit #2). **[Verifier note: do NOT flag this against criterion-2's "ISO week" wording — it is a deliberate, user-approved spec override.]**
- **D-02:** Every user gets a `user_limits` row **at auth (user upsert)** — default `free_weekly_limit = 3`, `free_used_this_week = 0`, `week_start = NULL` (anchors on the first reading). This **fixes the Phase-4 "no row → treated as unlimited" gap** (`_get_limits` returning None was treated as quota); after this, no authenticated user is ever unbounded.

### Paywall surface (payments are Phase 7)
- **D-03:** On exhaustion the paywall shows **"бесплатные расклады закончились + вернутся через N" + a soft "скоро можно будет открыть ещё" note** — NO tariffs, NO dead "buy" buttons (payments are Phase 7). Phase 7 swaps the «скоро» note for the real 1/3/10 + subscription tariffs. Honest for the current state. Copy anchored in TZ §9.8 / §11.2 (no fear, no pressure, "открыть ещё" not "купи").
- **D-04:** The paywall shows a **reset countdown** (days or date — "вернутся через 2 дня" / "обновятся 16 июня"). Especially important under per-user rolling (D-01) where the reset moment differs per user.
- **D-05:** Paywall **form = inline / bottom-sheet on the selection screen** (surfaced where «Начать расклад» is blocked) — NOT a dedicated full tariffs screen. The TZ §9.7 dedicated tariffs screen is deferred to Phase 7 (when tariffs are real). Contextual, minimal, no dead screen.

### Bucket consumption
- **D-06:** `determine_access(limits)` consumes buckets in order **free → subscription → paid_balance** — spend the **expiring** buckets first (free resets weekly, subscription resets per period — use before they lapse), preserve the **permanent** `paid_spreads_balance` last (never expires — the user's "savings"). Maximizes user value. The seam is **built in Phase 6** (success-criterion 5), but only the **free** bucket is ever populated here — `paid`/`subscription` stay 0 until Phase 7 fills them; the same function handles them then with no re-architecture.

### Throttle
- **D-07:** Redis throttle = **moderate (~1 reading / 10–15 s + a short-window burst cap, e.g. ≤ 5 / min)** via `INCR` + `EXPIRE` on a per-user key. It is the **FIRST gate** — runs before the limit check and before Postgres/LLM (success-criterion 4: "before it reaches Postgres"). A real user (readings 30 s+ apart) is never hit. Exact window/cap is the planner's within this band.
- **D-08:** **Distinct messages** for throttle vs limit-exhaustion: throttle → a soft, transient "колода переводит дыхание, подожди мгновение" (HTTP 429, retryable); limit → the paywall (D-03). Different states → different copy; never conflate the transient throttle with the weekly exhaustion.

### Remaining-count surfacing
- **D-09:** Show the **remaining free count** ("осталось N из 3") **subtly near «Начать расклад» on the selection screen AND in the profile** — this **un-hides the Phase-5 D-08 count block** (which was deferred precisely "until the limit is real" = now). Sourced from `GET /api/me` `limits` (already returned). Sets an honest expectation, avoids a surprise block.
- **D-10:** Prominence = **subtle always + a gentle "последний на этой неделе" hint when 1 remains**. No pressure/alarm (brand). The hint gracefully leads into the paywall.

### Claude's Discretion
- Exact reset / throttle / paywall copy (TZ §9.8 limit line + §11.2 no-pressure tone; the «скоро» note) — brand-safe (no «AI/нейросеть/модель»), via `copy.ts`.
- **Atomicity mechanism** for check+decrement (`SELECT … FOR UPDATE` vs atomic `UPDATE … WHERE free_used_this_week < free_weekly_limit … RETURNING`) — success-criterion 3 "no over-spend under concurrency" — research/planner.
- Exact throttle window / burst-cap numbers within the D-07 band; the `INCR`+`EXPIRE` key shape.
- Lazy-reset placement (in the limit seam before the consume); whether to add a dedicated `LimitService` vs extend `ReadingService` (the Phase-4 `_get_limits`/`_has_quota`/`_consume_limit` seam is the extension point) — planner.
- Whether to cache the count in Redis (CLAUDE.md "Redis as fast counter/cache") vs always read PG (PG authoritative) — planner.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project source-of-truth — `.planning/REFERENCE-TZ.md`
- §11.1 — free tier (3 readings/week, all 6 decks, last-10 history); §11.2 — packs UX (no "купи"/fear, "открыть ещё один расклад"); §11.5 — internal balance (`paid_spreads_balance`, free counted separately).
- §9.7 — tariffs screen ("Больше вопросов к колоде") — **deferred to Phase 7**; Phase 6 uses an inline paywall (D-05).
- §9.8 — error/empty copy incl. the limit-exhausted line ("На этой неделе бесплатные расклады закончились. Можно подождать обновления лимита или открыть ещё один расклад за Stars.") — adapt for D-03 (drop the Stars clause until Phase 7).
- §13.11 — `user_limits` columns (`free_weekly_limit`, `free_used_this_week`, `week_start`, `paid_spreads_balance`, `subscription_spreads_limit/used`).
- §29.2 — backend rules: limit checks backend-only; throttle before Postgres.

### Stack & locked decisions
- `CLAUDE.md` → "Redis Usage (edit #2 — no queue)": weekly limit PG-authoritative in `user_limits` + Redis as fast counter/cache; throttle = `INCR`+`EXPIRE` per-user short-window key; idempotency keys optional. NO Celery/RQ/Arq.
- `.planning/REQUIREMENTS.md` — Phase 6 IDs: LIMIT-01..05.
- `.planning/ROADMAP.md` → "Phase 6: Free Limits & Soft Paywall" — goal + 5 success criteria (NOTE criterion-2 "ISO week" is overridden by D-01).

### Prior phases (the seam this phase completes)
- `.planning/phases/04-real-personal-reading-keystone/04-CONTEXT.md` + `backend/app/services/reading.py` — the Phase-4 limit seam (`_get_limits` / `_has_quota` (`free_left = free_weekly_limit − free_used_this_week`) / `_consume_limit` (`free_used_this_week += 1`)) and the locked reading order ("limit check → safety → draw → … → consume"). Phase 6 extends this seam; the throttle becomes the new first gate.
- `.planning/phases/05-history-profile/05-CONTEXT.md` — D-08 (the readings-count / subscription block was HIDDEN in Phase 5 "until Phase 6/7") — D-09 un-hides the count now.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/models/billing.py` — `UserLimits` (all the quota columns). No schema change expected (columns exist).
- `backend/app/services/reading.py` — the Phase-4 limit seam: `_get_limits`, `_has_quota`, `_consume_limit`, and the "limit check → … → consume" order in `create_reading`. Phase 6 extends: lazy weekly reset, atomic decrement, `determine_access` bucket selection, and inserts the throttle as the first gate. The current `_get_limits → None → unlimited` path is the gap D-02 fixes.
- `backend/app/core/redis.py` — `redis_client` (async, `decode_responses=True`, PING-only so far). Phase 6 adds the throttle `INCR`+`EXPIRE` (and optionally a count cache).
- `backend/app/services/telegram_auth.py` — the user upsert; D-02 creates the `user_limits` row here.
- `backend/app/api/deps.py` — auth dep; the throttle may be a FastAPI dependency or a service-layer gate.
- `backend/app/api/users.py` — `GET /api/me` already returns `limits` → the frontend remaining count (D-09) reads from here; no schema change.
- Frontend: `CatalogScreen.tsx` (selection — the inline paywall sheet + the remaining-count near «Начать расклад», D-05/D-09), `ProfileScreen.tsx` (un-hide the Phase-5 D-08 count block, D-09), `useMe.ts` (`limits` source), `reading/copy.ts` (paywall + throttle + count copy, SAFE-06), `createReading.ts` (the 429/limit error branches feeding the paywall vs throttle messages, D-08).

### Established Patterns
- Backend: thin router → service, SQLAlchemy 2.0 async, soft in-character error bodies (no stacktrace). Redis async client shared. PG authoritative, Redis as cache/throttle.
- Frontend: server state in TanStack Query (`useMe` `limits`), client/ephemeral in Zustand; the paywall is a selection-screen state, not a new route (consistent with Phase 5's nav decisions).

### Integration Points
- The reading mutation (`createReading` → `POST /api/readings`) is where the throttle (429) and the limit-block (paywall body) surface; the frontend branches the error into the throttle message (D-08) vs the paywall sheet (D-05).
- `GET /api/me` `limits` feeds the remaining-count (D-09) on selection + profile.

</code_context>

<specifics>
## Specific Ideas

- Brand principle holds hardest here: the paywall must feel like an honest "вернётся через N" + "скоро можно будет открыть ещё", never fear or "узнай правду пока не поздно" (TZ §11.2). The countdown (D-04) is the antidote to a frustrating dead-end.
- Per-user rolling (D-01) is the user's explicit fairness choice over fixed-Monday — every user gets a real 7-day window from when they actually start, and the paywall always tells them exactly when it reopens.

</specifics>

<deferred>
## Deferred Ideas

- Telegram Stars purchase flow (invoice → `successful_payment` → grant), populating `paid_spreads_balance` + subscription buckets, the real tariffs screen (TZ §9.7) — **Phase 7**. D-03/D-05/D-06 leave the seams (the «скоро» note, the inline surface, the free→subscription→paid order).
- A dedicated full paywall/tariffs screen — Phase 7 (Phase 6 is inline/sheet, D-05).
- Heavier anti-abuse (per-IP throttle, CAPTCHA, device fingerprint) — out of MVP scope; the weekly limit + per-user throttle suffice.
- Caching the remaining count in Redis as the read path — optional optimization; PG stays authoritative (planner's call).

</deferred>

---

*Phase: 06-free-limits-soft-paywall*
*Context gathered: 2026-06-14*
