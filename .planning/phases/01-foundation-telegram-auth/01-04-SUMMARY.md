---
phase: 01-foundation-telegram-auth
plan: 04
subsystem: auth
tags: [telegram-initdata, hmac-sha256, pyjwt, fastapi-security, postgres-upsert, admin-allowlist, soft-error-handler, sentry, infra-05]

requires:
  - phase: 01-01
    provides: "pydantic-settings (ADMIN_TELEGRAM_IDS/JWT_SECRET/BOT_TOKEN/INITDATA_MAX_AGE_SECONDS/JWT_EXPIRE_SECONDS), async session + get_session dep, structured JSON logging, main.py Plan-04 router/handler seam, conftest make_init_data two-stage-HMAC signer + DB-gated skip fixtures"
  - phase: 01-02
    provides: "User (telegram_id BIGINT UNIQUE) + UserLimits (free_weekly_limit/free_used_this_week/week_start) models; users.telegram_id UNIQUE backs the ON CONFLICT upsert"
provides:
  - "validate_init_data — hand-rolled two-stage HMAC (secret=HMAC_SHA256(b'WebAppData', bot_token)) with hmac.compare_digest + auth_date freshness; forged/tampered/stale/missing-hash -> ValueError"
  - "core/security.py encode_jwt/decode_jwt — PyJWT HS256 pinned (alg:none rejected), exp auto-verified"
  - "services.telegram_auth.authenticate — validate -> derive telegram_id ONLY from validated user -> atomic INSERT...ON CONFLICT (telegram_id) upsert + ensure user_limits row -> issue JWT"
  - "POST /api/auth/telegram (thin router) returning {access_token, user, limits, settings}; generic 401 on any validation failure"
  - "get_current_user (HTTPBearer JWT) + require_admin (ADMIN_TELEGRAM_IDS allowlist) deps in api/deps.py"
  - "GET /api/me (Bearer-protected profile) + GET /api/admin/ping (require_admin probe, 403/200)"
  - "INFRA-05: global Exception handler -> 500 soft in-character JSON (no stacktrace leak) + structured logging + no-op init_sentry seam"
affects: [frontend-auth-wiring, deck-catalog, readings, payments, admin-panel]

tech-stack:
  added: []
  patterns:
    - "Hand-rolled initData validator EXACTLY to the Telegram two-stage HMAC spec, stdlib hmac/hashlib only, constant-time compare; the one place 'hand-rolled' means 'to the published algorithm'"
    - "Identity derived ONLY from the validated user blob (int(tg['id'])) — request body never trusted for telegram_id (T-04-01)"
    - "Atomic Postgres upsert via sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_update(index_elements=[User.telegram_id]).returning(User) — no SELECT-then-INSERT race (T-04-09)"
    - "Thin routers delegate to services/ so the bot/admin can reuse the same logic without HTTP (Phase 7)"
    - "decode_jwt pins algorithms=['HS256'] so alg:none is refused; ExpiredSignatureError/InvalidTokenError -> 401 in get_current_user"
    - "Generic single 401 message for every initData failure cause (no oracle, T-04-07)"
    - "Global Exception handler returns soft RU JSON; HTTPException/RequestValidationError handlers left intact so 401/403/422 keep semantics; full detail logged server-side via logger.exception (T-04-06)"
    - "init_sentry() strict no-op when SENTRY_DSN unset + guarded import so a missing sentry-sdk never raises"
    - "Transaction-isolated integration session: outer txn on a dedicated connection + AsyncSession(join_transaction_mode='create_savepoint'), get_session overridden, rolled back at teardown — survives the service's inner commit()"

key-files:
  created:
    - backend/app/core/security.py
    - backend/app/core/errors.py
    - backend/app/core/sentry.py
    - backend/app/services/__init__.py
    - backend/app/services/telegram_auth.py
    - backend/app/schemas/__init__.py
    - backend/app/schemas/auth.py
    - backend/app/api/auth.py
    - backend/app/api/users.py
    - backend/app/api/admin.py
    - backend/tests/integration/conftest.py
  modified:
    - backend/app/api/deps.py
    - backend/app/core/config.py
    - backend/app/main.py
    - backend/tests/unit/test_initdata.py
    - backend/tests/integration/test_auth_flow.py
    - backend/tests/integration/test_me.py
    - backend/tests/integration/test_admin_guard.py
    - backend/tests/integration/test_error_shape.py

