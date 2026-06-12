# Phase 4: Real Personal Reading (KEYSTONE) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-12
**Phase:** 4-real-personal-reading-keystone
**Areas discussed:** Per-deck divergence, Crisis & sensitive safety, Generation wait & failure, Reading depth & length, Additional edges (abusive / Sonnet / reversals / language)

---

## Per-deck divergence (Core Value)

### How differently do the 6 decks answer the same question?
| Option | Description | Selected |
|--------|-------------|----------|
| Tone + focus | Deck changes tone/imagery AND what it concentrates on (Тени→hidden, Сердце→feelings, Лесной→nature cycle). Strong wow at a stable JSON schema. | ✓ |
| Tone/accent only | One meaning skeleton, deck changes only words/mystical accent. Cheaper/steadier but Core Value weaker. | |
| Tone + focus + structure | Plus deck reshapes the summary/advice (order, length, form). Max difference but uneven length/format, harder validation. | |

### Does each deck need a recognizable "signature"?
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, signature | Each deck has a mandatory device (Лесной→always a nature metaphor; Тени→always names hidden tension). Difference guaranteed even on similar questions. | ✓ |
| No, emergent | Difference arises from the prompt_modifier naturally; risks being unnoticeable on short answers. | |

**User's choice:** Tone + focus; mandatory signature per deck.
**Notes:** Length stays uniform (see depth area) — divergence is content/focus, not volume.

---

## Crisis & sensitive safety

### Crisis (self-harm / violence) — what tone?
| Option | Description | Selected |
|--------|-------------|----------|
| Break the mystical frame | Oracle goes silent; warm human tone, no cards, no prediction; support. Honest & responsible. | ✓ |
| Gentle in-character | Oracle voice kept but no prediction; steers away from mysticism toward a real person. | |
| Hybrid | Short exit from ritual + warm message, keeps brand softness. | |

### Which resources in the crisis response?
| Option | Description | Selected |
|--------|-------------|----------|
| Concrete RU services | Real RU hotlines (8-800-2000-122, 112) in the refusal template. | |
| Generic wording | "близкий человек / специалист", no specific numbers. Less risk of inaccuracy. | ✓ |
| Minimal set | One or two verified contacts only. | |

### Sensitive (non-crisis) — how visible is the softening?
| Option | Description | Selected |
|--------|-------------|----------|
| Silent, softer tone | safety_modifier in prompt, text just gentler, no visible badges. Keeps immersion. | ✓ |
| Visible care-note | A soft visible reminder ("подсказка, не диагноз/приговор") in the answer. | |
| Hybrid | Silent softening + one short care line for the most sensitive (health/legal/fin). | |

**User's choice:** Break frame (warm human) / generic resources / silent softening.
**Notes:** Generic resources chosen deliberately over concrete RU numbers to avoid stale/incorrect data in MVP.

---

## Generation wait & failure

### How do we cover the real LLM call time (ritual ~3s, Haiku ~2–6s)?
| Option | Description | Selected |
|--------|-------------|----------|
| Ritual covers it | Call fires on «Начать расклад», ritual plays during wait, reveal only when JSON ready, last beat holds if slow. No spinner. | ✓ |
| Ritual + extra beat | If not ready, add another atmospheric beat instead of freezing the frame. | |
| Separate loading | Fixed ~3s ritual then an explicit "колода читает…" state. Simpler but visible pause. | |

### What does «колода замолчала» offer on failure (after 1 retry)? (multi)
| Option | Description | Selected |
|--------|-------------|----------|
| Retry | Re-run the same reading; limit not consumed → free. | ✓ |
| Switch deck | Back to selection with question preserved (like Phase 3 D-04). | ✓ |
| Just back | Close error, return to selection with no action. | |

### DB-fallback on total generation failure — what is it?
| Option | Description | Selected |
|--------|-------------|----------|
| Honest fail | reading=failed, soft error, limit NOT consumed, no reading. Matches READ-04, protects core. | ✓ |
| Templated reading | Assemble from base card meanings without LLM so the user gets something. Risks feeling cheap/non-personal. | |
| Hybrid | Show cards + base meanings as a "draft" with an honest note; limit not consumed. | |

