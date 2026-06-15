# Phase 6: Free Limits & Soft Paywall - Discussion Log

> **Audit trail only.** Not consumed by downstream agents — decisions are in CONTEXT.md; this preserves the alternatives considered.

**Date:** 2026-06-14
**Phase:** 6-free-limits-soft-paywall
**Areas discussed:** Weekly reset, Paywall surface, Bucket order, Throttle, Remaining-count surfacing

---

## Weekly reset

### Reset anchor?
| Option | Description | Selected |
|--------|-------------|----------|
| ISO week Mon UTC | week_start = Monday 00:00 UTC, everyone resets Monday. Deterministic, matches criterion-2 literal. Friday-starter waits to Mon. | |
| Per-user rolling 7d | week_start = first reading of the window; reset 7 days later. Fairer per-user, less predictable. | ✓ |
| Anchor from signup | week_start from user created_at, +7d cycles. | |

### New user with no user_limits row (Phase 4 = unlimited gap)?
| Option | Description | Selected |
|--------|-------------|----------|
| Row at auth | Create user_limits at user upsert, default 3/week. Every authed user has a row, no edge. | ✓ |
| Lazy at 1st reading | Create on first POST /api/readings. | |
| No-row = 0 quota | Missing row → exhausted (forces creation). Risk: new user blocked. | |

**User's choice:** per-user rolling 7d (overrides criterion-2 "ISO week") / row at auth.

---

## Paywall surface (payments = Phase 7)

### What to show on exhaustion?
| Option | Description | Selected |
|--------|-------------|----------|
| Limit + reset + «скоро» | "закончились, вернутся через N" + soft "скоро можно открыть ещё". No tariffs/dead buttons. Phase 7 swaps «скоро» for tariffs. | ✓ |
| Tariffs + stubbed «купить» | Show 1/3/10 + subscription, buy disabled until Phase 7. Dead buttons. | |
| Only limit + reset | Just "limit exhausted, back in N", no purchase mention. | |

### Show reset countdown?
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, days/date | "через 2 дня" / "обновятся 16 июня". Honest; important under per-user rolling. | ✓ |
| No | Just "limit exhausted". | |

### Paywall form?
| Option | Description | Selected |
|--------|-------------|----------|
| Inline/sheet on selection | Paywall as sheet/inline where «Начать расклад» blocked. Contextual, minimal; full tariffs screen = Phase 7. | ✓ |
| Dedicated tariffs screen | Navigate to a paywall screen (TZ §9.7). More structure, empty without payments. | |
| Bottom-sheet modal | Modal sheet over selection. | |

**User's choice:** limit+reset+«скоро» / countdown yes / inline-sheet on selection.

---

## Bucket order

### Consumption order when multiple buckets exist (logic built now, only free live)?
| Option | Description | Selected |
|--------|-------------|----------|
| Free→subscription→paid | Spend expiring buckets first (free weekly, subscription periodic), preserve permanent paid balance. Max user value. Seam built now, P7 fills paid/sub. | ✓ |
| Free→paid→subscription | free, then one-time packs, subscription last. Risk: burn permanent paid before expiring subscription. | |
| Only free now | Build only free check; defer full order to Phase 7. But criterion-5 wants the determine-access seam. | |

**User's choice:** free → subscription → paid.

---

## Throttle

### Redis throttle aggressiveness (anti-burst)?
| Option | Description | Selected |
|--------|-------------|----------|
| Moderate ~1/10-15s + burst-cap | 1 reading / ~10-15s + ≤5/min. Cuts rapid-fire/double-submit before Postgres/LLM; real user never hit. | ✓ |
| Strict 1/30-60s | Tighter, may annoy a user wanting a couple back-to-back. | |
| Anti-double only ~3-5s | Just debounce accidental double-taps. | |

### Message: throttle vs limit-exhaustion?
| Option | Description | Selected |
|--------|-------------|----------|
| Distinct | Throttle: soft transient "переведи дыхание" (429); limit: paywall "вернутся через N". Different states → different copy. | ✓ |
| One shared | Both → generic "try later". Simpler but confuses transient throttle with weekly exhaustion. | |

**User's choice:** moderate ~1/10-15s + burst-cap / distinct messages.

---

## Remaining-count surfacing

### Where to show "осталось N" (before exhaustion)?
| Option | Description | Selected |
|--------|-------------|----------|
| Selection + profile | Subtle "N из 3" near «Начать расклад» + un-hide the Phase-5 D-08 profile block. Honest expectation, no surprise block. | ✓ |
| Profile only | Count only in profile, not selection. | |
| Don't show | No count until blocked. Minimal but abrupt. | |

### Prominence?
| Option | Description | Selected |
|--------|-------------|----------|
| Subtle always + last-one hint | "N из 3" always + gentle "последний на этой неделе" when 1 left. Leads gracefully into paywall, no pressure. | ✓ |
| Subtle always | Just "N из 3", no special last-one hint. | |
| Only when low | Show only when 1 left. | |

**User's choice:** selection + profile / subtle always + last-one hint.

---

## Claude's Discretion

- Exact reset/throttle/paywall/count copy (TZ §9.8 + §11.2, brand-safe via copy.ts).
- Atomicity mechanism for check+decrement (SELECT FOR UPDATE vs atomic UPDATE…WHERE…RETURNING) — research/planner.
- Exact throttle window/burst-cap numbers within the moderate band; INCR+EXPIRE key shape.
- Lazy-reset placement; dedicated LimitService vs extend ReadingService seam.
- Redis count cache vs always-read-PG (PG authoritative).

## Deferred Ideas

- Telegram Stars purchase flow + tariffs screen + populating paid/subscription buckets — Phase 7.
- Dedicated full paywall/tariffs screen — Phase 7.
- Heavier anti-abuse (per-IP, CAPTCHA) — out of MVP.
- Redis count cache as read path — optional optimization.
