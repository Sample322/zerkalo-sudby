# Pitfalls Research

**Domain:** Telegram Mini App для AI-раскладов таро (initData auth, Telegram Stars payments, LLM interpretation, content safety, IP-sensitive art)
**Researched:** 2026-06-09
**Confidence:** HIGH for Telegram protocol pitfalls (initData, Stars, subscriptions — verified against official `core.telegram.org` docs), MEDIUM for LLM-cost/JSON and viewport-CSS pitfalls (practitioner sources + official viewport docs), MEDIUM for IP/safety (domain reasoning grounded in TZ §5/§20)

> Phase numbers below map to TZ §23 "План разработки MVP по этапам" (Этап 1–10), the structure the roadmap will follow.
> Этап 1 Подготовка · Этап 2 Telegram auth · Этап 3 База колод/раскладов · Этап 4 UX главного сценария · Этап 5 Генерация · Этап 6 История · Этап 7 Лимиты · Этап 8 Payments (Stars) · Этап 9 Admin · Этап 10 Полировка/релиз

---

## Critical Pitfalls

### Pitfall 1: initData validation done wrong → auth bypass / spoofed telegram_id

**What goes wrong:**
The whole identity model rests on one HMAC check. The common failure modes, in order of how often they appear in real Mini Apps:
- Trusting `window.Telegram.WebApp.initDataUnsafe.user.id` on the backend (it is attacker-controlled — anyone can POST a fake `telegram_id`).
- Validating on the frontend only, or not validating at all and just parsing the `user` field.
- Wrong secret-key derivation: using the raw bot token as the HMAC key instead of `secret_key = HMAC_SHA256(key="WebAppData", message=bot_token)`. The two-stage HMAC trips people up constantly.
- Wrong data-check-string: not sorting keys alphabetically, not joining with `\n`, or forgetting to exclude the `hash` field itself before hashing.
- Skipping the `auth_date` freshness check → a leaked `initData` string is replayable forever.
- URL-decoding fields before building the check string (must hash the raw received values).

Any of these means an attacker spoofs any `telegram_id`, draining another user's paid balance, reading their history, or impersonating an admin (admin auth is an allowlist of Telegram IDs — правка #6).

**Why it happens:**
`initDataUnsafe` is right there, already parsed, and "works" in dev. The two-stage HMAC and the exact check-string format are easy to get subtly wrong, and a wrong implementation still returns a valid-looking user object in the happy path — the bug is invisible until someone attacks it.

**How to avoid:**
Implement exactly (verified against official docs):
1. `secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)`
2. `data_check_string` = all fields **except** `hash`, sorted by key, formatted `key=<value>`, joined by `\n`, using the raw received values.
3. Valid iff `hex(HMAC_SHA256(key=secret_key, msg=data_check_string)) == hash` (constant-time compare).
4. Reject if `now - auth_date > TTL` (recommend 24h; tighter for sensitive actions).
5. Backend derives `telegram_id` **only** from the validated `user` field — never from request body.
Centralize this in `TelegramAuthService`; write unit tests with a real captured `initData` (valid, tampered-hash, stale-`auth_date`, missing-`hash`). After validation, issue your own short-lived JWT/session so you are not re-parsing initData on every call.

**Warning signs:**
- Code reads `telegram_id` / `user_id` from the POST body or query, not from validated initData.
- No `hmac`/`hashlib` + `"WebAppData"` constant anywhere in the auth path.
- No test feeds a tampered `hash` and asserts rejection.
- Auth "works" but there is no `auth_date` comparison.

**Phase to address:** Этап 2 (Telegram auth). This is the security spine — it must be correct before any user data, balance, or admin route exists.

---

### Pitfall 2: Stars double-grant — missing idempotency on payment confirmation

**What goes wrong:**
Telegram **retries** the `successful_payment` webhook update if your endpoint is slow or returns non-2xx. Without idempotency, the same payment credits `paid_spreads_balance` twice (or N times), or activates a subscription repeatedly. Reverse failure: granting access on `pre_checkout_query` (which only signals intent) instead of `successful_payment` → user gets readings without paying, or a declined card still grants access.

**Why it happens:**
The naive handler is "on successful_payment → balance += amount". It looks complete and passes a single happy-path test, but never exercises a retry or a duplicate delivery.

