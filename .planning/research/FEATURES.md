# Feature Research

**Domain:** Telegram Mini App — AI-powered (concealed) tarot / oracle reading with atmospheric ritual UX and Telegram Stars monetization
**Researched:** 2026-06-09
**Confidence:** HIGH (table stakes + monetization + safety verified against live apps, Telegram Bot API docs, and tarot-ethics sources; differentiator framing MEDIUM-HIGH — validated by tarot-community sources on deck "personality")

> Source of truth for scope is `REFERENCE-TZ.md` + `PROJECT.md`. This file categorizes that scope against the wider ecosystem and flags complexity/dependencies for the roadmap. Where the spec and the market disagree, that is called out.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any tarot/oracle reading app. Missing these = product feels broken or untrustworthy. All are in-scope per TZ.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Frictionless entry / auth | Telegram users expect zero registration; the whole pitch is "first reading without a long signup" (TZ §1.5, §3.1) | LOW | Telegram `initData` validated server-side. No password/email. This is also the auth root all gated features hang off. |
| Skippable onboarding (3–4 screens) | Sets expectations (it's a ritual, "not a verdict"), explains reversed cards, builds trust before the ask | LOW | TZ §9.1. Must be skippable; `onboarding_completed` flag. Cheap, high-trust ROI. |
| Free-text question input | Personal question = personal-feeling reading; baseline for every reading app | LOW | 10–500 chars; empty allowed → general reading; too-short → gentle nudge (TZ §3.2). Input is also the safety-classifier entry point. |
| Topic selection | Helps route the right spread/tone; standard in Co-Star/tarot apps (love/work/money/choice/day/self) | LOW | 7 topics (TZ §3.3). Drives spread recommendation + feeds prompt + saved to history. |
| Deck selection | Choosing a deck is core tarot UX; here it is elevated to THE differentiator (see below) | MEDIUM | 6 decks, all free in MVP. Each deck card shows atmosphere / best-for / tone / visual preview (TZ §3.4). |
| Spread selection + recommendation | Users don't want to think about which layout; "recommended spread" reduces choice paralysis | LOW-MEDIUM | 7 spreads of 3–4 cards; recommendation by topic via `/spreads/recommend` (TZ §3.5, §6). |
| Card draw (server-side, secure random) | Fairness + anti-tamper is implicit trust; users assume the draw is "real" | LOW | Cryptographically secure shuffle on backend only; 70/30 upright/reversed (TZ §12.4–12.5). Never client-side. |
| Per-card interpretation | The literal product — meaning per card, per position, per orientation | MEDIUM | Card name, position, orientation, short meaning, deep interpretation, mystical accent (TZ §3.7, §17). |
| Overall summary / synthesis | Users want a connected conclusion, not 4 disconnected blurbs | MEDIUM | Connection + main factor + attention point + soft advice + closing line (TZ §9.5, §18). Differentiates from "card-dictionary" apps. |
| Reading history (list + detail + delete) | Re-reading old readings is a top behavior; expected in every tarot app | MEDIUM | Auto-save; list shows date/question/deck/spread/thumbnails/short summary; soft delete (`deleted_at`). Last 10 free (TZ §3.8, §11.1). |
| Upright + reversed card meanings | Any "real" tarot app supports both orientations; absence reads as toy | LOW | Universal `meaning_upright`/`meaning_reversed` in data model; user toggle to disable (TZ §8). |
| Card-of-the-day style quick spread | Daily-card is the single most common tarot-app retention feature (Co-Star, Labyrinthos, Aura, Tarotoo all have it) | LOW | Covered by "Карта дня: три знака" spread + "day" topic. Note: TZ defers *push* "card of the day" — the spread itself ships, just no notification. |
| Profile + settings | Users expect to see balance, subscription state, and control reversed/personalization toggles | LOW | Name from Telegram, spreads balance, subscription, reversals toggle, history-personalization consent (TZ §3 profile). |
| Free usage limit + clear paywall | Freemium is the universal model; users accept a limit if the paywall is honest, not fear-based | MEDIUM | 3 free/week, weekly reset; soft paywall on exhaustion (TZ §3.9, §11.1). Depends on auth + reading flow. |
| In-app purchase via Telegram Stars | Telegram *mandates* Stars for digital goods; external payment is not an option | HIGH | invoice → pre_checkout → successful_payment → grant; refunds; idempotency by payload (TZ §11.4). Hard requirement, real complexity (see deps). |
| Graceful errors / empty states (in-voice) | "Колода замолчала на мгновение…" — even failures must stay in character or the ritual illusion breaks | LOW | TZ §9.8. Branded copy for generation error, payment error, limit reached, empty question, unsafe query. |

### Differentiators (Competitive Advantage)

Features that set this product apart. The first one IS the product — everything else is supporting cast.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Same question, different deck = different experience** ★ CORE | The entire reason to exist (PROJECT.md Core Value, TZ §30). 6 decks each change *artwork + tone + answer structure + accents + vocabulary*, not just a skin. Validated by tarot community: readers genuinely experience the same cards differently across decks ("kind voice" vs "sassy") driven by art/color/tone. Most apps have ONE voice. | HIGH | Mechanism = per-deck `prompt_modifier` + `deck_specific_*` card modifiers + per-deck palette/microcopy/particles (TZ §19, §10). The roadmap must protect this: if prompt-modifier differentiation is weak, the product has no reason to exist. Needs A/B/blind testing of deck outputs (TZ §25.2). |
| Per-deck theming (atmosphere engine) | Makes deck choice *felt*, not just labeled. Background, accent color, microcopy, card back, particle animation all swap per deck (TZ §10.1). This is what makes it "a ritual, not an AI chat." | MEDIUM-HIGH | 6 palettes already specified (TZ §21.2). Data-driven via `decks.visual_style` JSONB. Mostly CSS/Framer Motion + asset slots; works on day 1 even before bespoke art (PROJECT.md edit #4). |
| Ritual reveal sequence | Shuffle/"deck hears your question" prep screen → one-by-one card flip with short phrase before meaning → final "gathering" into summary. Converts a DB read into an experience; primary anti-"AI chatbot" lever (TZ §25.1). | MEDIUM | Framer Motion: prep states, flip, staggered reveal, glow, haptics. Depends on reading generation being *ready* before/while revealing (results pre-generated, revealed progressively — TZ §12.3). |
| Reversed-card mechanic with gentle framing | Differentiator vs both toy apps (upright-only) AND scary apps. 70/30 (not 50/50) + reframing reversed as "delay / block / unrevealed energy," never "bad" (TZ §8). Lower anxiety = better mass-market + monetization. | LOW-MEDIUM | Probability + framing live in prompt rules and card data. User-toggleable. Cheap, on-brand. |
| Deck/voice personality consistency | Each deck refuses certain phrasings and prefers certain metaphors (`allowed_metaphors`, `forbidden_phrasings` per deck — TZ §5.3). E.g. Shadow deck bans "беда/проклятие/рок." Gives decks believable, distinct character. | MEDIUM | Encoded in deck modifier + safety layer. Reinforces the core differentiator; also a safety control. |
| Share-card (privacy-safe) | Organic growth loop without a social graph. Beautiful deck-themed card with cards + short summary, *excludes the full personal question by default* (TZ §10.4). | MEDIUM | Render to image (client canvas or server). Privacy-by-default is the trust differentiator vs typical "share everything" apps. Depends on completed reading + deck theme. |
| Brand-voice concealment of AI | Never says "AI / нейросеть / модель / сгенерировано ИИ" in UI; speaks *as the deck* (TZ §0, §1.5). Reframes a commodity (LLM text) as a premium ritual — a genuine positioning edge in a sea of "AI tarot" apps. | LOW | A copy/voice constraint, not a feature to build — but must be enforced everywhere (errors, buttons, loading). |
| Topic→deck→spread fit guidance | Compatibility matrix recommends spreads per topic and notes which decks suit which themes (TZ §7, `deck_spread_compatibility`). Reduces "wrong tool" feeling; makes the product feel like it *understands* the question. | LOW-MEDIUM | Mostly seed data + a recommendation endpoint. Low build cost, high perceived intelligence. |

★ = the one differentiator the whole roadmap exists to protect.

### Safety & Ethics Features (First-Class — NOT optional)

Treated as a primary category, not an afterthought. Divination that gives life advice carries real duty-of-care; tarot-ethics literature is explicit that readers must take mental-health disclosures seriously, never give medical/legal/financial advice, and route crisis to real help. PROJECT.md edit #3 promotes the classifier from "desirable" to **mandatory**.

| Feature | Why Required | Complexity | Notes |
|---------|--------------|------------|-------|
| Safety classifier (normal / *_sensitive / crisis) | Core duty-of-care gate. Categories: relationship/financial/health/legal/crisis/abusive (TZ §20.4). | MEDIUM | Cheap path = regex pre-filter + classification folded into the single structured LLM call (PROJECT.md edit #1/#3). Runs *before* the answer is committed. |
| Crisis handling (no mystical "prediction") | Self-harm / violence / abuse must NOT get a mystical forecast — instead a supportive message + suggestion to reach a trusted person / local services (TZ §20.3). Matches tarot-ethics "connect people in crisis with the right help." | MEDIUM | Dedicated `refusal`/`safety` prompt templates. Region-aware resource suggestion is a stretch goal; a safe generic message is the MVP floor. |
| No-categorical-predictions guardrail | Banned: "точно случится," "он тебя любит," "тебя ждёт беда," income guarantees, medical/legal directives (TZ §15, §16, §20.1). | LOW-MEDIUM | Enforced in system prompt + allowed/forbidden phrasing lists + JSON-schema validation. Per-deck forbidden lists add a second layer. |
| Disclaimers / "not a substitute for a professional" | Tarot is legally framed as entertainment; standard apps state readings don't replace medical/legal/financial/psychological help. | LOW | Surface in onboarding, profile/settings, and unsafe-query copy ("Колода не заменяет помощь специалиста…" TZ §9.8). Pure content, high liability-reduction. |
| Sensitive-topic soft modifiers | Health/pregnancy/death/money/infidelity/dependency get extra-careful phrasing injected, not blocked (TZ §3.2: "не блокируются агрессивно, но обрабатываются безопасно"). | LOW-MEDIUM | `safety_modifier` appended to prompt for sensitive classes. Keeps UX warm while staying safe. |
| "Report this answer" + error logging | Human-in-the-loop backstop for harmful generations (TZ §25.4). Lets ops catch what the classifier misses. | LOW | Generation logs already in data model; add a user-facing report action. Feeds admin review. |

### Anti-Features (Do NOT Build for MVP)

Documented to prevent scope creep. Each carries the reason from the spec and/or market. These are *deliberate* exclusions (TZ §2.2 + PROJECT.md edits).

| Anti-Feature | Why Requested / Surface Appeal | Why Problematic | Alternative |
|--------------|-------------------------------|-----------------|-------------|
| Social feed of readings | "Communities drive engagement" | Readings are intimate; a feed invites comparison, oversharing, moderation burden — antithetical to a private ritual | Privacy-safe **share-card** (opt-in, question hidden by default) — growth without a social graph |
| Public user profiles | "Identity / status" | No social value here; pure privacy/moderation liability | Private profile only (balance, subscription, settings) |
| Deck marketplace | "UGC scale, long-tail revenue" | Massive surface (creator tools, payouts, IP review, ratings); not the core value | Admin-curated decks only; premium/seasonal decks ship later via admin, post-MVP monetization |
| On-the-fly card image generation | "Infinite unique art" | Cost + latency per reading; legal exposure ("in style of [deck/artist]"); breaks the single-fast-call model | Pre-assigned `image_url` slots + atmospheric CSS/SVG fallback; real art uploaded via admin (PROJECT.md edit #4) |
| Voice fortune-teller | "Immersion" | TTS cost/latency, accessibility QA, voice-art direction per deck — large build for an unproven win | Text + microcopy + haptics carry the ritual; revisit post-MVP (TZ §24.2) |
| Post-reading chat | "Let me ask a follow-up" | Turns the ritual back into an "AI chat" (the exact thing the product avoids per §25.1); unbounded LLM cost; harder safety surface | New reading per question; one structured call each (keeps cost/illusion intact) |
| Referral program / gamification with levels | "Viral growth, retention" | Premature optimization before PMF; invites free-tier abuse; adds fraud surface | Validate core loop first; light share-card now. Defer referrals (TZ §24.2) |
| Push "card of the day" | "Daily retention hook" | Telegram push UX + opt-in/abuse management before the loop is proven; notification fatigue | Ship the day-spread *in-app* now; add notifications post-MVP (TZ §2.2 — "можно после MVP") |
| Background job queue (Celery/RQ/Arq) | "Scalable async generation" | Generation = ONE fast LLM call; a queue adds infra, ops, and latency-perception complexity for zero benefit at this scale | Synchronous call inside the request with a timeout; Redis only for rate-limit/cache (PROJECT.md edit #2) |
| Complex personal memory (cross-reading) | "Deeper personalization" | Privacy risk without explicit consent; storage/PII complexity | History-personalization is *opt-in*, off by default; only passed to prompt if consented (TZ §2.2, §18) |
| External payment acquiring | "Lower fees / familiar checkout" | Telegram **requires** Stars for digital goods — non-Stars acquiring risks app rejection | Telegram Stars only (XTR) |
| Native iOS/Android apps | "App store reach" | Web-first inside Telegram is the whole distribution thesis; native doubles build/maintenance | Mobile-first web mini app (360–430px) |
| 468 bespoke illustrations (78×6) on day 1 | "It must look finished" | That's a *content* effort, not MVP code; would block launch on art production | All 6 decks function visually via theme + fallback on day 1; arts trickle in through admin (PROJECT.md edit #4) |

---

## Admin / Content-Ops Features

The product is content-and-prompt-driven, so the admin panel is a **first-class MVP surface**, not a luxury — decks, card meanings, prompts, and pricing must be editable without code deploys (TZ §22, §30). Admin auth = Telegram-ID allowlist on protected `/admin` routes (PROJECT.md edit #6).

| Feature | Purpose | Complexity | Notes |
|---------|---------|------------|-------|
| Dashboard metrics | Operate the business: users total/today, readings today/week, payment conversion, revenue (Stars), popular deck/topic, generation error rate + avg latency (TZ §22.2) | MEDIUM | Read-mostly aggregations over events/readings/payments. |
| CRUD decks | Create/edit deck, description, preview, `prompt_modifier`, `access_type`, `sort_order` (TZ §22.3) | MEDIUM | Editing `prompt_modifier` directly tunes the core differentiator — high-leverage screen. |
| CRUD cards + deck_cards | Edit universal meanings (upright/reversed/keywords/advice) and bind per-deck art + style modifiers (TZ §22.4) | MEDIUM | Two-layer model (`cards` vs `deck_cards`) keeps universal meaning separate from deck style (IP-safe, TZ §5.3). |
| CRUD spreads (+ positions) | Manage spreads, card counts, positions, `prompt_instruction` per position | MEDIUM | Position prompt-instructions shape interpretation quality. |
| CRUD prompt templates (versioned) | Create new prompt version, activate one, view history, fast-disable a bad prompt (TZ §22.5) | MEDIUM | Versioning + `prompt_version` logging enables safe iteration and rollback. |
| CRUD products / tariffs | Manage Stars prices, spread amounts, subscription days | LOW-MEDIUM | Pricing experiments without deploys. |
| Toggle deck / spread | One-click disable a problematic deck or spread (TZ §22.1, `/toggle` endpoints) | LOW | Critical incident lever — pull a deck/spread that's producing bad output instantly. |
| View users / readings / payments | Support + audit; inspect a user's state, a specific reading, payment status | MEDIUM | Read views; respect privacy (sensitive questions). |
| View generation logs / errors | Diagnose model failures, latency, token usage; review reported answers (TZ §13.16, §25.4) | LOW-MEDIUM | Closes the safety loop with the "report answer" feature. |

---

## Analytics / Instrumentation (Cross-Cutting)

Not user-facing, but required from day 1 to know whether the core hypothesis ("different deck feels different → retention + willingness to pay") is true. Event set + metrics are specified (TZ §26).

- **Funnel events:** app_opened → onboarding_* → question_entered → topic/deck/spread_selected → reading_started/completed/failed → card_revealed → summary_viewed → paywall_viewed → product_clicked → payment_started/success/failed → subscription_started (TZ §26.1).
- **Core metrics:** DAU/WAU, retention D1/D7, readings/user, completion rate, free-limit-reached rate, paywall conversion, payment conversion, ARPPU, popular decks/spreads/topics, generation error rate + latency (TZ §26.2).
- **Complexity:** LOW-MEDIUM. A single `app_events` table + emit calls. The differentiator validation specifically needs `deck_selected` distribution and per-deck retention.

---

## Feature Dependencies

```
Telegram Auth (initData validation)
    └──requires──> nothing (root)
        ├──enables──> Profile / Settings
        ├──enables──> Limits (free weekly + paid balance)
        └──enables──> Reading flow

Decks/Cards/Spreads seed data + APIs
    └──requires──> DB schema + Admin (to populate/curate)
        └──enables──> Main-screen selection UX

Reading generation (CORE)
    ├──requires──> Auth
    ├──requires──> Decks/Cards/Spreads data
    ├──requires──> Card-draw service (server-side secure random)
    ├──requires──> Prompt engine + LLMService (per-deck modifiers)
    ├──requires──> Safety classifier  ← MUST gate before answer is committed
    └──requires──> Limit check (consume only on success)
        ├──enables──> Ritual reveal animation (reveals pre-generated result)
        ├──enables──> Reading history (persisted reading)
        ├──enables──> Share-card (themed export of a completed reading)
        └──enables──> Summary synthesis

Payments (Telegram Stars)
    ├──requires──> Auth (user identity)
    ├──requires──> Limits (what to top up / what entitlement to grant)
    └──requires──> Products catalog (admin-managed)
        └──enables──> Paid balance / subscription entitlement

Per-deck differentiator (CORE VALUE)
    ├──requires──> Prompt modifiers (data) + deck_card modifiers
    ├──requires──> Per-deck theming (visual_style)
    └──enhances──> Reading generation, Ritual reveal, Share-card

Admin panel
    ├──requires──> Auth (admin allowlist)
    └──enables──> Decks/Cards/Spreads/Prompts/Products content → which all of the above depend on

Analytics ──instruments──> every flow (orthogonal, build alongside)
Safety classifier ──gates──> Reading generation (cannot be bolted on after)
```

### Dependency Notes

- **Payments depend on Auth + Limits + Products:** you cannot grant or top up access without a user identity, a limit ledger to credit, and a product to sell. Build Limits before Payments (TZ stages 7 → 8 confirm this ordering).
- **Ritual reveal depends on Reading generation:** the spec generates the full reading server-side first, then the client *reveals progressively* (TZ §12.3). The animation is a presentation layer over already-complete data — do not couple reveal pacing to live LLM streaming.
- **Safety classifier gates Reading generation (not after):** it must run before the answer is finalized/persisted; retrofitting safety post-launch is the classic divination-app failure. Folding it into the single structured call keeps it cheap (PROJECT.md edits #1/#3).
- **Admin enables everything content-driven:** decks, card meanings, prompts, and products are data the user flows read. Even a thin admin (or robust seed scripts) must exist before content can be curated — the differentiator is literally edited here.
- **The per-deck differentiator spans three subsystems:** prompt layer + theming layer + (later) art assets. The roadmap should treat "6 decks that genuinely feel different" as an acceptance criterion that cuts across generation, theming, and reveal — not a single ticket.
- **Limit consumption couples to generation success:** decrement only when a reading is successfully created (TZ §14.5, §29.2) — otherwise users are charged for failures and trust collapses.

---

## MVP Definition

### Launch With (v1) — matches TZ §24.1 / §30

- [ ] Telegram auth (initData validation, no registration) — root of everything; the "fast first impression" thesis
- [ ] Skippable onboarding (3–4 screens, reversed-card explainer, "not a verdict" framing) — trust + expectation-setting
- [ ] Main flow: question → topic → deck → spread → recommendation → start — the product's spine
- [ ] **6 decks with distinct prompt modifiers + theming** — THE core value; non-negotiable
- [ ] 7 spreads (3–4 cards) + topic-based recommendation
- [ ] Server-side secure card draw + 70/30 reversed mechanic (toggleable)
- [ ] Ritual prep + one-by-one reveal animation — anti-"AI chat" lever
- [ ] Per-card interpretation + overall summary (single structured LLM call)
- [ ] **Safety classifier + crisis handling + no-categorical-predictions + disclaimers** — duty-of-care, mandatory
- [ ] Reading history (list / detail / soft-delete)
- [ ] Free weekly limit (3/week) + honest soft paywall
- [ ] Telegram Stars: 1/3/10 packs + subscription; invoice→pre_checkout→successful_payment→grant; refunds; idempotency
- [ ] Profile + settings (balance, subscription, reversals toggle, history-personalization consent)
- [ ] Share-card (privacy-safe, question hidden by default)
- [ ] Admin panel (dashboard, CRUD decks/cards/spreads/prompts/products, toggles, view users/readings/payments/gen-logs)
- [ ] Analytics events + core metrics

### Add After Validation (v1.x)

- [ ] Region-aware crisis resources — trigger: real crisis-classified traffic observed
- [ ] "Report this answer" UI surfaced prominently — trigger: any harmful-output incident
- [ ] Native recurring Stars subscription — trigger: Stars subscription API confirmed stable for the use case (else manual 30-day entitlement per PROJECT.md edit #7)
- [ ] Bundle/discount pricing experiments (3-for-2 framing lifts AOV 35–50% per market data) — trigger: baseline conversion measured
- [ ] User rating of a reading (thumbs) — trigger: need to quantify "answers too generic" risk (TZ §25.2)
- [ ] Bespoke per-deck card illustrations (trickling in via admin) — trigger: art production capacity; code already supports slots

### Future Consideration (v2+) — TZ §24.2

- [ ] Premium / seasonal / limited / subscriber-only decks — defer: post-MVP monetization layer
- [ ] Push "card of the day" — defer: notification UX + opt-in management after loop is proven
- [ ] 5–7 card deep spreads — defer: more generation cost/complexity
- [ ] Voice fortune-teller, post-reading chat — defer: high cost, risks the "ritual not chat" positioning
- [ ] Cross-reading personal dynamics / memory — defer: privacy + storage complexity, needs explicit consent
- [ ] Referral program, Telegram Stories sharing, PDF export, A/B paywall framework, visual-theme editor, deck marketplace, multilanguage — defer: all post-PMF

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 6 decks w/ distinct prompt modifiers + theming (CORE) | HIGH | HIGH | P1 |
| Telegram auth (frictionless) | HIGH | LOW | P1 |
| Main selection flow (question/topic/deck/spread) | HIGH | MEDIUM | P1 |
| Per-card interpretation + summary (1 LLM call) | HIGH | MEDIUM | P1 |
| Safety classifier + crisis handling + disclaimers | HIGH | MEDIUM | P1 |
| Server-side card draw + reversed mechanic | HIGH | LOW | P1 |
| Ritual reveal animation | HIGH | MEDIUM | P1 |
| Reading history | HIGH | MEDIUM | P1 |
| Free limit + soft paywall | HIGH | MEDIUM | P1 |
| Telegram Stars payments (packs + sub) | HIGH | HIGH | P1 |
| Admin (decks/cards/spreads/prompts/products + toggles) | HIGH (ops) | MEDIUM | P1 |
| Analytics events + metrics | MEDIUM (HIGH for validation) | LOW-MEDIUM | P1 |
| Onboarding | MEDIUM | LOW | P1 |
| Profile + settings | MEDIUM | LOW | P1 |
| Share-card (privacy-safe) | MEDIUM | MEDIUM | P2 |
| Topic→deck→spread compatibility guidance | MEDIUM | LOW-MEDIUM | P2 |
| "Report answer" UI | MEDIUM (safety) | LOW | P2 |
| Reading rating (thumbs) | MEDIUM | LOW | P2 |
| Region-aware crisis resources | MEDIUM | MEDIUM | P2 |
| Bespoke card art (via admin) | MEDIUM | HIGH (content) | P2 |
| Push card-of-the-day | MEDIUM | MEDIUM | P3 |
| Premium/seasonal decks | MEDIUM | MEDIUM | P3 |
| Voice / post-reading chat / deep spreads | LOW-MEDIUM | HIGH | P3 |
| Referral / marketplace / PDF / multilang | LOW | HIGH | P3 |

**Priority key:** P1 = must have for launch · P2 = should have, add when possible · P3 = future.

---

## Competitor Feature Analysis

| Feature | Co-Star (astrology) | Labyrinthos / Tarotoo / Aura (tarot) | Our Approach |
|---------|---------------------|--------------------------------------|--------------|
| Daily card / horoscope | Daily hyper-personalized horoscope; "Void" Q&A | Card-of-the-day is the core retention hook | Day-spread in-app now; push deferred |
| Upright + reversed meanings | n/a | Full 78-card upright+reversed dictionaries | Same, but woven into per-deck voice, not a static dictionary |
| Multiple decks | n/a | Usually ONE deck (often Rider-Waite-style) | **6 decks that change tone+art+structure for the same question — our wedge** |
| AI interpretation | "Void" credits, AI answers (overtly AI) | Some "AI psychic chat" (overtly AI) | LLM concealed; speaks *as the deck*, never "AI" |
| Monetization | Freemium; a-la-carte IAP (add friends, advanced charts); free first Void then credits | Freemium + subscription + IAP | Free weekly limit + Stars packs (1/3/10) + subscription; soft, non-fear paywall |
| Onboarding personalization | Birth date/time/place natal chart | Light or none | Light + skippable; personalization is opt-in |
| Social | Friend charts, compatibility | Mostly solo | Deliberately solo + privacy-safe share-card (anti-feature: feed/profiles) |
| Safety framing | Entertainment | Entertainment disclaimers | First-class classifier + crisis routing + disclaimers (stronger than typical apps) |
| Platform | Native iOS/Android | Native | Telegram mini app (web-first) — zero install, native Stars payments |

**Reading of the field:** the market is crowded with single-voice tarot apps and overtly-AI "psychic chat." Two things are genuinely scarce and defensible here: (1) **multiple decks that meaningfully change the SAME answer**, and (2) **AI concealed inside a ritual** rather than sold as "AI tarot." Co-Star proves freemium a-la-carte IAP works for this audience; Telegram Stars is the native analogue. Weekly subscriptions reportedly convert ~5.4× annual in this space — favor the short cycle.

---

## Sources

- Tarot/oracle app feature baselines: [Labyrinthos (Google Play)](https://play.google.com/store/apps/details?id=com.labyrinthos.app&hl=en_US), [Tarot – Daily Card Reading (App Store)](https://apps.apple.com/us/app/tarot-daily-card-reading/id1611588287), [Daily Tarot Aura (App Store)](https://apps.apple.com/us/app/daily-tarot-card-reading-aura/id1444277220), [Tarotoo (App Store)](https://apps.apple.com/us/app/tarot-card-reading-tarotoo/id6736652947), [Labyrinthos review – Bustle](https://www.bustle.com/life/labyrinthos-tarot-reading-app-review) — confidence HIGH
- Astrology-app monetization (freemium / a-la-carte IAP): [Co-Star](https://www.costarastrology.com/), [Co-Star – Wikipedia](https://en.wikipedia.org/wiki/Co%E2%80%93Star), [How Astrology Apps Make Money – JPLoft](https://www.jploft.com/blog/how-astrology-apps-make-money) — confidence HIGH
- Telegram Stars monetization patterns (consumables, subscriptions, soft paywall, bundle uplift, weekly>annual conversion): [Merge – TMA 2026 monetization guide](https://merge.rocks/blog/telegram-mini-apps-2026-monetization-guide-how-to-earn-from-telegram-mini-apps), [OmiSoft](https://omisoft.net/gb/blog/how-to-monetize-telegram-mini-app/), [Nadcab](https://www.nadcab.com/blog/telegram-mini-apps-monetization) — confidence MEDIUM (vendor blogs; directionally consistent)
- Telegram Stars payment mechanics (invoice/pre_checkout/successful_payment, refundStarPayment, subscription_period, idempotency by charge_id): [Telegram Bot Payments – Stars (official)](https://core.telegram.org/bots/payments-stars), [Star subscriptions (official)](https://core.telegram.org/api/subscriptions), [Bot API changelog (official)](https://core.telegram.org/bots/api-changelog) — confidence HIGH
- Tarot ethics / safety / disclaimers (entertainment-only, not-a-substitute, crisis routing, take mental-health disclosures seriously): [Tarot Ethics with AI – aimag.me](https://aimag.me/blog/tarot-ethics-and-responsibility), [Ethics & Safety for Tarot Online – tarotyesno](https://tarotyesno.com/ethics-and-safety/), [Magick Makers ethics statement](https://themagickmakers.com/tarot-policies-ethics-statement) — confidence HIGH
- Deck "personality" / same-cards-feel-different validation: [Do Tarot Decks Have Different Personalities? – Lightwands](https://lightwands.org/blog/tarot-deck-personalities) — confidence MEDIUM
- Primary spec: `REFERENCE-TZ.md` (§2 scope, §3 stories, §4 decks, §6 spreads, §8 reversed, §9 UX, §10 wow, §11 monetization, §20 safety, §22 admin, §26 analytics, §24/§30 MVP) and `PROJECT.md` (Core Value, Out of Scope, edits #1–#7) — confidence HIGH (source of truth)

---
*Feature research for: Telegram Mini App tarot/oracle ritual with concealed-AI interpretation and Stars monetization*
*Researched: 2026-06-09*
