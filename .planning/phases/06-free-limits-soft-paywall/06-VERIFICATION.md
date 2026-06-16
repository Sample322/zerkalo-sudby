---
phase: 06-free-limits-soft-paywall
verified: 2026-06-16T00:00:00Z
status: human_needed
score: 5/5 must-haves verified (code-level); 3 live user-smokes pending
overrides_applied: 0
mode: mvp
mvp_goal_format: non-user-story  # goal is an outcome description, not "As a... I want... so that..."
re_verification:
  previous_status: none
  note: initial verification
human_verification:
  - test: "Apply migration 0002 against a live database (06-01 Task 4, BLOCKING checkpoint)"
    expected: "alembic upgrade head applies cleanly; alembic current shows 0002_user_limits_rolling_window; \\d user_limits shows week_start = timestamp with time zone + uq_user_limits_user_id UNIQUE; existing ISO-Monday DATE rows self-heal to midnight timestamptz (not NULL, not errored); downgrade -1 then upgrade head succeeds"
    why_human: "No Docker/Postgres in the agent environment (locked env constraint). Migration authored against Base.metadata but never applied. test_double_login_single_limits_row stays xfail until applied."
  - test: "Live concurrency-race proof + rolling-reset + paywall/refund (06-02 user-smokes, need live Postgres + applied 0002)"
    expected: "test_limit_concurrency.py: two gathered create_reading at boundary (used=2,limit=3) → exactly one completed + one failed, free_used_this_week == 3 (NEVER 4). Mutation test: break the WHERE free_used<limit guard → test observes used==4 and goes red. test_limits_reset.py: stale window resets to used=1+re-anchors; within-window stays blocked; NULL anchors. test_paywall_block.py + test_readings_limit.py: paywall body carries reason='paywall'+reset_at; honest-fail refunds net-0; all 5 untouched-on-* green."
    why_human: "True cross-connection PostgreSQL row-lock concurrency needs a live DB (the committed two-connection fixture skips without Postgres). LIMIT-03 success-criterion-3 is a security control proven only by the live race."
  - test: "Live throttle burst (06-03 user-smoke, needs live Redis)"
    expected: "With Redis up + a valid Bearer JWT, fire >5 POST /api/readings within 60s → the 6th returns HTTP 429 'throttled'; the throttled request opens NO Postgres session and makes NO LLM call (fake_llm.calls==0, no reading row); after the 60s window a fresh request passes; two readings ≥30s apart are never throttled."
    why_human: "No Docker/Redis in the agent environment; fakeredis not installed. The 3 test_throttle.py tests skip cleanly without Redis. LIMIT-05 success-criterion-4 live proof requires a real Redis."
  - test: "Render the three FE surfaces in the real Telegram Mini App with a live exhausted-limit + 429 state (06-04 Task 4, BLOCKING checkpoint)"
    expected: "Paywall: on the 4th reading the soft bottom-sheet «На этой неделе бесплатные расклады закончились» surfaces with an accent-tinted «вернутся через N дней»/date countdown + «скоро ещё» note, NO buy/price/Stars, NO red/alarm hue, dismiss preserves question+selections. Count: «Осталось N из 3» quietly near the CTA at 2 and 3 left, «Последний расклад на этой неделе» accent at exactly 1, suppressed at 0, same count in profile. Throttle: rapid >5/60s requests show the transient «Колода переводит дыхание» toast that auto-dismisses (~3.75s) and is visibly distinct from the sheet, then a normal-paced retry works. Brand: zero AI/ИИ/нейросеть/модель or fear/pressure copy on all three surfaces."
    why_human: "Real Telegram WebView rendering (per-deck atmosphere, safe-area, motion, live exhausted-limit + 429 state) cannot be verified headlessly. Plan 06-04 is autonomous:false — the executor stopped at this checkpoint."
---

# Phase 6: Free Limits & Soft Paywall — Verification Report

**Phase Goal:** Free usage is bounded so monetization becomes meaningful — the user gets 3 free readings per week with a deterministic, anchored weekly reset and atomic check+decrement (no over-spend under concurrency), a Redis throttle against abuse, and an honest, non-pushy paywall surface when free access is exhausted.

**Verified:** 2026-06-16
**Status:** human_needed
**Re-verification:** No — initial verification