**How to avoid:**
- `payments.payload UNIQUE` **and** index `telegram_payment_charge_id`. Insert the payment row first; catch the unique-violation (IntegrityError) and treat it as "already processed → return existing row, grant nothing more." This makes the grant idempotent at the DB level even under concurrent retries.
- Grant entitlements **only** inside the `successful_payment` handler, in the **same DB transaction** as the payment insert.
- `pre_checkout_query` validates only (product exists, active, payload unused, price matches) and answers true/false — it never grants.
- Return 200 fast; do the grant synchronously but quickly (no queue — правка #2), and make it safe to re-run.

**Warning signs:**
- No UNIQUE constraint on `payload` or `telegram_payment_charge_id`.
- Entitlement code runs in the `pre_checkout` path.
- Handler isn't wrapped in a transaction with the payment insert.
- No test simulates the same `successful_payment` delivered twice.

**Phase to address:** Этап 8 (Payments). Idempotency must ship with the very first payment write, not bolted on later.

---

### Pitfall 3: answerPreCheckoutQuery 10-second timeout → silent failed payments

**What goes wrong:**
The bot **must** call `answerPreCheckoutQuery` within **10 seconds** of receiving `pre_checkout_query`, or Telegram **cancels the transaction** (verified, official). If pre-checkout validation does a slow DB lookup, an LLM call, or any blocking work, payments randomly fail at the worst moment (user has already tapped Pay), and there is no retry.

**Why it happens:**
Pre-checkout looks like "just validate", so people put it on the same slow path as everything else, or behind cold-start/network latency, without measuring the budget.

**How to avoid:**
- Keep pre-checkout validation to fast indexed queries only (payload lookup, product active flag, price equality). No LLM, no external calls.
- Always answer — `ok=false` with a friendly `error_message` is correct for invalid payloads; never just drop the update.
- Ensure the bot webhook is warm and reachable over HTTPS with low latency (ties to Этап 10 / timeweb deploy).

**Warning signs:**
- Pre-checkout handler awaits anything heavier than a primary-key/unique lookup.
- No timing/log on pre-checkout latency.
- Users report "payment didn't go through" intermittently.

**Phase to address:** Этап 8 (Payments), with deploy-latency verification in Этап 10.

---

### Pitfall 4: Crisis questions get a mystical reading instead of a safe response

**What goes wrong:**
A user asks about self-harm, suicide, violence, abuse, or a serious medical fear, and the product returns an atmospheric tarot interpretation ("the Tower suggests painful but necessary endings…"). For crisis content this is harmful and a real liability. Equally damaging on the brand-safety axis: categorical predictions ("он тебя точно бросит"), asserting a third party's feelings as fact, or medical/legal/financial directives ("у тебя болезнь", "вложи деньги").

**Why it happens:**
The single-LLM-call design (правка #1) is optimized to *always produce a beautiful reading*. If safety is just a line in the system prompt, the model will still happily generate a mystical answer for a crisis question — prompt-only guardrails are not reliable for this. The TZ originally marked the classifier "желательно"; правка #3 correctly made it **mandatory**.

**How to avoid:**
- **Cheap regex/keyword pre-filter** (RU + EN) for hard crisis signals (самоповреждение, суицид, убить себя, насилие, "хочу умереть"…) → short-circuit **before** the creative call, return a supportive safe-response template (acknowledge + не давать предсказания + suggest a trusted person / regional helpline), and do **not** draw cards into a mystical reading. TZ §20.3/§9.8 already provide the copy.
- **Classification inside the structured call**: have the model emit `safety_category ∈ {normal, relationship_sensitive, financial_sensitive, health_sensitive, legal_sensitive, crisis_sensitive, abusive_or_manipulative}` (TZ §20.4). For `*_sensitive`, inject the `safety_modifier`; for `crisis_sensitive`, the backend overrides the rendered output with the safe template regardless of what creative text came back.
- **Defense in depth**: regex catches what the model misclassifies; the classifier catches phrasing the regex misses. Never rely on one.
- Banned-phrase post-filter on generated text (TZ §15 запрещённые формулировки) as a final net.
- Log every `*_sensitive`/`crisis` classification to `generation_logs` for manual review; ship the "Пожаловаться на ответ" button (TZ §25.4).

**Warning signs:**
- Safety lives only in the prompt; no code path can refuse/override.
- No regex pre-filter executes before the LLM call.
- A crisis test prompt returns a normal card reading.
- No structured `safety_category` field in the model's JSON.

**Phase to address:** Этап 5 (Генерация) — the classifier + safe-response path are part of the generation pipeline, not a later add-on. Refusal/safe templates seeded as `prompt_templates` (type `safety`/`refusal`) in Этап 3.

---

### Pitfall 5: LLM cost/latency blowup — per-card calls, unbounded output, no caching, no logging

**What goes wrong:**
A 4-card reading becomes 5 LLM calls (4 cards + summary), 4–5× cost and latency, plus cross-card inconsistency (summary contradicts cards). Output length is unbounded → token spend and latency creep up invisibly. Base card meanings (static, deck-agnostic) get re-generated every time instead of read from `cards`. No token logging → you discover the bill at month-end, not in the dashboard.

**Why it happens:**
"One prompt per card" is the obvious decomposition and reads cleanly. Without `generation_logs` token columns wired from day one, cost is invisible until it hurts.

**How to avoid:**
- **One structured call per reading** (правка #1, locked): all cards + summary in a single JSON response; per-card templates retained only as fallback. The card array is the cost driver, not the number of calls.
- Constrain output: low `max_tokens`, low temperature (0.0–0.3 for reliable JSON + tone consistency), per-field length caps already specified in TZ §17/§18 (`short_meaning` ≤140 chars, "2–4 коротких абзаца").
- Base meanings (`meaning_upright/reversed`, `keywords`, `advice`) live in Postgres (`cards` + `deck_cards`) and are **passed into** the prompt as context — the model personalizes, it does not re-derive. This is also the IP-correct design (Pitfall 8).
- Populate `generation_logs.input_tokens/output_tokens/latency_ms` on every call; surface `average_generation_latency` + token cost on the admin dashboard (TZ §22.2).
- Hard timeout on the call with a graceful fallback (Pitfall 6).

**Warning signs:**
- Loop issuing one completion per card.
- No `max_tokens` set; responses vary wildly in length.
- `generation_logs` token columns null/unused.
- Card base meanings reconstructed by the model instead of read from DB.

**Phase to address:** Этап 5 (Генерация). Token logging is part of the first generation implementation.

---

### Pitfall 6: No timeout / no fallback when the model returns invalid JSON

**What goes wrong:**
The model returns truncated JSON (hit token limit mid-object), adds prose around the JSON, uses `"True"` instead of `true`, an enum value outside the allowed set, or empty fields. The reading errors out *after* the user watched the shuffle ritual — the worst possible moment. Without a synchronous timeout (queue removed — правка #2), a slow/hung provider blocks the request indefinitely.

**Why it happens:**
Structured output is ~60–70% reliable raw; people assume `json.loads` will just work and don't budget for retries or partials.

**How to avoid:**
- Validate every response against a Pydantic/JSON schema (TZ §29.2). On failure, **one** corrective retry that feeds back the invalid output + the validation error (this pattern lifts parse success ~60–70% → ~95–97%).
- Wrap the call in an explicit timeout. On timeout/second-failure, save `status=failed` + `generation_error`, and either (a) fall back to deck-modified base meanings from DB (a real, if less personalized, reading) or (b) show the soft error and **do not consume the user's limit** (TZ: "списывать лимит только при успешном создании расклада").
- Limit-decrement happens only after a validated reading is persisted — never before the LLM call.
- Strip code fences / extract the JSON object defensively before parsing.

**Warning signs:**
- Raw `json.loads` with no schema validation or retry.
- No timeout on the LLM client.
- Limit is decremented before/independent of generation success.
- No `failed` path that preserves the question and the user's quota.

**Phase to address:** Этап 5 (Генерация).

---

### Pitfall 7: Copying real decks / using commercial names / "in style of" art → legal exposure

**What goes wrong:**
Shipping Rider–Waite–Smith scans or near-identical compositions, using commercial deck/publisher names in the UI, generating art via "in style of [living artist/deck]" prompts, or pulling Pinterest/Google assets without a license. Tarot *meanings and structure* are not protectable, but specific *illustrations* (RWS card art, named decks) are. This is a takedown/legal risk that can kill a public launch and is expensive to unwind once 6 decks of assets are baked in.

**Why it happens:**
RWS imagery is the cultural default and trivially available; "make it look like the classic Tarot" quietly reproduces protected art. The data model can also accidentally entangle universal meaning with a specific deck's look.

**How to avoid:**
- **Separation is already in the schema and must be enforced**: universal meaning in `cards` (deck-agnostic); per-deck *style only* in `deck_cards` (`image_url`, `visual_prompt`, deck modifiers). Never store deck-specific art assumptions in `cards`.
- Original art only; original deck names only (TZ §5 — 6 original deck names already chosen). No commercial deck/publisher names in UI copy, prompts, or seed data.
- Code-side this is cheap because of правка #4: ship `image_url` slots + atmospheric CSS/SVG fallback; **no bespoke art is required on day 1**. Real art is uploaded via admin and must clear legal review *before public launch* (constraint in PROJECT.md / TZ §25.3).
- If using generative art for assets, store provenance and keep it out of "in style of [protected work]" territory; human review + legal check before publishing.

**Warning signs:**
- Any asset filename, `visual_prompt`, or seed value references RWS / a commercial deck / a living artist.
- Card art committed without a license/provenance record.
- `cards` table holding deck-specific imagery or style.

**Phase to address:** Этап 3 (seed data / data model enforces separation) + a launch gate in Этап 10 (legal review before public). Day-1 code is safe via CSS/SVG fallback.

---

### Pitfall 8: Cards drawn on the frontend / non-crypto RNG → manipulable, unfair readings

**What goes wrong:**
Drawing cards client-side lets a user re-roll for a "better" outcome or forge a reading, and breaks single-source history. Using `Math.random()` / `random.random()` (non-CSPRNG) is predictable and, for a product whose whole premise is a trustworthy oracle, undermines fairness.

**Why it happens:**
Drawing on the client is less round-trips and "feels instant"; default RNG is the first thing reached for.

**How to avoid:**
- Card selection + orientation **only on backend** (TZ §12.4, §29.2; правка locked). Frontend animates *already-decided* cards streamed from the server.
- Use a CSPRNG (`secrets` in Python) to shuffle the active deck and pick N cards.
- Orientation: if `reversals_enabled` → 70% upright / 30% reversed via CSPRNG (TZ §8.3); else all upright.
- Persist `seed`/`debug_hash` server-side for reproducibility/debugging but never expose it (TZ §12.5).

**Warning signs:**
- Any card/orientation logic in frontend code.
- `Math.random()` / `random.random()` in the draw path.
- `POST /api/readings` accepts a client-provided card list.

**Phase to address:** Этап 5 (CardDrawService), backend-only.

---

### Pitfall 9: Free-limit abuse — weekly-reset bugs and multi-account farming

**What goes wrong:**
The weekly reset is the classic off-by-one: comparing wall-clock weeks, mishandling timezones, or resetting on read so a user near the boundary gets extra readings; or a race where two concurrent `POST /api/readings` both pass the limit check and both decrement (TOCTOU) → free over-spend. Separately, multi-account farming (new Telegram account = fresh 3/week) caps how much abuse you can ever stop.

**Why it happens:**
"3 per week" sounds trivial, so reset logic is written ad hoc without a fixed anchor, and the check-then-decrement is done as two unguarded steps.

**How to avoid:**
- Anchor the window deterministically: store `week_start` (ISO week, UTC) on `user_limits`; on each reading, if `current_iso_week > week_start` reset counters atomically, then check.
- Make check+decrement atomic: a single `UPDATE ... SET free_used = free_used + 1 WHERE ... AND free_used < free_weekly_limit RETURNING ...` (or row lock / Redis token), so concurrent requests can't both succeed.
- Redis throttle for burst/anti-spam on reading creation (TZ §25.6) — distinct from the weekly quota.
- Accept that `telegram_id` is the identity anchor; multi-account farming is *bounded* not *eliminated* (creating Telegram accounts has friction). Do not over-engineer device fingerprinting (privacy + TZ scope).

**Warning signs:**
- Reset logic compares dates without a stored week anchor, or resets inside a GET.
- Limit check and decrement are separate non-atomic statements.
- No Redis rate-limit on `POST /api/readings`.
- Concurrency test (two simultaneous reading requests at limit boundary) not written.

**Phase to address:** Этап 7 (Лимиты). Redis throttle scaffolding from Этап 1 (Redis provisioned).

---

### Pitfall 10: Brand-voice leak — product sounds like an AI chatbot, not a ritual

**What goes wrong:**
The word "AI"/"нейросеть"/"модель"/"сгенерировано ИИ" surfaces in UI copy, loading text, error states, or — most commonly — leaks *through the model's own output* ("как ИИ-модель, я не могу…", "я был обучен…"). Generic assistant phrasing ("Конечно! Вот ваш расклад:") shatters the "I opened a mystical ritual, not a chatbot" emotion that is the product's entire differentiation (TZ §0, §25.1).

**Why it happens:**
LLMs default to assistant register and self-reference, especially on refusals. Technical/error states are written by developers who forget they're player-facing.

**How to avoid:**
- System prompt forbids AI self-reference (TZ §16 already does) **and** a post-generation banned-phrase filter strips/flags leaks (TZ §15) — prompt alone is insufficient, especially on refusals.
- All player-facing strings (loading, empty, error, paywall) written in deck voice (TZ §9.8 supplies them: "Колода замолчала на мгновение…"). No raw stack traces (TZ §29.2).
- Refusals are *soft redirects in character*, never "Я ИИ и не могу" (TZ §16: avoid "я не могу" without a gentle alternative).
- Ritual framing reinforced by UX, not just text: deck chosen before generation, shuffle animation, cards revealed before text (TZ §25.1).

**Warning signs:**
- Any UI string containing AI/нейросеть/модель (outside legally required notices).
- No post-output filter for assistant-register leaks.
- Refusal copy that breaks character.

**Phase to address:** Этап 5 (output filter in generation) + Этап 4/10 (in-character UI/error copy).

---

### Pitfall 11: Reversed-card UX causing anxiety

**What goes wrong:**
Treating reversed cards as "bad" (50/50 odds, ominous phrasing) makes readings feel negative and scary — wrong for an 18–35 mass-market self-reflection product and contrary to the "не приговор, а подсказка" principle (TZ §1.5, §8).

**Why it happens:**
Traditional tarot often frames reversals negatively; the default 50/50 + literal "reversed = opposite/bad" carries that anxiety into the app.

**How to avoid:**
- 70% upright / 30% reversed (TZ §8.3) — fewer reversals, less perceived negativity.
- Reversed framed as block / delay / inner tension / unrevealed energy, **never** "bad" (TZ §8.4); enforced in the system prompt (TZ §16 principle 6) and per-deck modifiers (e.g. Тени Арканов forbids беда/проклятие/опасность/рок).
- First-run plain-language explainer (TZ §8.2) + user toggle to disable reversals (`reversals_enabled`).

**Warning signs:**
- Orientation probability is 50/50.
- Generated reversed text uses fatalistic words.
- No onboarding explainer / no settings toggle.

**Phase to address:** Этап 5 (probability + prompt rules) and Этап 4 (explainer + toggle UI).

---

### Pitfall 12: Subscription modeling with Stars — recurring vs 30-day window confusion

**What goes wrong:**
Conflating a true Telegram **recurring** Stars subscription with a manual 30-day entitlement window, leading to: assuming arbitrary periods work (Telegram allows **only** `subscription_period = 2592000` / 30 days), not handling renewal `successful_payment` updates (`is_recurring=true`, `is_first_recurring=false`), ignoring `subscription_expiration_date`, providing no cancel path, or double-counting renewals as fresh purchases. Mismatched state means users keep access after cancel/expiry or lose it early.

**Why it happens:**
Stars recurring subscriptions are newer than most training data; the TZ (§11.5) leaned toward a simple balance, and правка #7 chose a 30-day entitlement window — but the native recurring API has hard constraints that are easy to model wrong.

**How to avoid:**
- Decide explicitly (правка #7): **native recurring** (`createInvoiceLink` with `subscription_period=2592000`) *or* **manual 30-day window** — and model exactly that, not a hybrid.
- If native recurring: `subscription_period` must be exactly `2592000`; price is fixed for the subscription; one active subscription per user per bot. On each renewal you receive a `successful_payment` with `is_recurring=true` — apply it idempotently (Pitfall 2) and extend the period; persist `subscription_expiration_date`. Cancel via `editUserStarSubscription(user_id, telegram_payment_charge_id, is_canceled=true)` → stops renewal, access kept until period end. Re-enable with `is_canceled=false`.
- If manual window: on `successful_payment`, set `current_period_end = now + 30d` on `subscriptions`; entitlement checks compare against `current_period_end`; "renewal" is a new purchase. No native auto-debit.
- Entitlement check is a single source of truth (`subscriptions.status` + `current_period_end`), separate from `paid_spreads_balance` and from the free weekly counter (three independent buckets — TZ §11.5).
- Handle refunds → revoke/adjust entitlement (TZ §11.4 п.20) within the 21-day refund window.

**Warning signs:**
- `subscription_period` set to anything but `2592000`.
- Renewal `successful_payment` (`is_recurring=true`) not handled or treated as a new product.
- No cancel path; or cancel revokes access immediately instead of at period end.
- Subscription, paid balance, and free quota tangled in one counter.

**Phase to address:** Этап 8 (Payments). Decide recurring-vs-window before writing the schema usage.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Read `telegram_id` from `initDataUnsafe` / request body | Skips HMAC plumbing | Full auth bypass; spoofed identity, drained balances, admin impersonation | **Never** |
| Per-card LLM calls "for simplicity" | Easy to reason about | 4–5× cost & latency, cross-card drift | **Never** — single call is locked (правка #1); per-card only as fallback |
| Grant entitlement without UNIQUE/idempotency | Fewer lines | Double-grants on Telegram retries; revenue/trust loss | **Never** |
| Safety as prompt-only, no classifier/regex | One less component | Crisis questions get mystical readings; liability | **Never** (правка #3 made classifier mandatory) |
| Draw cards on frontend | Instant, fewer round-trips | Manipulable, unfair, broken history | **Never** |
| `Math.random()` for draw | Trivial | Predictable, undermines fairness premise | **Never** — use CSPRNG |
| Placeholder CSS/SVG card art at launch | Ships 6 decks day 1 without 468 illustrations | None if art slots exist; real art via admin later | **Yes** — explicitly chosen (правка #4) |
| `env(safe-area-inset-*)` instead of Telegram SDK insets | Standard CSS, less code | Bottom CTA covered on iOS inside Telegram | Only with SDK-inset fallback |
| Manual 30-day window instead of native recurring Stars | Simpler billing logic | No auto-renew; manual re-purchase friction | **Yes** if recurring API is unavailable/undesired (правка #7) |
| Skip token logging in `generation_logs` | Faster first cut | Cost invisible until the bill; no latency dashboard | Only briefest spike; wire before Этап 5 ships |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Telegram initData | Using `initDataUnsafe`; raw token as HMAC key; unsorted check-string; no `auth_date` check | `secret=HMAC_SHA256("WebAppData", token)`; sorted `key=value\n` excl. `hash`; compare hex HMAC; reject stale `auth_date` |
| Stars `pre_checkout_query` | Slow/blocking validation; dropping the update | Answer within **10s** with fast indexed checks; always answer (true or false+message); grant nothing here |
| Stars `successful_payment` | Granting on intent; no idempotency; out-of-transaction | Grant only here, idempotent via UNIQUE(`payload`)/charge_id, in one transaction; store `telegram_payment_charge_id` |
| Stars subscriptions | Arbitrary `subscription_period`; ignoring renewal/cancel | `subscription_period=2592000` only; handle `is_recurring` renewals idempotently; cancel via `editUserStarSubscription(is_canceled=true)` |
| Stars refunds | No revocation; assuming unlimited window | `refundStarPayment(user_id, telegram_payment_charge_id)` within **21 days**; adjust entitlement on refund |
| LLM provider | `json.loads` with no schema/retry/timeout | Pydantic-validate; one corrective retry with error feedback; hard timeout + DB fallback |
| Telegram theme | Hardcoding colors; ignoring theme changes | Consume `themeParams` / CSS vars; react to `themeChanged`; design dark-first but handle light |
| Mini App viewport | `100vh` + `env()` insets | Use `viewportStableHeight` for bottom-pinned CTA; SDK `safeAreaInset`/`contentSafeAreaInset`; `viewport-fit=cover` |
| timeweb.cloud deploy | Assuming managed PG/Redis auto-provision; HTTP webhook | HTTPS mandatory for WebApp + bot webhook; managed PostgreSQL/Redis/S3 + VPS provisioned **manually** (MCP only does App Platform git deploy) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Per-card LLM calls | High latency per reading, big bill | Single structured call (правка #1) | Immediately at any real volume |
| Synchronous LLM with no timeout (queue removed) | Requests hang on slow provider; workers exhausted | Hard timeout + fallback; keep one fast call | Under provider latency spikes / concurrency |
| No base-meaning reuse | Re-deriving static meanings every call → tokens | Store in `cards`/`deck_cards`, pass as context | Cost scales linearly with traffic |
| Non-atomic limit check+decrement | Free over-spend under concurrency | Atomic `UPDATE ... WHERE used < limit` / lock | Concurrent requests from same user |
| Unbounded LLM output | Latency/cost drift, truncated JSON | `max_tokens` + per-field caps (TZ §17/§18) | Gradually, then truncation errors |
| Unindexed history/payments queries | Slow `/history`, slow pre-checkout | Index `user_id`, `payload`, `charge_id` | As rows grow (history, payments) |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Trusting `initDataUnsafe` / body `telegram_id` | Full account/identity spoofing | Server-side HMAC validation; derive id only from validated initData |
| No `auth_date` freshness check | Replay of leaked initData indefinitely | Reject stale `auth_date` (TTL) |
| Admin = client-asserted Telegram ID | Privilege escalation to admin CRUD | Allowlist `ADMIN_TELEGRAM_IDS` checked **server-side** against validated id (правка #6) |
| Granting Stars entitlement without idempotency | Double-grant / paid-access bypass | UNIQUE(`payload`)/charge_id; grant only on `successful_payment` |
| Card draw / limit check on frontend | Manipulated outcomes, free over-spend | Backend-only draw & limit (TZ §29.2) |
| Non-CSPRNG randomness | Predictable "fair" draws | `secrets`/CSPRNG |
| Leaking stack traces / internal errors to UI | Info disclosure + brand break | Soft in-character errors; log details server-side (TZ §29.2) |
| Exposing `seed`/`debug_hash` to client | Reproducible/forgeable draws | Keep server-side only (TZ §12.5) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Crisis question → mystical reading | Harmful, unsafe, liability | Regex pre-filter + classifier → supportive safe template (TZ §20.3) |
| "AI/нейросеть" leaks in copy or output | Breaks the ritual; product = generic chatbot | Banned-phrase filter + in-character strings (TZ §15/§9.8) |
| 50/50 reversals + ominous phrasing | Anxiety, "negative" readings | 70/30 + block/delay/unrevealed framing (TZ §8) |
| Categorical predictions / asserting others' feelings | False certainty, emotional harm | Hedged phrasing only (TZ §15 allowed list) |
| Bottom CTA hidden under iOS home bar / keyboard | Can't tap "Начать расклад"/Pay | SDK safe-area insets + `viewportStableHeight`; sticky CTA respects insets |
| Pushy/fear-based paywall | Erodes trust, violates principles | "Открыть ещё один расклад", no fear/manipulation (TZ §11.2) |
| Limit consumed on failed generation | User pays quota for nothing | Decrement only after validated reading persisted |
| Sharing card exposes private question by default | Privacy leak | Exclude full personal question unless user opts in (TZ §10.4) |

## "Looks Done But Isn't" Checklist

- [ ] **initData auth:** Often missing tampered-hash & stale-`auth_date` rejection — verify with a test that feeds a forged `hash` and a 2-day-old `auth_date` and asserts 401.
- [ ] **Stars payment:** Often missing idempotency — verify the same `successful_payment` delivered twice grants once (UNIQUE on `payload`/charge_id).
- [ ] **pre_checkout:** Often missing the 10s budget — verify validation is fast indexed lookups only and always answers.
- [ ] **Subscriptions:** Often missing renewal/cancel — verify `is_recurring` renewal handled idempotently and `editUserStarSubscription(is_canceled=true)` keeps access until period end.
- [ ] **Refunds:** Often missing entitlement revocation — verify `refundStarPayment` path adjusts access and records status (within 21d).
- [ ] **Safety:** Often missing the override path — verify a crisis prompt returns the safe template, never a card reading; classifier emits `safety_category`.
- [ ] **LLM JSON:** Often missing retry/timeout/fallback — verify malformed JSON triggers one corrective retry, then DB fallback, and does **not** consume the limit.
- [ ] **Card draw:** Often missing backend-only enforcement — verify `POST /api/readings` ignores any client-supplied cards and uses CSPRNG.
- [ ] **Limits:** Often missing atomicity & deterministic reset — verify concurrent boundary requests can't both pass; reset uses stored `week_start`.
- [ ] **Brand voice:** Often missing output filter — verify generated text containing "ИИ/модель" is stripped/flagged; refusals stay in character.
- [ ] **IP separation:** Often missing — verify `cards` holds no deck-specific art; no RWS/commercial names in seed/prompts/assets.
- [ ] **Viewport:** Often missing iOS inset handling — verify bottom CTA/Pay reachable with keyboard open and on notched iPhones inside Telegram.
- [ ] **Theme:** Often missing reactivity — verify switching Telegram light/dark updates the app live.
- [ ] **Deploy:** Often missing manual provisioning — verify HTTPS, bot webhook reachable, managed PG/Redis/S3 provisioned (not auto).

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Spoofable initData shipped | HIGH | Patch validation immediately; invalidate sessions; audit payments/history for spoofed `telegram_id`; rotate bot token if leaked |
| Stars double-grant in prod | MEDIUM | Add UNIQUE/idempotency; reconcile balances against `payments` via `telegram_payment_charge_id`; correct over-grants |
| Crisis safety gap shipped | HIGH | Add regex pre-filter + override now; review `generation_logs` for past sensitive prompts; enable report button |
| Per-card calls in prod | MEDIUM | Refactor to single call; per-card stays as fallback; immediate cost drop |
| Invalid-JSON crashes | LOW–MEDIUM | Add schema+retry+timeout+fallback; replay failed readings from saved questions |
| Infringing art published | HIGH | Pull assets, swap to CSS/SVG fallback (slots already exist), re-commission, legal review before re-publish |
| Free-limit over-spend | MEDIUM | Make check+decrement atomic; add Redis throttle; reconcile counters |
| Wrong subscription model | MEDIUM–HIGH | Reconcile against `subscriptions`/charge ids; migrate to chosen model; honor active access during migration |
| iOS CTA covered | LOW | Switch to SDK insets + `viewportStableHeight`; test on notched device |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase (TZ §23) | Verification |
|---------|---------------------------|--------------|
| 1. initData spoofing | Этап 2 (Telegram auth) | Forged-hash & stale-`auth_date` tests reject; id only from validated initData |
| 2. Stars double-grant | Этап 8 (Payments) | Duplicate `successful_payment` grants once; UNIQUE present |
| 3. pre_checkout 10s timeout | Этап 8 (+ Этап 10 latency) | Pre-checkout fast-only, always answers; latency logged < budget |
| 4. Crisis → mystical reading | Этап 5 (Генерация); templates seeded Этап 3 | Crisis prompt returns safe template; `safety_category` emitted |
| 5. LLM cost/latency blowup | Этап 5 (Генерация) | Single call; token/latency in `generation_logs` + dashboard |
| 6. Invalid JSON / no timeout | Этап 5 (Генерация) | Malformed JSON → retry→fallback; limit not consumed on fail |
| 7. Deck IP infringement | Этап 3 (schema/seed) + Этап 10 (legal gate) | No RWS/commercial refs; `cards` style-free; CSS/SVG day-1 |
| 8. Frontend draw / weak RNG | Этап 5 (CardDrawService) | Server-only draw, CSPRNG; client cards ignored |
| 9. Free-limit abuse | Этап 7 (Лимиты); Redis from Этап 1 | Atomic check+decrement; deterministic weekly reset; Redis throttle |
| 10. Brand-voice leak | Этап 5 (output filter) + Этап 4/10 (copy) | No AI terms in UI/output; in-character refusals/errors |
| 11. Reversed-card anxiety | Этап 5 (prob+prompt) + Этап 4 (UX) | 70/30; non-fatalistic reversed text; explainer + toggle |
| 12. Subscription modeling | Этап 8 (Payments) | Chosen model only; renewals idempotent; cancel = access to period end |

## Sources

- Telegram Mini Apps — initData validation (secret key, data-check-string, `auth_date`, `initDataUnsafe` warning, themeParams, viewport, safe-area insets): https://core.telegram.org/bots/webapps — HIGH
- Telegram Bot Payments for Digital Goods (Stars; `answerPreCheckoutQuery` 10s rule; store `telegram_payment_charge_id`; `refundStarPayment`): https://core.telegram.org/bots/payments-stars — HIGH
- Telegram Star subscriptions (`subscription_period`=2592000 only, monthly auto-debit): https://core.telegram.org/api/subscriptions — HIGH
- Telegram Bot API changelog (`subscription_period`, `is_recurring`/`is_first_recurring`/`subscription_expiration_date` on SuccessfulPayment, `editUserStarSubscription`): https://core.telegram.org/bots/api-changelog — HIGH
- `editUserStarSubscription` (`is_canceled` semantics — keep access to period end): https://gramio.dev/telegram/methods/edituserstarsubscription — MEDIUM
- Stars refund window (21 days) & idempotency via UNIQUE(charge_id): https://core.telegram.org/bots/payments-stars + practitioner reference (n8n Stars refund workflow) — MEDIUM
- Telegram Mini App viewport / keyboard / safe-area iOS quirks (`env(safe-area-inset-*)` unreliable inside Telegram; `viewportStableHeight`): https://docs.telegram-mini-apps.com/platform/viewport ; https://github.com/TelegramMessenger/Telegram-iOS/issues/1410 ; https://github.com/TelegramMessenger/Telegram-iOS/issues/1377 — MEDIUM
- LLM structured-output reliability (low temp; corrective retry lifts parse success ~60–70%→95–97%; truncation/enum/refusal edge cases): https://apxml.com/courses/prompt-engineering-llm-application-development/chapter-7-output-parsing-validation-reliability/handling-parsing-errors ; https://dev.to/pockit_tools/llm-structured-output-in-2026-stop-parsing-json-with-regex-and-do-it-right-34pk — MEDIUM
- Tarot IP separation (meanings/structure not protectable vs. specific deck art) grounded in TZ §5 strategy + PROJECT.md constraints — MEDIUM (domain reasoning)

---
*Pitfalls research for: Telegram Mini App AI-таро (initData, Telegram Stars, LLM safety, tarot IP)*
*Researched: 2026-06-09*
</content>
</invoke>
