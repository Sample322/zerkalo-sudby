---
phase: 5
slug: history-profile
status: verified
threats_open: 0
asvs_level: 2
created: 2026-07-05
---

# Phase 5 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verify-only run: the register was authored at plan time (all 7 `05-0N-PLAN.md` carry a
> `<threat_model>` block). Each threat below was verified against the IMPLEMENTATION — a mitigation
> is CLOSED only where the actual control was found in code (file + mechanism cited), never on the
> strength of documentation or intent. Headline risk: **IDOR = HIGH** (history read/detail/delete/
> restore + settings write).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Mini App → API (client → API) | The Bearer JWT is the ONLY identity on every history/profile call; `limit`/`offset` are untrusted query params validated by FastAPI; `{reading_id}` is a UUID path (422 on malformed); no request body carries identity. | JWT (session token), reading UUIDs, settings booleans |
| API → DB | All reads/writes are `select()`/`update()`-parameterized + user-scoped (`Reading.user_id == user.id`); soft delete is a timestamp write, never a hard delete. | Owned readings, user_limits, settings flags |
| prompt assembly → LLM | The §18 prompt is the privacy boundary for HIST-05/D-06: history must never cross it. Today it never crosses at all — `PromptEngine.build` has no history parameter. | (nothing — closed by absence) |
| user copy → UI | New history/profile/settings strings pass the SAFE-06 `BANNED_BRAND_TOKENS` scan (brand-voice boundary). | Static copy strings |
| optimistic cache → server | The 5s undo window is a pure client timer; the server is authoritative for ownership + soft-delete state (optimistic cache is UI-only). | Cached list snapshot |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-IDOR | Information Disclosure / Elevation | cross-user `GET`/`DELETE /api/readings/{id}` | mitigate | Executable lock `test_cross_user_detail_and_delete_404` (Plan 01) + the service-level scope it verifies (see IDOR-GET/DEL). Non-owned id → 404 on both verbs. | closed |
| T-05-IDOR-GET | Information Disclosure / Elevation | `GET /api/readings/{id}` | mitigate | `reading.py:494-504` `get_reading_detail` — `select(Reading).where(id, user_id == user.id, deleted_at.is_(None))`; `None → ReadingInputError`. Router `readings.py:114-117` maps → **404 (not 403)**, no existence leak. | closed |
| T-05-IDOR-DEL | Tampering | `DELETE` + `POST /{id}/restore` | mitigate | `reading.py:564-576` `soft_delete` and `578-598` `restore` — both `.where(id, user_id == user.id)`; non-owned/already-deleted → `ReadingInputError` → **404** (`readings.py:135-136,155-156`). One user cannot delete/restore/probe another's row. | closed |
| T-05-IDOR-UI | Information Disclosure / Elevation | reopen/delete another user's id (FE) | mitigate | `ResultScreen.tsx:66-72` sources the detail id ONLY from `detailReadingId`, set from the user's own server-scoped list (`HistoryScreen.tsx:60-63`). `api/readings.ts:62-88` sends no client user_id; the server re-checks ownership and 404s (T-05-IDOR-GET/DEL). UI cannot reach another user's reading. | closed |
| T-05-01 | Information Disclosure / Elevation | `GET /api/readings` list scoping | mitigate | `reading.py:411-415` `list_readings` filters `Reading.user_id == user.id`; user comes from `get_current_user` (`readings.py:78`), never a body/query user_id. | closed |
| T-05-02 | Information Disclosure | soft-delete leak in list | mitigate | `reading.py:413` `Reading.deleted_at.is_(None)` on the list query; deleted rows never appear. | closed |
| T-05-03 | Information Disclosure | over-reading internals in list | mitigate | `schemas/reading.py:302-336` `ReadingListItemOut` exposes only the 7 §9.6 fields; omits `generation_error`/`prompt_version`/`model_name` and per-card `interpretation`. Built explicitly at `reading.py:434-445` (no ORM passthrough of internal columns). | closed |
| T-05-05 | Tampering | unbounded paging past the free cap | mitigate | `reading.py:401-403` `eff = min(limit, FREE_HISTORY_CAP - offset)`, `offset >= cap → []`; router `readings.py:76` `Query(10, ge=1, le=10)`. `FREE_HISTORY_CAP=10` (`reading.py:127`). | closed |
| T-05-LEAK | Information Disclosure | detail over-exposure | mitigate | `get_reading_detail` reuses `_build_response` (`reading.py:1343-1378`) → `ReadingOut`, which carries no `generation_error`/`prompt_version`/`model_name`/debug column. No internal field added. | closed |
| T-05-SOFTDEL | Information Disclosure | deleted reading reappearing | mitigate | `reading.py:499` `deleted_at.is_(None)` on detail; `restore` (`578-598`) is the only path nulling `deleted_at`; `soft_delete` sets a timestamp, never a hard delete (D-04 retain-data). | closed |
| T-05-SPOOF | Spoofing / Elevation | `PATCH /api/me/settings` body | mitigate | `schemas/auth.py:83-103` `SettingsPatch` has NO `user_id` field; handler `users.py:52-53` mutates `current_user` (JWT `sub`) via `model_dump(exclude_unset=True)`. A forged body user_id has no effect. | closed |
| T-05-SPOOF-UI | Spoofing | settings PATCH from the client | mitigate | `hooks/useMe.ts:40-41` + `api/me.ts:41-50` `patchSettings` sends only the changed flag(s) as body; identity rides the Bearer via `apiFetch` (`api/client.ts:26-28`). Server (T-05-SPOOF) ignores any body identity. | closed |
| T-05-VAL | Tampering | unexpected PATCH keys | mitigate | `SettingsPatch` is a closed Pydantic schema (3 optional booleans); `exclude_unset` writes only provided known keys (`users.py:52`). Unknown keys are dropped by Pydantic. | closed |
| T-05-AUTH | Spoofing | list fetch identity (FE) | mitigate | JWT attached only via `apiFetch` (`api/client.ts:19-31`); the client never sends a user_id — the server scopes by the token (`reading.py:411`). | closed |
| T-05-CONSENT | Information Disclosure / Privacy | PromptEngine + history (HIST-05/D-06) | mitigate | `prompt_engine.py:374-385` `build(...)` has NO `history`/`history_context`/`prior_readings` parameter; explicit closed-gate lock comment `358-372`; regression fence `test_prompt_has_no_history_even_with_flag_on` + `test_build_has_no_history_parameter`. `create_reading` (`reading.py:325-334`) passes no history. Consent flag defaults OFF. Gate closed BY ABSENCE. | closed |
| T-05-PRIV | Information Disclosure / Privacy | personalization consent copy | mitigate | `copy.ts:169-170` `SETTINGS_PERSONALIZATION_EXPLAINER` describes «история раскладов»/«колода помнит» + privacy note («История остаётся только твоей и никуда не передаётся»), never the mechanism. Toggle defaults OFF (server, D-05); gate stays closed (T-05-CONSENT). | closed |
| T-05-XSS | Tampering / Information Disclosure | history list + detail rendering | mitigate | No `dangerouslySetInnerHTML`/`.innerHTML` anywhere in `frontend/src` (grep: 0 sinks in source). Question/summary/detail render as React text nodes (`HistoryScreen.tsx:173,201`; `ResultScreen.tsx:29` control comment covers detail mode `isDetail` at `199`). | closed |
| T-05-BRAND | Information Disclosure (brand) | new history/profile copy | mitigate | `copy.ts:17-18` `BANNED_BRAND_TOKENS` (`ai|нейросет|модель|сгенерирован|ИИ`); `copy.test.ts:47-62` module-wide scan over EVERY exported string asserts zero banned tokens. | closed |
| T-05-STALE | Tampering | optimistic cache mismatch | mitigate | `hooks/useReadings.ts:13,72-88,98-112` delete/restore mutations target the single stable key `["readings","list"]`; `onError` rolls back to the snapshot; the server already soft-deleted so cache and server agree. | closed |
| T-05-D08 | Information Disclosure | premature readings-count exposure | mitigate | Verified CLOSED at Phase-5 delivery: the count/subscription block was deliberately omitted and `ProfileScreen.test.tsx` asserted the count absent (05-07-SUMMARY §Accomplishments/Decisions). The block now visible in `ProfileScreen.tsx:194-212` was INTENTIONALLY un-hidden by the authorized **Phase-6 D-09** decision (06-04-PLAN Task 3 inverts the absence test; introduced commit `8eee1e4`, 2026-06-22 — after Phase-5 close 2026-06-15). Exposure is no longer premature; out-of-scope later-phase evolution. | closed |
| T-05-SC | Tampering | npm/pip/cargo installs | accept | Phase 5 installs ZERO new packages (RESEARCH Package Legitimacy Audit; SUMMARY tech-stack `added: []` on every plan; no toast/router lib — grep of `frontend/package.json` finds no toast dependency; snackbar is `motion` + `setTimeout`). See Accepted Risks Log. | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-SC | T-05-SC | Supply-chain tampering of new dependency installs is not applicable to Phase 5: the phase installs zero new packages (RESEARCH "Phase 5 installs ZERO new packages"; every `05-0N-SUMMARY.md` records `tech-stack.added: []`). The history/profile UI reuses already-pinned deps (`motion`, TanStack Query, Zustand) and the step-machine; the undo snackbar is `motion` `AnimatePresence` + `setTimeout` (no toast/router library added — verified against `frontend/package.json`). No new package-legitimacy checkpoint is required. | ivan.galkin13@gmail.com (project owner) | 2026-07-05 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-07-05 | 20 | 20 | 0 | gsd-security-auditor (verify-only) |

Notes:
- Verify-only mode — register authored at plan time across the seven `05-0N-PLAN.md` `<threat_model>` blocks; no new-threat scan performed.
- SUMMARY `## Threat Flags`: only `05-04-SUMMARY.md` carries the section, reporting "None — no new security surface beyond the planned threat_model." No `unregistered_flag` recorded.
- Implementation files were treated READ-ONLY; only this `05-SECURITY.md` was written.
- IDOR (HIGH) scrutinized hardest: JWT identity via `get_current_user` on every route; every detail/delete/restore/list query carries `Reading.user_id == user.id`; cross-user → 404 (not 403 — no existence leak); no route reads a body/path-supplied user_id; `{reading_id}` typed `uuid.UUID` (422 on malformed); `SettingsPatch` has no `user_id`.
- T-05-D08 note: mitigated as-shipped in Phase 5; the count block is now visible only because Phase 6 (D-09) deliberately lifted the hide — a planned cross-phase evolution flagged out-of-scope by this audit, not a Phase-5 regression.

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-07-05