key-decisions:
  - "initData validator kept pure (no DB) so the four mandated failure modes are unit-tested without Postgres; the DB upsert lives in a separate authenticate() orchestration in the same module"
  - "JWT sub = user UUID (str); telegram_id carried as a convenience claim; PyJWT verifies exp automatically — get_current_user maps Expired/Invalid to 401, unknown sub to 401"
  - "ensure user_limits via SELECT-then-insert-if-absent (idempotent) rather than a second upsert, so a repeat login never creates a second limits row; week_start = Monday of the current UTC ISO week"
  - "auth router maps every ValueError to one generic HTTPException(401, 'authentication failed') — failure cause stays server-side (no oracle)"
  - "soft-error handler registered for bare Exception only; FastAPI keeps its HTTPException/validation handlers so 401/403/422 are unaffected (verified the error test does not perturb the auth 401/403 tests)"
  - "Sentry minimal seam only (no-op without DSN, guarded import); full dashboards/alerting deferred to Phase 8 per RESEARCH Open Question #4 — did not over-build observability"
  - "is_premium_telegram populated from the validated user blob's is_premium flag on insert"

patterns-established:
  - "Two-stage HMAC + freshness + constant-time compare as the canonical initData gate; warning sign of a broken validator is the absence of the b'WebAppData' constant or telegram_id read from the body"
  - "authenticate() is the single TelegramAuthService entrypoint the bot (Phase 7) and any future server-to-server path reuse"
  - "Integration tests share one transaction-isolated AsyncSession with the ASGI app via dependency_overrides[get_session] + create_savepoint, and skip cleanly when Postgres is unreachable"

requirements-completed: [AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, INFRA-05]

duration: 40min
completed: 2026-06-10
---

# Phase 01 Plan 04: Telegram Auth Security Spine Summary

**The full backend auth security spine: a hand-rolled two-stage Telegram `initData` HMAC validator (`secret = HMAC_SHA256(b"WebAppData", bot_token)`, constant-time `hmac.compare_digest`, `auth_date` freshness) + PyJWT HS256 issuance/verification (`alg:none` refused), `POST /api/auth/telegram` that validates → derives `telegram_id` ONLY from the validated `user` → atomically upserts the user (+`user_limits`) → returns a JWT, the `get_current_user` Bearer dependency + `GET /api/me`, the server-side `require_admin` allowlist with a `GET /api/admin/ping` probe (403/200), and the INFRA-05 global soft-error handler that returns in-character RU JSON with no stack-trace leak plus a no-op Sentry seam.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-06-10T13:45Z
- **Completed:** 2026-06-10T14:25Z
- **Tasks:** 3 executed (Task 1 + Task 2 TDD; Task 3 INFRA-05)
- **Files modified:** 19 (11 created, 8 modified)

## Accomplishments

- **AUTH-02 — initData two-stage HMAC (the spine):** `services/telegram_auth.py::validate_init_data` implements the documented algorithm EXACTLY (stdlib `hmac`/`hashlib`, `parse_qsl(strict_parsing=True)`, key-sorted `\n`-joined `data_check_string` sans `hash`/`signature`, `secret = HMAC_SHA256(b"WebAppData", bot_token)`, constant-time `hmac.compare_digest`) and enforces `auth_date` freshness against `INITDATA_MAX_AGE_SECONDS`. Forged hash, tampered field, stale `auth_date`, missing `hash`, and a wrong-bot-token signature all raise — proven by 10 DB-free unit tests using the conftest `make_init_data` signer.
- **AUTH-04 — JWT (T-04-03):** `core/security.py` `encode_jwt`/`decode_jwt` (PyJWT HS256). `decode_jwt` pins `algorithms=["HS256"]`, so an `alg:none` token and a wrong-secret token are both rejected; `exp` is auto-verified (expired → `ExpiredSignatureError`). All asserted in unit tests.
- **AUTH-01/03 — auth endpoint + upsert:** `POST /api/auth/telegram` (thin router) → `authenticate()` validates, derives `telegram_id` only from the validated `user` blob, runs one atomic `INSERT ... ON CONFLICT (telegram_id) DO UPDATE ... RETURNING User`, ensures a `user_limits` row (free_weekly_limit=3, week_start=current Monday), and returns `{access_token, user, limits, settings}`. Integration tests assert valid → 200 + JWT (sub = user.id) + a single user + a limits row, and repeat → `last_seen_at` advanced with exactly one user row.
- **AUTH-04 — Bearer dependency + `/api/me`:** `get_current_user` (HTTPBearer → `decode_jwt` → `session.get(User, sub)`; 401 on expired/invalid/unknown) protects `GET /api/me`, which returns the profile + limits + settings. Tests cover accept / missing / malformed / expired.
- **AUTH-05 — server-side admin allowlist:** `require_admin` rejects any `telegram_id` not in `settings.ADMIN_TELEGRAM_IDS` (403, deny-by-default); `GET /api/admin/ping` is the testable probe (403 for non-allowlisted, 200 `{"ok": true}` for allowlisted).
- **INFRA-05 — soft errors + logging + Sentry seam:** `core/errors.py` global `Exception` handler returns `500 {"error":"soft","message":"Колода сейчас молчит. Попробуй чуть позже."}` with the full detail logged server-side via `logger.exception` — no stack trace, exception class, file path, or secret in the body (verified live). FastAPI's HTTPException/validation handlers are left intact so 401/403/422 keep their semantics. `core/sentry.py::init_sentry()` is a strict no-op when `SENTRY_DSN` is unset and never raises if `sentry-sdk` is absent (guarded import); structured JSON logging from Plan 01 is wired on startup.