> **MVP-mode note (format discrepancy, non-blocking):** the phase has `mode: mvp` but its ROADMAP goal is an **outcome description**, not a User Story («As a [role], I want to [capability], so that [outcome].»). `gsd-sdk query user-story.validate` returns `valid=false`. Per the verifier MVP contract this is normally surfaced as a discrepancy with a request to run `/gsd mvp-phase 6`. Because the goal IS a clear, testable technical outcome and the verification_context directs full technical + requirement verification, this report verifies goal-backward against the five ROADMAP Success Criteria (the contract) rather than refusing. **Recommendation:** reformat the Phase-6 goal to User-Story shape if the MVP user-flow framing is desired for future re-verification; it does not change any code finding below.

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria — the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | After 3 free readings in a week the user is blocked from a 4th and sees a soft, in-character paywall (no fear/pressure) | ✓ VERIFIED (code) | `reading.py:278-286` atomic gate returns None → `_soft_body(reason="paywall", reset_at=...)` no draw; `reading.py:106-109` SOFT_PAYWALL_COPY (honest, no pressure); FE `PaywallSheet.tsx:1-145` bottom-sheet, NO purchase affordance/price/Stars, NO red/alarm hue, dismiss preserves selections; copy.ts:174-180 brand-safe RU. Live Mini-App render = user-smoke. |
| 2 | The free counter resets based on a stored `week_start` so a boundary user gets exactly 3/week — not extra | ✓ VERIFIED (code, user-approved deviation) | `reading.py:647-672` folded `case()` reset: stale (week_start ≤ now−7d) → used=1+re-anchor; NULL → used=1+anchor; fresh-room → +1; fresh-no-room → 0 rows → paywall. **D-01 per-user rolling 7-day deliberately OVERRIDES ROADMAP SC-2's "ISO week, UTC" (user-approved); intent "exactly 3/week" preserved.** Migration 0002 makes week_start TIMESTAMP. Live reset run = user-smoke. |
| 3 | Two concurrent requests at the boundary cannot both succeed (atomic check+decrement); free/paid/subscription = 3 independent buckets | ⚠ VERIFIED (code) / live race = user-smoke | `reading.py:658-677` ONE `update(UserLimits).where(or_(stale,first_ever,fresh_has_room)).values(case(...)).returning(...)`; no-slot via `.first() is None` (not rowcount); NO FOR UPDATE/app lock — the row lock IS the control. 3 buckets independent in `Bucket`/`determine_access` (free/sub/paid counted separately; only FREE populated, Phase-7 seam). Static mutant-compile proof in 06-02-SUMMARY. **Live cross-connection race = user-smoke (needs Postgres).** |
| 4 | Burst spamming of reading creation is throttled via Redis before it reaches Postgres | ✓ VERIFIED (code) / live burst = user-smoke | `redis.py:44-80` atomic Lua `INCR`+conditional-`EXPIRE` (TTL only on count==1, no stuck-counter), key `throttle:reading:{user_id}`, 60s/5; `deps.py:62-75` `throttle_gate` depends ONLY on `get_current_user` (no get_session), raises 429; `readings.py:49-53` wired as `dependencies=[Depends(throttle_gate)]` on POST only → resolves before get_session opens a txn. **Live burst→429 = user-smoke (needs Redis).** |
| 5 | Before each reading the backend determines access (free/paid/sub) and consumes from the correct bucket | ✓ VERIFIED | `reading.py:147-174` pure `determine_access` (free→sub→paid order); `reading.py:679-706` `_consume_free_gate` routes Bucket.FREE → atomic consume, fail-closed on missing row; `create_reading:274-288` calls the gate before any draw. Behavioral spot-check passed (free/none/stale/sub-order all correct). |

