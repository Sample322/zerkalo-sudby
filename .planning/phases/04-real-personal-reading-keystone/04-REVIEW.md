---
phase: 04-real-personal-reading-keystone
reviewed: 2026-07-05T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - backend/app/services/reading.py
  - backend/app/services/safety.py
  - backend/app/services/llm.py
  - backend/app/services/card_draw.py
  - backend/app/services/prompt_engine.py
  - backend/app/services/answer_style.py
  - backend/app/services/telegram_auth.py
  - backend/app/core/brand_guard.py
  - backend/app/core/llm_client.py
  - backend/app/core/openrouter_adapter.py
  - backend/app/core/security.py
  - backend/app/api/auth.py
  - backend/app/api/readings.py
  - backend/app/api/deps.py
  - backend/app/schemas/reading.py
findings:
  critical: 1
  warning: 7
  info: 6
  total: 14
status: resolved_partial
resolution:
  fixed: [CR-01, WR-01, WR-02, WR-06, WR-07]
  covered_by_dependency: [WR-03, WR-04]  # get_session async-with rollback + CR-01 refactor
  deferred: [WR-05, IN-01, IN-02, IN-03, IN-04, IN-05, IN-06]  # documented-defensive / tradeoffs
  resolved_date: 2026-07-05
  commit: c573006
---

# Phase 4: Code Review Report

**Reviewed:** 2026-07-05
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Reviewed the Phase-4 keystone reading engine: safety gate, CSPRNG draw, prompt assembly, single-call LLM wrapper (tenacity retry + OpenRouter adapter), brand-guard, persistence, and the honest-fail / limit-refund paths. The code is careful, well-documented, and the locked ordering invariants (safety-before-draw, atomic consume-gate, refund-on-honest-fail) are correctly implemented. Security mitigations were audited separately (04-SECURITY.md) and were not re-litigated.

Per the review's adversarial mandate, findings concentrate on the correctness dimension the security pass did not cover: async/transaction/session handling, the LLM retry/timeout contract, the OpenRouter adapter's fidelity to the `messages.parse` surface, honest-fail integrity, and tz-aware/naive datetime handling.

The one BLOCKER is a real transaction-integrity defect on the crisis/abusive short-circuit path: it commits inside a method invoked from a broader flow, but that flow's outer session is shared — the more precise defect is a **`session.refresh(limits)` on a detached/expired object after a commit in `_honest_fail` producing a stale `remaining`, combined with the short-circuit `_short_circuit` committing a partially-built parent row while a prior `session.flush()` for other work could already be pending**. The concrete, demonstrable defect is the OpenRouter adapter silently dropping the retry contract's timeout guarantee (WARNING) and the `stop_reason` fallback masking a truncated/empty parse — see below. The single Critical is the honest-fail `remaining` value being computed from a **stale, non-refunded counter for the subscription/paid buckets**, returning a wrong quota number to the client after a paid failure.

## Critical Issues

### CR-01: Honest-fail returns a stale/wrong `remaining_limits` for subscription and paid buckets

**File:** `backend/app/services/reading.py:1284-1296`
**Issue:**
On honest-fail, the refund is correctly routed to the actually-consumed bucket via `_refund_consumed_bucket` (free / subscription / paid). But the value surfaced back to the client is always computed from the **free** counter:

```python
if refund and limits is not None:
    await self._refund_consumed_bucket(session, user.id, consumed_bucket)
    await session.refresh(limits)
await session.commit()
...
return self._soft_body(
    reading_id=str(reading.id),
    message=SOFT_FAILURE_COPY,
    remaining=self._remaining(limits) if refund else None,   # <-- always FREE remaining
)
```

`_remaining()` only reads `free_weekly_limit - free_used_this_week` (line 636-640). When a reading was paid for from the **PAID** bucket (`consumed_bucket == Bucket.PAID`) and honest-fails, the refund correctly restores `paid_spreads_balance += 1`, but the response reports the user's *free* remaining count (e.g. `0` if the weekly free quota is already spent) instead of the restored paid balance. The success path for a PAID consume returns `new_balance` as `remaining_limits` (line 834 → 372), so the same reading that succeeds vs. honest-fails returns a *different kind* of number for `remaining_limits`. A client that renders "N осталось" from `remaining_limits` will show `0` (or a stale free count) after a paid reading fails, even though the paid spread was refunded and is spendable — a user-visible correctness defect on the paid tier (the exact tier where money changed hands).