## Task Commits

Each task committed atomically on `gsd/phase-01-foundation-telegram-auth`:

1. **Task 1: two-stage initData HMAC validator + PyJWT HS256 helpers** (TDD) — `1c75cfb` (feat). RED: `tests/unit/test_initdata.py` failed on import (`No module named 'app.core.security'`); GREEN after `core/security.py` + `services/telegram_auth.py` landed (10 unit tests pass).
2. **Task 2: auth endpoint + user upsert + /api/me Bearer dep + admin allowlist probe** (TDD) — `4a15ce6` (feat). Schemas + thin routers + `get_current_user`/`require_admin` + main.py wiring + transaction-isolated integration tests.
3. **Task 3: INFRA-05 soft-error handler + no-op Sentry seam + structured logging** — `86ccc06` (feat).

**Plan metadata:** committed separately (docs: complete plan) with this SUMMARY + STATE/ROADMAP/REQUIREMENTS updates.

## Files Created/Modified

**Core / security**
- `backend/app/core/security.py` — `encode_jwt`/`decode_jwt` (HS256 pinned, exp verified, alg:none rejected)
- `backend/app/core/errors.py` — `unhandled_exception_handler` (soft RU JSON, server-side `logger.exception`)
- `backend/app/core/sentry.py` — `init_sentry()` no-op-without-DSN, guarded import
- `backend/app/core/config.py` — added optional `SENTRY_DSN`

**Service / schemas / routers**
- `backend/app/services/__init__.py` + `telegram_auth.py` — `validate_init_data` + `parse_user` (pure) + `authenticate` + `_ensure_user_limits` + `get_user_limits` (DB)
- `backend/app/schemas/__init__.py` + `auth.py` — `AuthRequest`/`UserOut`/`LimitsOut`/`SettingsOut`/`AuthResponse`/`MeResponse` (Pydantic v2, `from_attributes=True`)
- `backend/app/api/auth.py` — `POST /api/auth/telegram` (thin; ValueError → generic 401)
- `backend/app/api/users.py` — `GET /api/me` (Bearer)
- `backend/app/api/admin.py` — `GET /api/admin/ping` (require_admin)
- `backend/app/api/deps.py` — `get_current_user` + `require_admin`
- `backend/app/main.py` — wired auth/users/admin routers under `/api`, registered the Exception handler, `init_sentry()` on startup

**Tests**
- `backend/tests/unit/test_initdata.py` — 10 tests: forged/tampered/stale/missing-hash/wrong-token + JWT round-trip/expired/alg:none/wrong-secret (skip removed)
- `backend/tests/integration/conftest.py` — transaction-isolated `auth_session` + `auth_client` (get_session override)
- `backend/tests/integration/test_auth_flow.py` — valid→200+JWT+upsert, repeat→last_seen no-dup, forged/stale→401 (skip removed)
- `backend/tests/integration/test_me.py` — bearer accept/missing/invalid/expired (skip removed)
- `backend/tests/integration/test_admin_guard.py` — 403 non-admin, 200 admin, no-token rejected (skip removed)
- `backend/tests/integration/test_error_shape.py` — forced RuntimeError → 500 soft JSON, no leak (skip removed)

## Decisions Made

