---
phase: 6
slug: free-limits-soft-paywall
status: verified
threats_open: 0
asvs_level: 2
created: 2026-07-05
---

# Phase 6 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verify-only mode: the register was authored at plan time (all four 06-*-PLAN.md
> carry `<threat_model>` blocks). Each threat below was verified against the
> IMPLEMENTATION (file + mechanism/line cited), not documentation or intent.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client → `POST /api/auth/telegram` | Untrusted initData; identity (`telegram_id`) derived ONLY from the validated blob, never the body | initData blob, telegram_id |
| concurrent first-logins → `user_limits` INSERT | Two requests for the same brand-new user could race to insert two rows | user_id, quota defaults |
| Alembic 0002 → existing `user_limits` rows | A `DATE`→`TIMESTAMP` type change must not destroy or NULL existing quota state | week_start column values |
| concurrent `POST /api/readings` → `user_limits` UPDATE | Two requests at the boundary must not both consume a slot (the TOCTOU double-spend) | free_used_this_week counter |
| `create_reading` early exits → `user_limits` counter | Crisis / abusive / honest-fail must leave the net counter correct (READ-10) | free_used_this_week counter |
| client → `POST /api/readings` (burst) | Rapid-fire creation attempts (each a paid LLM call) cross here untrusted | JWT identity, request body |
| request body → throttle key | The throttle must key off identity that cannot be forged | jwt user.id (never a body field) |
| worker crash → Redis throttle counter | A counter without a TTL is a permanent self-lockout | throttle:reading:{user_id} |
| backend response → FE error branching | The FE must discriminate throttle vs paywall vs failure from backend signals only | HTTP status, `reason`, `reset_at` |
| `GET /api/me` limits → displayed count | Non-authoritative display chrome; the real gate is server-side | free_weekly_limit, free_used_this_week, week_start |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-06-01 | Tampering | `user_limits` row-ensure at auth | mitigate | `INSERT … ON CONFLICT (user_id) DO NOTHING` + UNIQUE constraint — verified `telegram_auth._ensure_user_limits` (`backend/app/services/telegram_auth.py:163-172`, `on_conflict_do_nothing(index_elements=["user_id"])`); UNIQUE target `uq_user_limits_user_id` in `models/billing.py:56` + migration `0002:56-58`. A double-login can never create two rows. | closed |
| T-06-02 | Elevation | Phase-4 "no `user_limits` row → unlimited" gap | mitigate | Row ensured at auth BEFORE commit — `telegram_auth.authenticate` calls `_ensure_user_limits` at `:145` then `commit()` at `:146`; `week_start` omitted from `.values()` → NULL anchor. Read path is fail-closed: `_consume_free_gate` returns `None` (paywall) when `limits is None` (`services/reading.py:802-803`). No authenticated user is unbounded. | closed |
| T-06-03 | DoS / data loss | `week_start` `DATE`→`TIMESTAMP` migration | mitigate | `postgresql_using="week_start::timestamptz"` self-heal cast (`alembic/versions/0002_user_limits_rolling_window.py:47-54`), no NULL/no error; fully reversible `downgrade()` (`:61-71`, reverse order — drop constraint then cast back to DATE). Applied under a BLOCKING human checkpoint against a real DB (06-01 Task 4). | closed |
| T-06-04 | Spoofing | identity at the upsert | accept (unchanged) | `telegram_id` still derived only from validated initData — `authenticate` derives it from `parse_user` output (`telegram_auth.py:110-111`, `int(tg["id"])`), never the request body (existing T-04-01 control, untouched by this phase). See Accepted Risks Log RISK-06-A. | closed |
| T-06-05 | Tampering / Elevation | free-quota check+decrement (boundary race) | mitigate | Single conditional `UPDATE … WHERE free_used < limit … RETURNING` — `ReadingService._consume_free_atomic` (`services/reading.py:683-702`): one `update(UserLimits)…returning(...)`; no-slot via `.first() is None` (`:701`); NO `.rowcount`, NO `FOR UPDATE`, NO app lock — PG row lock serializes writers. THE control for success-criterion 3. | closed |
| T-06-06 | Tampering | rolling reset (separate-call double-spend) | mitigate | Reset folded into the SAME atomic UPDATE via `case()` — `services/reading.py:688-698` (`stale`/`first_ever` arms set `free_used=1` + re-anchor within the one statement). Predicate objects `stale`/`fresh_has_room`/`first_ever` defined once (`:672-681`) and reused in BOTH the WHERE `or_()` (`:686`) and the SET `case()` (no drift, Pitfall 5). No read-then-reset-then-decrement window. | closed |
| T-06-07 | Elevation / abuse | over/under-charge on non-success exits | mitigate | Safety runs BEFORE the consume-gate — `create_reading` classifies+routes at `services/reading.py:263-270` (crisis/abusive `_short_circuit`, NO consume) THEN the consume-gate at `:291`. The only post-consume exit (honest-fail) refunds the ACTUALLY-consumed bucket: `_honest_fail(refund=not unlimited, consumed_bucket=…)` (`:349-357`) → `_refund_consumed_bucket` (`:926-942`) → `_refund_free` (`:886-890`) `free_used -= 1` in-transaction + `session.refresh(limits)` (`:1284-1286`). Success path does NOT consume again (`:368-372`). Net counter correct (READ-10). | closed |
| T-06-08 | Information Disclosure | the limit-block body | mitigate | `_soft_body` (`services/reading.py:1327-1341`) carries only `remaining_limits` / `reason` / `reset_at` (the caller's own values) — no cross-user fields, no SQL, no stacktrace. `generation_error` is stored server-side only (`_honest_fail:1271`) and never crosses the boundary (documented `:1267-1268`). Schema fields `reason` / `reset_at` are plain optionals (`schemas/reading.py:287-299`). Deliberate 200 soft body; the global handler stays the 500 path. | closed |
| T-06-09 | Tampering | SQL injection in the new UPDATE/case() | mitigate | Parameterized SQLAlchemy Core throughout `_consume_free_atomic` — `update()` / `case()` / `or_()` / `and_()` with bound column expressions (`services/reading.py:672-700`); no string-built SQL. Same discipline as the existing `on_conflict_do_*`. | closed |
| T-06-10 | Denial of Service | rapid-fire reading creation (cost/abuse) | mitigate | Redis throttle as GATE 0 before any PG/LLM — `throttle_gate` is the FIRST dependency on `POST /readings` (`api/readings.py:49-53`, `dependencies=[Depends(throttle_gate)]`), resolved before the path-op's own `Depends`. `throttle_ok` runs the atomic Lua `INCR`+`EXPIRE` (`core/redis.py:76-80`). Caps the burst at the cheapest layer (60s/cap-5 band). | closed |
| T-06-11 | Denial of Service | stuck throttle counter (permanent lockout) | mitigate | Atomic Lua `INCR` + conditional-`EXPIRE` — `_THROTTLE_LUA` (`core/redis.py:44-48`): `EXPIRE` fires ONLY when `INCR` returns 1 (first hit), inside one script → TTL always armed, never an orphaned counter. Registered once at module load (`:53`). | closed |
| T-06-12 | Spoofing / Tampering | forged `user_id` to dodge the throttle | mitigate | `throttle_gate` keys off the verified JWT `user.id` only — depends solely on `get_current_user` (`api/deps.py:62`), calls `throttle_ok(user.id)` (`:74`); key shape `throttle:reading:{user_id}` (`core/redis.py:77`). Never a request-body field. | closed |
| T-06-13 | Tampering | throttle running after Postgres opens | mitigate | The gate depends ONLY on `get_current_user`, NOT on `get_session` — `throttle_gate` signature has no session param (`api/deps.py:62`), so the 429 short-circuits before any txn (`raise HTTPException(429)` at `:74-75`). Guarded on `POST /readings` only; GET/detail/delete/restore unguarded (`api/readings.py`). success-criterion 4. | closed |
| T-06-14 | Elevation | FE remaining-count / paywall trigger | accept (display-only) | The FE count + the `freeLeft === 0` CTA gate are display chrome — `CatalogScreen.tsx:128` computes `freeLeft` from `useMe` limits, `:213` opens the sheet client-side; catch routes `ReadingError.kind` (`:93-94`, `:198-204`). The AUTHORITATIVE gate is the backend atomic consume (T-06-05, verified) + throttle (T-06-10, verified): a user editing FE state can at most open/skip their own sheet; the server still blocks the 4th reading. See Accepted Risks Log RISK-06-B. | closed |
| T-06-15 | Information Disclosure | the paywall countdown | mitigate | `reset_at` is the caller's OWN reopen moment (`week_start + 7d`) — computed server-side per-user in `_compute_reset_at` (`services/reading.py:945`) and rendered FE-side via `formatReset(resetAt)` (`PaywallSheet.tsx:87`) from the caller's own `SessionLimits.week_start` (`api/auth.ts:35`). No cross-user data (T-05 IDOR discipline on `GET /api/me` upheld). | closed |
| T-06-16 | Spoofing (brand) | new paywall/throttle/count copy | mitigate | All strings in `copy.ts`, scanned by `BANNED_BRAND_TOKENS` `/ai|нейросет|модель|сгенерирован|(?:^\|[^а-яё])ии(?:[^а-яё]\|$)/i` (`reading/copy.ts:17-18`). New constants `PAYWALL_TITLE`/`PAYWALL_RESET_LEAD`/`PAYWALL_DISMISS`/`THROTTLE_MESSAGE`/`LIMIT_REMAINING_PREFIX`/`LIMIT_LAST_ONE_HINT`/`PROFILE_LIMIT_LABEL` present (`:183-200`), RU, no AI/нейросеть/модель tokens; enforced by `copy.test.ts` (SAFE-06). | closed |
| T-06-17 | Tampering | XSS via rendered count/reset/identity | mitigate | Every value renders as a React text node — no `dangerouslySetInnerHTML` in `PaywallSheet.tsx`, `ThrottleToast.tsx`, or `CatalogScreen.tsx` (grep clean; the only occurrences are Phase-4 `ResultScreen.tsx` + a test file, out of Phase-6 scope). `reset` via `formatReset` (`PaywallSheet.tsx:87`), message via `{THROTTLE_MESSAGE}` (`ThrottleToast.tsx:61`) — both interpolated text. | closed |
| T-06-SC | Tampering | npm/pip installs (supply chain) | accept (mitigate — zero new deps) | Zero new runtime dependencies this phase — verified in all four SUMMARY `tech-stack.added: []` (06-01/02/03/04); throttle reuses redis-py (already pinned `>=5.2,<6`, `core/redis.py:1`), FE surfaces hand-authored against existing components + `motion` (already in the lockfile). No package added by any of the four plans. See Accepted Risks Log RISK-06-C. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| RISK-06-A | T-06-04 | Identity at the `user_limits`/user upsert is derived ONLY from the validated Telegram `initData` blob (existing T-04-01 control at `telegram_auth.py:110-111`), never the request body. This phase does not touch that surface; the risk is inherited-and-unchanged, not newly introduced. | GSD security-auditor (verify-only) | 2026-07-05 |
| RISK-06-B | T-06-14 | The FE remaining-count and the `freeLeft === 0` CTA pre-check are non-authoritative display chrome. The server-side atomic consume (T-06-05) and Redis throttle (T-06-10) are the authoritative gates and are both code-verified. A user tampering with FE state can at most open or skip their OWN paywall sheet; the server still blocks the 4th reading and the burst. Accepted per the Architectural Responsibility Map (display tier). | GSD security-auditor (verify-only) | 2026-07-05 |
| RISK-06-C | T-06-SC | Zero new runtime dependencies introduced by Phase 6 (verified across all four plan SUMMARYs, `tech-stack.added: []`). The throttle reuses the already-pinned redis-py; the FE surfaces are hand-authored against existing components and `motion` already in the lockfile. No install-time supply-chain surface was added. The plan-time gate (any added package → blocking human checkpoint) was never triggered. | GSD security-auditor (verify-only) | 2026-07-05 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-05 | 18 | 18 | 0 | gsd-security-auditor (verify-only, ASVS L2) |

**Unregistered flags:** none. No `## Threat Flags` section is present in any of the four
06-*-SUMMARY.md, and no new attack surface was declared during implementation. All new
surface (the atomic consume-gate, the Redis throttle GATE 0, the FE paywall/throttle/count
surfaces) maps to registered threats T-06-01..T-06-17 + T-06-SC.

**Notes on known deferred debt (NOT new, per audit scope):** the atomic consume-gate + the
honest-fail refund were re-verified during the Phase-7 review; the subscription window-gate
(CR-01 at `services/reading.py:805-818`) was FIXED in Phase 7 (commit 73b26ee) and is not
re-flagged here. `PaywallSheet.tsx` now renders `ShopTariffs` (`:24,:92`) — the documented
Phase-7 seam ("swap PAYWALL_SOON_NOTE for a real purchase affordance behind the same sheet"),
not a Phase-6 regression; the Phase-6 controls (no cross-user data, brand-safe copy, React
text nodes) remain intact.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log (RISK-06-A/B/C)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-05