Additionally, `session.refresh(limits)` re-reads the ORM object, but `limits` was loaded at the top of `create_reading` (line 258) and the atomic consume + refund were executed as **raw `UPDATE` statements** that bypass the ORM identity map. `refresh` issues a fresh SELECT so it does pick up the committed-in-transaction values for FREE, but this is load-bearing and undocumented at the call site: if the refund path is ever reordered after `commit()`, `refresh` on an expired instance would emit a SELECT outside the just-committed transaction (or raise). The correctness currently holds only for FREE by luck of `_remaining` reading the one bucket that `refresh` reloads.

**Fix:**
Thread the refunded bucket's remaining value through honest-fail the same way the success path threads the gate's `remaining`, instead of recomputing from the free counter. Minimal version:

```python
async def _honest_fail(self, session, reading, user, limits, exc, *,
                       refund=True, consumed_bucket=None, remaining_after_refund=None):
    reading.status = ReadingStatus.FAILED
    reading.generation_error = self._truncate_error(exc)
    session.add(GenerationLog(...))
    remaining = None
    if refund and limits is not None:
        await self._refund_consumed_bucket(session, user.id, consumed_bucket)
        await session.refresh(limits)
        remaining = self._remaining_for_bucket(limits, consumed_bucket)
    await session.commit()
    logger.warning("reading_honest_fail", extra={...})
    return self._soft_body(reading_id=str(reading.id), message=SOFT_FAILURE_COPY, remaining=remaining)
```

where `_remaining_for_bucket` returns `paid_spreads_balance` for PAID, `None` for SUBSCRIPTION (matching the success path), and the free count for FREE — so the same field means the same thing on both the success and honest-fail exits for a given bucket.

## Warnings

### WR-01: OpenRouter adapter forwards `timeout` to `beta.chat.completions.parse` but does not guarantee a `TimeoutError` the retry contract expects

**File:** `backend/app/core/openrouter_adapter.py:75-82`
**Issue:**
`LLMService.RETRYABLE` (llm.py:82-93) lists `openai.APITimeoutError` and `TimeoutError` so a per-attempt deadline triggers the corrective retry then honest-fail. The adapter passes `timeout=timeout` straight into `self._client.beta.chat.completions.parse(...)`. The OpenAI SDK accepts a per-request `timeout` and raises `openai.APITimeoutError` on expiry — which IS in `RETRYABLE`, so this path is mostly fine. However, the Anthropic-native path (`llm.py:_attempt`) relies on the SDK raising on the deadline too, but there is **no `asyncio.wait_for` wrapper** anywhere: both providers are trusted to honor the `timeout` kwarg. If a provider (or a mock, or a future gateway) ignores or silently caps `timeout`, the "per-attempt wall clock" guarantee (`ATTEMPT_TIMEOUT_SECONDS = 20.0`) is not enforced by the service — a hung connection blocks the FastAPI request indefinitely. The module docstrings assert a per-attempt timeout as a hard contract; it is actually delegated entirely to the SDK kwarg with no service-level backstop.

**Fix:**
Either document explicitly that timeout enforcement is delegated to the SDK (and that both `openai` and `anthropic` honor it), or wrap the single attempt in `asyncio.wait_for(self._attempt(...), timeout=ATTEMPT_TIMEOUT_SECONDS)` so a provider that ignores the kwarg still surfaces `TimeoutError` (already retryable). The wrapper is the robust choice given the swappable-provider design.

### WR-02: `_ParsedResponse.parsed_output` can be `None` on a non-refusal empty parse, bypassing the retry trigger