- **Pure validator + separate `authenticate()`** — the crypto gate has no DB dependency so the four mandated failure modes (forged/tampered/stale/missing) are fast unit tests; the Postgres upsert lives in `authenticate()` in the same module (the `TelegramAuthService` the bot reuses in Phase 7).
- **JWT `sub` = user UUID (str), `telegram_id` convenience claim** — matches RESEARCH Pattern 5; `get_current_user` resolves the user by `sub`; expired/invalid → 401, unknown sub → 401.
- **`user_limits` ensured via insert-if-absent (not a second upsert)** so a repeat login never creates a duplicate limits row; `week_start` = Monday of the current UTC ISO week.
- **Single generic 401 (`"authentication failed"`)** for every initData failure cause — no oracle that reveals which check failed (T-04-07); the real reason is logged server-side.
- **Soft-error handler scoped to bare `Exception` only** — FastAPI's HTTPException/validation handlers stay intact so 401/403/422 keep semantics; confirmed the error path does not perturb the auth tests.
- **Sentry is a minimal no-op seam** (no DSN → returns False, missing sdk → returns False, never raises); full observability deferred to Phase 8 per RESEARCH Open Question #4 — deliberately did not over-build.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Coverage] Added wrong-bot-token + JWT wrong-secret unit tests beyond the four mandated**
- **Found during:** Task 1
- **Issue:** The plan mandates forged/tampered/stale/missing-hash + a JWT round-trip + alg:none test. A signature made with a *different* bot token (the real-world "wrong app" case) and a JWT signed with a *different* secret were not explicitly covered, though both are core to the HMAC/JWT trust model.
- **Fix:** Added `test_wrong_bot_token_rejected` and `test_jwt_wrong_secret_rejected` (10 unit tests total).
- **Files modified:** backend/tests/unit/test_initdata.py
- **Verification:** `pytest -q tests/unit/test_initdata.py` → 10 passed.
- **Committed in:** `1c75cfb` (Task 1).

**2. [Rule 2 - Coverage] Added integration conftest + extra rejection/auth tests**
- **Found during:** Task 2
- **Issue:** The service calls `session.commit()`, so a plain rollback fixture would not isolate tests; and the plan's integration set did not include a forged→401-through-HTTP, a stale→401-through-HTTP, an admin-no-token, or a `/api/me` expired-bearer case (all part of the boundary contract).
- **Fix:** Added `tests/integration/conftest.py` with a transaction-isolated `auth_session` (`AsyncSession(join_transaction_mode="create_savepoint")` on a dedicated connection, rolled back at teardown) + an `auth_client` overriding `get_session`; added `test_forged_hash_returns_401`, `test_stale_auth_date_returns_401`, `test_me_rejects_invalid_bearer`, `test_me_rejects_expired_bearer`, `test_admin_requires_auth`.
- **Files modified:** backend/tests/integration/conftest.py (new), test_auth_flow.py, test_me.py, test_admin_guard.py
- **Verification:** All collect cleanly (22 auth nodes); skip cleanly when Postgres is down; security-critical 401/403 paths additionally proven live via a throwaway DB-free probe (removed after).
- **Committed in:** `4a15ce6` (Task 2).

**3. [Rule 1 - Lint] Import-sort auto-fix on the new unit test**
- **Found during:** Task 1
- **Issue:** `ruff check` flagged I001 (import order) in `test_initdata.py`.
- **Fix:** `ruff check --fix` reordered imports.
- **Files modified:** backend/tests/unit/test_initdata.py
- **Verification:** `ruff check app tests` → all checks passed.
- **Committed in:** `1c75cfb` (Task 1).

---

**Total deviations:** 3 (2 coverage, 1 lint). All additive hardening of the security spine or ruff-cleanliness; no scope creep and no contract change — the response shapes, route paths, status codes, and threat-model mitigations match the plan exactly.

**Impact on plan:** None negative. Every `<threat_model>` mitigation (T-04-01..09) is implemented and, where DB-free, asserted live; the DB-touching upsert assertions are written and run when Postgres is available.

## Threat Model Coverage