**User's choice:** Ritual covers it / Retry + Switch deck / Honest fail.
**Notes:** "Honest fail" resolves the PROJECT.md tension between "DB-fallback" and "reading=failed."

---

## Reading depth & length

### Depth / length of the reading text?
| Option | Description | Selected |
|--------|-------------|----------|
| Short / atmospheric | short_meaning ~1 line, interpretation 2–3 phrases, tight summary. Fast/cheap, mobile, "less dry text, more atmosphere." | ✓ |
| Medium | interpretation ~3–4 phrases, fuller summary. Balance. | |
| Richer | interpretation ~paragraph, full summary. Deeper but longer + more tokens/latency. | |

### Uniform length across decks or varied?
| Option | Description | Selected |
|--------|-------------|----------|
| Uniform | Even format across all 6; difference via tone/focus/signature, not volume. Predictable layout/cost. | ✓ |
| Deep decks longer | Тени/Лесной a bit more text, light decks shorter. More character but uneven layout/cost. | |

**User's choice:** Short / atmospheric, uniform across all decks.

---

## Additional edges

### Abusive / trolling / junk question (not crisis) — what does the oracle do?
| Option | Description | Selected |
|--------|-------------|----------|
| Gentle redirect | "колода молчит на это, задай вопрос от сердца." No reading, limit not consumed. | ✓ |
| Answers atmospherically | Treats as normal, answers evasively-prettily. Risks encouraging trolling, wastes tokens/limit. | |
| Refuse + don't consume | Short neutral refusal, limit kept. | |

### When does Sonnet kick in for MVP (no premium tier yet)?
| Option | Description | Selected |
|--------|-------------|----------|
| Retry on Sonnet | Haiku default; corrective retry on invalid JSON goes to Sonnet. Matches CLAUDE.md. | ✓ |
| Always Haiku | Retry also on Haiku; Sonnet unused in MVP. | |
| Deep decks on Sonnet | Тени/Лесной always Sonnet. Pricier, contradicts "short/uniform" — post-MVP. | |

### Reversals default for a new user (settings persist only in Phase 5)?
| Option | Description | Selected |
|--------|-------------|----------|
| On, 70/30 | Model default reversals_enabled=True; ONB-03 already explains reversed; richer experience. | ✓ |
| Off by default | All upright, softer for a newcomer. | |
| Ask in onboarding | Explicit choice at start — extra step, against "fast first impression." | |

### If the question isn't in Russian — what language is the answer?
| Option | Description | Selected |
|--------|-------------|----------|
| Always Russian | Russian-language product; reading always in Russian. Simpler for safety/prompt. | ✓ |
| Mirror question language | Answer in the question's language. Harder for safety classification, audience is RU. | |
| Russian + soft nudge | Answer in Russian and gently suggest asking in Russian. | |

**User's choice:** Gentle redirect / Retry on Sonnet / On 70/30 / Always Russian.

---

## Claude's Discretion

- Safety-classifier **mechanism** (separate classify call vs regex pre-filter + structured-output safety field vs in-call) — open research question; product invariant (crisis short-circuits before draw/charge) is locked.
- **Single-call JSON schema design** merging §17 (per-card) + §18 (summary) into one `messages.parse` object and mapping onto the DB schema — planner/research.
- Concrete per-deck signature texts, `safety_modifier` text, `refusal` copy — derived from TZ §16/§17/§18/§19/§20.3 + §9.8.
- Exact retry/timeout timings and temperature — planner.

## Deferred Ideas

- Concrete regional crisis hotline numbers (chose generic for MVP).
- Per-deck / premium-tier model escalation (post-MVP).
- Visible sensitive-topic disclaimer UI (chose silent softening).
- History-based personalization (Phase 5).
- Weekly-limit reset / buckets / Redis throttle (Phase 6).
- `app_events` reading_* analytics (Phase 8).
- Reduced-motion fallback (still deferred from Phase 3).