**File:** `backend/app/core/openrouter_adapter.py:83-101`; `backend/app/services/llm.py:150-154`
**Issue:**
The adapter maps `parsed_output = message.parsed`. `message.parsed` is `None` when the model returns content the SDK could not coerce to the schema *without* setting `message.refusal` (e.g. a malformed structured response, or `finish_reason="stop"` with unparseable content). In that case:
- `stop_reason` is computed from `finish_reason` → `"end_turn"` (not in `_NON_SCHEMA_STOP_REASONS`), so the Pitfall-2 retry does **not** fire.
- Back in `LLMService._attempt`, `output: ReadingOutput = response.parsed_output` assigns `None`. There is no `isinstance`/`None` check; `stop_reason` is `end_turn`, so it skips the retry and returns a `GenerationResult(output=None, ...)`.
- `ReadingService._unpack_generation` (reading.py:1132-1136) checks `isinstance(result, ReadingOutput)` on the *GenerationResult*, not on `.output`; since a real result is a `GenerationResult`, it falls to `getattr(result, "output", None)` → `None`, and the `if not isinstance(output, ReadingOutput)` guard raises `TypeError`.
- `TypeError` is **not** in `RETRYABLE`, so it propagates out of `LLMService.generate` unchanged and out of `create_reading` — hitting the global 500 handler instead of the honest-fail soft body. That is the exact "never a raw 500 on generation" invariant the phase is built to avoid (reading.py module docstring, D-09).

The Anthropic-native path is protected because `response.parsed_output` there raises `ValidationError` on a bad shape (retryable). The OpenRouter adapter breaks that assumption by returning `None` instead of raising, so a schema-empty-but-not-refusal completion escapes the retry/honest-fail machinery and 500s.

**Fix:**
In the adapter, treat a `None` `message.parsed` without a refusal as a non-schema outcome — raise the same signal the caller retries on, or set `stop_reason="refusal"`:

```python
parsed = message.parsed
if getattr(message, "refusal", None) or parsed is None:
    stop_reason = "refusal"   # force the corrective retry / honest-fail
else:
    stop_reason = _FINISH_TO_STOP.get(choice.finish_reason or "stop", "end_turn")
```

Alternatively, guard `LLMService._attempt` so a `None`/non-`ReadingOutput` `parsed_output` raises a `RETRYABLE` error rather than a bare `TypeError`.

### WR-03: `_short_circuit` and other exits `commit()` a session owned by the request-scoped dependency, but a mid-flow failure leaves no rollback path

**File:** `backend/app/services/reading.py:1241`, `371`, `576`, `598`, `1287`
**Issue:**
`create_reading`, `_short_circuit`, `_honest_fail`, `soft_delete`, and `restore` each call `await session.commit()` directly on the injected `AsyncSession`. The session comes from `get_session` (deps.py → `core.db.get_session`). If any statement *after* a partial `flush()` but *before* the `commit()` raises a non-`ReadingInputError`, non-`LLMGenerationError` exception (e.g. the `TypeError` from WR-02, or a DB error on the classify-log insert), the half-built transaction is left open and unrolled at the point of raise. Whether it is cleaned up depends entirely on `get_session`'s `finally: rollback/close` — which is not in scope here but is the only thing preventing a leaked/aborted transaction from poisoning connection reuse. The service commits eagerly at multiple points and assumes the dependency's teardown always rolls back on exception; there is no `try/except: await session.rollback(); raise` around the multi-step mutation in `create_reading`. This is a robustness gap, not a proven leak, because the reviewed `get_session` was out of scope — but the service should not depend on unseen teardown semantics for transactional correctness across five commit sites.

**Fix:**
Confirm `core.db.get_session` wraps the yield in `try/.../finally` with a `rollback()` on exception (if it does, downgrade this to Info and add a comment at the commit sites noting the dependency guarantees rollback). If it does not, wrap the mutating body of `create_reading` so any escape rolls back the partial transaction before re-raising.

### WR-04: `session.refresh(limits)` before `commit()` in honest-fail relies on transaction-visible reads of raw-UPDATE'd rows

**File:** `backend/app/services/reading.py:1284-1287`
**Issue:**
`limits` is the ORM instance loaded at reading.py:258. The consume-gate and refund mutate the row with Core `update()` statements, not through this instance. `await session.refresh(limits)` issues a `SELECT ... WHERE id = :pk` inside the still-open transaction, which correctly sees the uncommitted refund — so FREE `remaining` is right today. But this couples correctness to (a) the refresh running *before* commit, and (b) `_remaining` happening to read only the FREE columns that were refunded. It is fragile: any change that moves the refresh after `commit()`, or that surfaces a non-free bucket count (see CR-01), silently returns stale data. There is no assertion or comment binding the refresh-before-commit ordering.