| Threat ID | Mitigation in this plan | Verified |
|-----------|-------------------------|----------|
| T-04-01 Spoofed telegram_id | `authenticate` derives `telegram_id = int(tg["id"])` only from the validated `user`; router never reads an id from the body (grep-confirmed) | unit + (DB) integration |
| T-04-02 Replay of leaked initData | `auth_date` freshness vs `INITDATA_MAX_AGE_SECONDS`; stale → ValueError → 401 | unit + live HTTP |
| T-04-03 Forged JWT / alg:none | `decode_jwt` pins `algorithms=["HS256"]`; alg:none + wrong-secret rejected | unit |
| T-04-04 Non-admin → admin | `require_admin` server-side allowlist; 403 deny-by-default; `/api/admin/ping` 403/200 | (DB) integration |
| T-04-05 Timing attack on compare | `hmac.compare_digest` (constant-time) | code + unit |
| T-04-06 Stacktrace leak | global Exception handler → soft JSON; detail logged server-side; no traceback/class/path/secret in body | live integration |
| T-04-07 Auth-error oracle | single generic 401 message for all failure causes | live HTTP |
| T-04-08 Secret leakage | secrets only from settings/env; never logged or in bodies; response schemas expose no secret columns | code review |
| T-04-09 SQLi in upsert | parameterized `insert(...).on_conflict_do_update` — no string-built SQL | code review |

## Issues Encountered

- **No live database/Docker in this environment** — `docker version` hangs (daemon not running, same as Plans 01-02), so the 11 DB-backed auth integration tests (`test_auth_flow`, `test_me`, `test_admin_guard`) **skip cleanly** here rather than running. To compensate, the security-critical rejection paths (forged-hash 401, stale 401, missing-initData 422, invalid-Bearer 401, missing-Bearer, admin-no-token) were proven **live** end-to-end through the real ASGI app with a throwaway DB-free probe (since those paths raise before any DB access), and the INFRA-05 soft-error path passes live (no DB needed). The upsert/last_seen/admin-200 assertions run when Postgres is up (user smoke below).
- **Backslash paths in the Bash tool** — Windows tree, POSIX shell; used `/c/zerkalo-sudby/...` and the repo's `.venv/Scripts/*.exe` interpreters.
- **`InsecureKeyLengthWarning`** appears once — only from `test_jwt_wrong_secret_rejected`, which intentionally signs with a short throwaway secret to prove rejection; production `JWT_SECRET` is operator-provided.

## User Setup Required

To turn the DB-gated skips into live confirmation (run once locally with Docker Desktop running and a real `.env`):

1. **Start the stack + migrate:** `docker compose up -d && cd backend && alembic upgrade head`.
2. **Run the auth suite live:**
   ```
   cd backend && pytest -q tests/unit/test_initdata.py tests/integration/test_auth_flow.py tests/integration/test_me.py tests/integration/test_admin_guard.py tests/integration/test_error_shape.py
   ```
   Expect all green (the 11 currently-skipped integration tests now run): valid initData → 200 + JWT + a single upserted user + a `user_limits` row; repeat → `last_seen_at` advanced, no duplicate; `/api/me` accept/reject; `/api/admin/ping` 403/200.
3. **(Optional) real-Telegram smoke** is Plan 01-05's checkpoint (Mini App → `POST /api/auth/telegram` → authenticated state).

## Next Phase Readiness

- **Plan 01-05 (frontend auth wiring):** the `POST /api/auth/telegram` contract (`{init_data}` → `{access_token, user, limits, settings}`) and `GET /api/me` are live; the frontend can store the JWT and gate the authenticated state, then the real-Telegram verify checkpoint closes Phase 1.
- **Phase 2+ (catalog/readings/payments/admin):** `get_current_user` is the reusable Bearer gate for every protected route; `require_admin` + the allowlist is the admin seam (real admin bodies in Phase 8); `authenticate()` is the `TelegramAuthService` the aiogram bot reuses in Phase 7 (no HTTP).
- **No blockers.** `ruff check app` is clean; the unit + error-shape suite is green; the DB-backed auth assertions run on `docker compose up` (the only outstanding item is the user smoke above).

## Self-Check: PASSED

- All 11 created files + 8 modified files verified present on disk.
- All three task commit hashes verified in git history: `1c75cfb` (HMAC+JWT), `4a15ce6` (endpoint+deps+upsert), `86ccc06` (INFRA-05).
- `pytest -q tests/unit` → 22 passed; `pytest -q` (full) → 23 passed, 15 skipped (DB-gated), 0 failures; `ruff check app` → 0.
- Security-critical 401/403/500 paths proven live through the ASGI app (forged/stale/invalid-bearer/admin-no-token/soft-error); DB-upsert paths run under live Postgres.

---
*Phase: 01-foundation-telegram-auth*
*Completed: 2026-06-10*