**Score:** 5/5 truths verified at code level. Truths 3 & 4 additionally carry a live user-smoke (DB/Redis race + burst); Truth 2 carries a user-approved deviation from SC-2 wording.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/0002_user_limits_rolling_window.py` | week_start DATE→TIMESTAMP(tz) + UNIQUE(user_id), reversible | ✓ VERIFIED | down_revision=0001; upgrade alter_column +postgresql_using cast + create_unique_constraint; downgrade reverses both. Authored, NOT applied (user-smoke). |
| `backend/app/models/billing.py` | UserLimits.week_start TIMESTAMP + UniqueConstraint | ✓ VERIFIED | `week_start: Mapped[datetime\|None]` TIMESTAMP(timezone=True) (l.58-60); `__table_args__=(UniqueConstraint("user_id", name="uq_user_limits_user_id"),)` (l.44) — name matches migration. |
| `backend/app/schemas/reading.py` | ReadingOut += reason + reset_at | ✓ VERIFIED | `reason: str\|None` (l.283), `reset_at: datetime\|None` (l.290), both default None, serialized. |
| `backend/app/services/telegram_auth.py` | race-safe ON CONFLICT DO NOTHING, week_start NULL, _current_week_start removed | ✓ VERIFIED | `_ensure_user_limits` (l.145-164) pg_insert(...).on_conflict_do_nothing(index_elements=["user_id"]); week_start omitted → NULL; no `_current_week_start` in file. |
| `backend/app/services/reading.py` | determine_access + Bucket + _consume_free_atomic + refund + create_reading rewire | ✓ VERIFIED | All present + substantive (1161 lines, full module). Behavioral spot-check of determine_access passed. |
| `backend/app/core/redis.py` | Lua throttle + throttle_ok | ✓ VERIFIED | register_script(_THROTTLE_LUA) (l.53), throttle_ok int(count)<=cap (l.60-80), 60s/5 band. |
| `backend/app/api/deps.py` | throttle_gate 429 | ✓ VERIFIED | throttle_gate depends only on get_current_user, raises 429, no get_session (l.62-75). |
| `frontend/src/reading/createReading.ts` | discriminated ReadingError (throttle/paywall/failure) + resetAt | ✓ VERIFIED | ReadingError extends Error w/ kind+resetAt (l.37-48); 429→throttle, reason==="paywall"→paywall+reset_at, else→failure (l.187-209); success path/signature/MockReading unchanged. |
| `frontend/src/reading/limitCopy.ts` | formatRemaining + formatReset | ✓ VERIFIED | formatRemaining clamp≥0+NaN-guard (l.28-32); formatReset RU plural/genitive/«совсем скоро» fallback (l.74-92). 12 limitCopy tests pass. |
| `frontend/src/components/PaywallSheet.tsx` | bottom-sheet, countdown, no purchase/alarm | ✓ VERIFIED | scrim+glass sheet, PAYWALL_* copy, formatReset accent-tinted, dismiss; no Stars/buy/price; SDK safe-area (no env/100vh); m.* motion. |
| `frontend/src/components/ThrottleToast.tsx` | transient auto-dismiss toast | ✓ VERIFIED | setTimeout ~3750ms cleared on unmount, THROTTLE_MESSAGE, no buttons, role=status, distinct pill. |
| `frontend/src/components/CatalogScreen.tsx` | paywall trigger + catch routing + count | ✓ VERIFIED | freeLeft===0 pre-check opens sheet; catch kind-switch → 3 surfaces; «Осталось N из 3» + 1-remaining hint; both surfaces rendered. |
| `frontend/src/components/profile/ProfileScreen.tsx` | un-hidden free-count block | ✓ VERIFIED | GLASS block between identity & settings (l.197-209), PROFILE_LIMIT_LABEL+formatRemaining, free count only, omission comment → D-09. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| telegram_auth `_ensure_user_limits` | user_limits row (week_start NULL) | `on_conflict_do_nothing(index_elements=["user_id"])` | ✓ WIRED | l.155-164; relies on uq_user_limits_user_id (migration 0002). |
| migration 0002 | user_limits.week_start | `alter_column` DATE→TIMESTAMP +postgresql_using | ✓ WIRED | l.47-54. |
| reading.py create_reading | user_limits (atomic) | `update().where(...).values(case(...)).returning(...)` | ✓ WIRED | l.658-677; `.first() is None` no-slot. |
| consume-gate None branch | soft paywall body w/ reset_at | `_compute_reset_at(week_start)=week_start+7d` | ✓ WIRED | l.280-286 + l.723-731. |
| _honest_fail | free_used refund | compensating `free_used = free_used - 1` UPDATE | ✓ WIRED | l.1053-1056 + `_refund_free` l.708-721. |
| readings.py POST /readings | throttle_gate | `dependencies=[Depends(throttle_gate)]` | ✓ WIRED | l.49-53; POST only (GET/delete/restore unguarded — confirmed). |
| deps.py throttle_gate | Redis INCR+EXPIRE | `throttle_ok(user.id)` key throttle:reading:{user_id} | ✓ WIRED | deps.py l.72-75 → redis.py l.76-79. |
| CatalogScreen handleStart catch | PaywallSheet/ThrottleToast/failure band | switch on `ReadingError.kind` | ✓ WIRED | CatalogScreen l.155-167. |
| CatalogScreen + ProfileScreen | GET /api/me limits | `useMe().data.limits` → formatRemaining | ✓ WIRED | Catalog l.95-98,382-385; Profile l.197-207. |
| PaywallSheet | per-user reset moment | `formatReset(resetAt)` after PAYWALL_RESET_LEAD | ✓ WIRED | PaywallSheet l.106-108. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| PaywallSheet | `resetAt` prop | CatalogScreen: `err.resetAt` (from backend `reset_at`=week_start+7d) OR `computeResetAt(limits.week_start)` | Yes — real reset moment off `GET /api/me` week_start or the 200 paywall body | ✓ FLOWING |
| CatalogScreen count | `freeLeft` | `useMe().data.limits.free_weekly_limit − free_used_this_week` (real GET /api/me) | Yes — live limits, not hardcoded | ✓ FLOWING |
| ProfileScreen block | `data.limits` | `useMe()` → GET /api/me (LimitsOut serializes the user_limits row) | Yes | ✓ FLOWING |
| ReadingOut.reason/reset_at | backend response | `_consume_free_atomic` RETURNING + `_compute_reset_at` (real DB row, real week_start) | Yes — atomic UPDATE returns the real persisted counter | ✓ FLOWING |

No HOLLOW/DISCONNECTED/HOLLOW_PROP artifacts found. `freeLeft===0`/`paywallResetAt` initial states are overwritten by `useMe`/the catch before display (not stubs).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| determine_access free-room | `determine_access(L(used=0,ws=now))` | `free` | ✓ PASS |
| determine_access exhausted-fresh | `determine_access(L(used=3,ws=now))` | `none` | ✓ PASS |
| determine_access exhausted-stale (reset) | `determine_access(L(used=3,ws=now−8d))` | `free` | ✓ PASS |
| determine_access null-exhausted (deviation) | `determine_access(L(used=3,ws=None))` | `none` | ✓ PASS |
| determine_access bucket-order (sub before paid) | `determine_access(L(used=3,sub_lim=5,paid=10))` | `subscription` | ✓ PASS |
| WINDOW constant | `WINDOW == timedelta(days=7)` | `True` | ✓ PASS |
| Backend suite | `uv run pytest -q` | 83 passed, 77 skipped, 3 xpassed, 0 failed | ✓ PASS (baseline) |
| Frontend suite | `node_modules/.bin/vitest run` | 117 passed, 0 failed (19 files) | ✓ PASS (baseline) |
| Frontend typecheck | `tsc --noEmit` | exit 0, 0 errors | ✓ PASS |
| FE pure-fn (formatRemaining/formatReset) | covered by 12 limitCopy.test.ts (in the 117) | green | ✓ PASS |
| Red-stub symbol references | grep stub files for contract symbols | all reference determine_access/_consume_free/throttle_ok/throttle_gate/reason/reset_at + asyncio.gather | ✓ PASS |

> 77 backend skips = DB/Redis integration tests that SKIP locally (no Docker daemon — Postgres/Redis unavailable, locked env constraint). NOT a gap. 3 xpassed = the `determine_access` pure-fn stubs that flipped green when the symbol landed.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| LIMIT-01 | 06-01, 06-04 | Бесплатный лимит 3 расклада/неделя per-user (user_limits) | ✓ SATISFIED | `_FREE_WEEKLY_LIMIT=3` (telegram_auth l.43); free_weekly_limit server_default 3 (billing l.49-51); FE paywall at exhaustion. Live exhaustion render = user-smoke. |
| LIMIT-02 | 06-01, 06-02 | Недельный лимит сбрасывается (week_start) | ✓ SATISFIED | Folded `case()` rolling reset (reading.py l.647-672); week_start TIMESTAMP (migration 0002). Live reset = user-smoke. |
| LIMIT-03 | 06-02, 06-04 | Перед раскладом проверяется доступ; при исчерпании — мягкий paywall | ✓ SATISFIED (code) | Atomic check+decrement (reading.py l.658-677) + determine_access gate; soft paywall body. Live concurrency race = user-smoke. |
| LIMIT-04 | 06-02 | Платные из paid_spreads_balance, подписочные из sub-лимита; бесплатные отдельно | ✓ SATISFIED | `Bucket` (free/sub/paid/none) + determine_access free→sub→paid order; 3 independent counters in UserLimits; only FREE populated (sub/paid are Phase-7 seam, correctly counted-separately now). |
| LIMIT-05 | 06-03, 06-04 | Anti-abuse/rate-limit через Redis (атомарный throttle) | ✓ SATISFIED (code) | Atomic Lua throttle GATE 0 (redis.py + deps.py + readings.py). Live burst→429 = user-smoke. |

**All 5 Phase-6 requirement IDs accounted for.** REQUIREMENTS.md maps LIMIT-01..05 → Phase 6 (marked Complete), and every ID is declared across the 4 plans' `requirements:` frontmatter (06-01:[LIMIT-01,02]; 06-02:[LIMIT-02,03,04]; 06-03:[LIMIT-05]; 06-04:[LIMIT-01,03,05]). No orphaned requirements — no LIMIT-* maps to Phase 6 in REQUIREMENTS.md without appearing in a plan.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| frontend/src/reading/copy.ts | 60 | `QUESTION_PLACEHOLDER` constant | ℹ Info | Legitimate textarea placeholder copy («О чём спросим колоду?») — NOT a stub. No action. |

No `TODO`/`FIXME`/`XXX`/`TBD`/`HACK`/"not implemented"/"coming soon" debt markers in any Phase-6 modified file. No empty-return or hollow-prop stubs. The only `placeholder` hit is a real UI placeholder string, not a debt marker. **No blockers.**

### Deferred Items (informational — not Phase-6 gaps)

| # | Item | Disposition | Evidence |
|---|------|-------------|----------|
| 1 | `models/spread.py:38,56` UP037 ruff lint | Pre-existing since Phase 2 (logged in 05 + 06 deferred-items.md); NOT a Phase-6 file. Out of scope. | `deferred-items.md`; all 3 touched 06-02 files lint clean. |
| 2 | Bucket SUBSCRIPTION/PAID arms unpopulated | Phase-7 seam by design (LIMIT-04 = "3 independent buckets counted separately" IS met; only FREE populated until payments) | Phase 7 goal: «buying packs / subscription through Telegram Stars» — fills sub/paid balances. |

These do NOT affect status.

### Human Verification Required

4 deploy-time user-smokes (consistent with Phase 4/5 HUMAN-UAT pattern; classified `human_needed`, not gaps):

1. **Apply migration 0002 against a live DB** (06-01 Task 4, BLOCKING) — `alembic upgrade head`, confirm week_start→timestamptz + UNIQUE, self-heal of existing rows, reversibility. Needs Postgres.
2. **Live concurrency race + rolling reset + paywall/refund** (06-02) — the LIMIT-03 boundary-race proof (used==3 never 4) + mutation test (broken guard → used==4) + reset/paywall/refund DB tests. Needs Postgres + applied 0002.
3. **Live throttle burst** (06-03) — >5/60s → 429, no PG session/LLM call, window recovery. Needs Redis.
4. **Render the 3 FE surfaces in the real Telegram Mini App** (06-04 Task 4, BLOCKING) — paywall sheet+countdown, remaining-count + 1-remaining hint + profile block, throttle toast distinct from sheet, brand-safe copy — against a live exhausted-limit + 429 state. Needs deployed build + live backend.

(Full test/expected/why_human in the frontmatter `human_verification` block.)

### Gaps Summary

**No gaps.** All five ROADMAP Success Criteria are achieved at the code level: the atomic folded-reset `UPDATE…RETURNING` consume-gate (no over-spend by construction — the PostgreSQL row lock is the control), the per-user rolling 7-day reset (D-01, user-approved override of SC-2's "ISO week" wording with intent preserved), the bucket policy (`determine_access` free→sub→paid; 3 independent counters), the atomic Lua Redis throttle wired as GATE 0 before any Postgres session, and the honest non-pushy soft paywall (no purchase affordance, no alarm hue, brand-safe copy) routed via a discriminated `ReadingError` to three distinct FE surfaces. All artifacts exist, are substantive, wired, and data-flowing. Backend 83 pass / 77 skip (DB/Redis env-skips, not gaps) / 0 fail; frontend 117 pass / 0 fail; tsc clean. Every Phase-4 untouched-on-* invariant (READ-10) is preserved via safety-before-consume-gate + refund-only-on-honest-fail.

The status is **human_needed** (not passed) solely because four deploy-time live-DB/Redis/Mini-App user-smokes remain — the migration apply (06-01 Task 4) and the FE surface render (06-04 Task 4) are explicit BLOCKING checkpoints the executor correctly stopped at, and the concurrency/throttle live proofs require infrastructure absent from the agent environment. None of these are code defects; they are the irreducible live-verification surface for a limits/throttle phase.

---

_Verified: 2026-06-16_
_Verifier: Claude (gsd-verifier)_