**Fix:**
Prefer returning the post-refund remaining directly from the refund helper (as in the CR-01 fix) instead of round-tripping through `refresh` + a bucket-blind `_remaining`. If keeping `refresh`, add a comment that it MUST precede `commit()` and reads the in-transaction refunded state.

### WR-05: `_regex_prefilter` sends the crisis-classified question no further, but Stage-2 classify passes the raw untrimmed question to the model

**File:** `backend/app/services/safety.py:186-191`
**Issue:**
Stage-1 (`_regex_prefilter`) trims and null-checks the question. When it returns `None` (undecided), `classify` proceeds to Stage-2 and sends `messages=[{"role": "user", "content": question or ""}]` — the **original untrimmed** `question`. That is functionally fine for classification, but note the `question or ""` is dead-defensive: `_regex_prefilter` already returned `NORMAL` for any falsy/whitespace question, so at line 187 `question` is guaranteed truthy and non-blank. The `or ""` can never trigger. Minor, but it signals the invariant (question non-empty here) is not asserted, and a future refactor of `_regex_prefilter` that stops short-circuiting empties would silently send an empty user turn to the classifier. Not a runtime bug today.

**Fix:**
Drop the `or ""` (the value is guaranteed non-empty by the prefilter contract) or add an `assert question and question.strip()` at the top of Stage-2 to lock the invariant the prefilter guarantees.

### WR-06: `list_readings` default `limit=10` in the service vs. router `Query(10, le=10)` — the cap is enforced in two places with a silent coupling to `FREE_HISTORY_CAP`

**File:** `backend/app/services/reading.py:381,400-402`; `backend/app/api/readings.py:76`
**Issue:**
`list_readings(limit=10)` and the route's `Query(10, ge=1, le=10)` both hardcode `10`, and the service separately clamps with `eff = min(limit, FREE_HISTORY_CAP - offset)` where `FREE_HISTORY_CAP = 10`. Three independent `10`s must stay in sync. If `FREE_HISTORY_CAP` is ever raised (the docstring explicitly anticipates Phase-6/7 swapping it for a tier-derived limit), the router's `le=10` and the service default silently continue to cap at 10, defeating the config change. The magic number is duplicated across the boundary instead of the router deriving its bound from `FREE_HISTORY_CAP`.

**Fix:**
Have the router import and reference `FREE_HISTORY_CAP` for the `le=` bound (and the service default), so the single constant governs the cap end-to-end:

```python
from app.services.reading import FREE_HISTORY_CAP
limit: int = Query(FREE_HISTORY_CAP, ge=1, le=FREE_HISTORY_CAP),
```

### WR-07: `get_current_user` uses `session.get(User, payload["sub"])` with an unvalidated string PK — a malformed `sub` may raise instead of 401

**File:** `backend/app/api/deps.py:49-52`
**Issue:**
`decode_jwt` verifies signature + `exp` but does not constrain the *shape* of `sub`. `session.get(User, payload["sub"])` passes the raw `sub` string as the UUID primary key. For a token this backend issued, `sub` is `str(user.id)` (a valid UUID string) and asyncpg/SQLAlchemy coerces it fine. But a signed token whose `sub` is a non-UUID string (e.g. issued by a future code path, or a test token, or a tampered-then-resigned token if the secret ever leaks) makes `session.get` attempt a UUID cast that raises `DBAPIError`/`ValueError` rather than returning `None` → the handler does not map it to 401 and it escapes as a 500. `payload["sub"]` also uses direct key indexing; a token missing `sub` entirely (valid signature, malformed claims) raises `KeyError` → 500, not 401.

**Fix:**
Fetch and validate `sub` defensively:

```python
sub = payload.get("sub")
if not sub:
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")
try:
    user = await session.get(User, uuid.UUID(sub))
except (ValueError, TypeError):
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token") from None
```

so a malformed/absent `sub` is a clean 401, consistent with the module's stated "any expired/invalid/unknown token yields 401" contract.

## Info

### IN-01: `LLMService.generate` has provably-unreachable code with an `AssertionError` sentinel

**File:** `backend/app/services/llm.py:195-196`
**Issue:**
`raise AssertionError("unreachable")` after the `async for` loop. With `reraise=True`, `AsyncRetrying` always returns from inside `with attempt:` or re-raises, so the line is dead. It is marked `# pragma: no cover` and is a defensible defensive sentinel, but it is dead code by construction.

**Fix:**
Acceptable as-is (defensive). Optionally replace with a comment-only note, or keep — no action required.

### IN-02: `_consume_subscription_atomic` / `_consume_paid_atomic` accept an unused `now` parameter

**File:** `backend/app/services/reading.py:705-707,745-747`
**Issue:**
Both take `now: datetime` but never reference it (subscription is window-gated elsewhere; paid is balance-only). The parameter exists for signature symmetry with `_consume_free_atomic`, but it is dead in these two.

**Fix:**
Drop the unused `now` params (or prefix `_now`) to signal they are intentionally unused; the callers in `_consume_free_gate` pass `now` positionally so update the call sites accordingly.

### IN-03: OpenRouter adapter ignores the incoming model alias, so the Haiku→Sonnet corrective escalation is a no-op

**File:** `backend/app/core/openrouter_adapter.py:59-82`
**Issue:**
`_Messages.parse` accepts `model` (the Anthropic alias `LLMService` passes per attempt) but always uses `self._model`. This is documented (module docstring, line 14-16) and intentional for the cheap test deploy — the D-12 "escalate to Sonnet on retry" behavior silently degrades to "retry on the same model" under OpenRouter. Correct and documented, but worth flagging: the resilience contract's model-escalation guarantee does not hold on the OpenRouter path, so a validation failure that only Sonnet would fix cannot be recovered in that deployment.

**Fix:**
No code change required (documented tradeoff). If OpenRouter becomes a primary (non-test) rail, add a two-model map so the retry can escalate to a stronger OpenRouter model.

### IN-04: `_soft_body` sets `status=ReadingStatus.FAILED.value` for the paywall, conflating "quota block" with "generation failed"

**File:** `backend/app/services/reading.py:1327-1341`
**Issue:**
The paywall, refusal, redirect, and honest-fail bodies all return `status="failed"`. The FE discriminant is `reason` (`"paywall"` vs `None`), which works, but overloading the `failed` status for a *successful-but-quota-blocked* outcome is semantically muddy — a paywall is not a generation failure. Analytics/monitoring that count `status="failed"` readings will over-count by including quota blocks and safety refusals.

**Fix:**
Not a correctness bug given `reason` carries the true discriminant. Consider a distinct status/`reason` for the paywall so downstream metrics can separate "generation failed" from "quota exhausted" and "safety-blocked".

### IN-05: `_truncate_error` interpolates `repr(cause)` into a stored string — low risk of leaking prompt/PII fragments into `generation_error`

**File:** `backend/app/services/reading.py:1298-1303`
**Issue:**
`detail = f"{exc}: {cause!r}"` then truncated to 500 chars and stored in `readings.generation_error` (server-side only, never returned — confirmed by `_build_response`/`_soft_body` not reading it). The `cause` repr for a provider exception could embed a fragment of the request payload (some SDK errors include the request body) or the model's partial output. It never crosses the API boundary, so this is not a data-leak to clients, but it does persist potentially-sensitive fragments (the user's question) into an audit column in cleartext.

**Fix:**
Acceptable given it is server-side and truncated. If `generation_error` is ever surfaced in an admin UI, sanitize/omit the underlying-cause repr, or store only the exception type + message, not the full `repr`.

### IN-06: `_thumbnails_by_reading` groups in Python and silently returns `[]` for readings with zero drawn cards, masking a data-integrity anomaly

**File:** `backend/app/services/reading.py:447-474`
**Issue:**
A COMPLETED reading with no `reading_cards` rows (which should be impossible post-`_persist_pending`, but would occur for a corrupted row) yields `thumbnails.get(reading.id, []) → []` and renders as a history item with no miniatures rather than surfacing the anomaly. Combined with the `list_readings` filter `status == COMPLETED`, a completed-but-cardless reading is a silent inconsistency. Purely defensive observation — not reachable through the normal write path.

**Fix:**
No action required for MVP. Optionally log a warning when a COMPLETED reading returns zero thumbnails, since that indicates a broken persistence invariant.

---

_Reviewed: 2026-07-05_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
