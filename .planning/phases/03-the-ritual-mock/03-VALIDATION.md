---
phase: 3
slug: the-ritual-mock
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Phase 3 is a front-end mock: most success criteria are inherently visual/live (animation feel, Telegram-client theming, haptics) and route to manual acceptance. Automatable surface = pure logic: question validation, reversals draw, the schema-faithful mock builder, and component render assertions.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest + React Testing Library (already configured in Phase 2) |
| **Config file** | `frontend/vite.config.ts` (test block) |
| **Quick run command** | `cd frontend && npm run test -- --run` |
| **Full suite command** | `cd frontend && npm run test -- --run && npm run build` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npm run test -- --run`
- **After every plan wave:** Run full suite (`npm run test -- --run && npm run build`)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~30 seconds

---

## Per-Task Verification Map

> Planner fills concrete rows per task. Automatable units below; visual/feel items go to Manual-Only.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 3-xx-xx | xx | 1 | HOME-01/02 | T-3-01 | Question is length-validated (10–500, empty allowed) and rendered as text, never HTML | unit | `npm run test -- --run` | ❌ W0 | ⬜ pending |
| 3-xx-xx | xx | 1 | READ-08/D-07 | — | Reversals draw: off→all upright, on→~70/30 (deterministic via seedable RNG in test) | unit | `npm run test -- --run` | ❌ W0 | ⬜ pending |
| 3-xx-xx | xx | 2 | READ-09/D-05 | — | `createReading()` returns MockReading matching READ-05/06 shape (cards[] + summary fields) | unit | `npm run test -- --run` | ❌ W0 | ⬜ pending |
| 3-xx-xx | xx | 2 | ONB-04/D-11 | — | onboarding_completed persists to localStorage; onboarding not re-shown once set | unit | `npm run test -- --run` | ❌ W0 | ⬜ pending |
| 3-xx-xx | xx | 2 | SAFE-06 | — | No banned brand-voice strings (AI/нейросеть/модель/сгенерировано) in rendered copy | unit | `npm run test -- --run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Vitest + RTL already installed (Phase 2) — no framework install needed
- [ ] `frontend/src/test/renderWithClient.tsx` shared harness exists (Phase 2) — reuse
- [ ] New fixtures: mock card-pool fixture + `createReading()` test, question-validation test, reversals-draw test (seedable RNG)

*Existing infrastructure covers the framework; new tests are per-plan.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Transitions feel smooth, no jank, no abrupt pop-in, fast load | D-01 / UI-01 / UI-03 | Perceived-quality judgment; not assertable from DOM | Run `npm run dev` in Telegram, walk onboarding→selection→ritual→reveal→result; confirm crossfades are continuous, no layout shift, no stutter on a mid/low device |
| Ritual prep ~3s timeline + completion haptic | READ-07 / D-08 | Timing feel + native haptic only fire in the Telegram client | On device: tap «Начать расклад», observe 3 beats + dimming + particles, feel haptic at completion, confirm tap-to-skip after first beat |
| Tap-to-flip reveal + «раскрыть все» feel | READ-08 / D-09 | Flip choreography is a visual/feel judgment | Reveal cards one-by-one, then «раскрыть все»; confirm stagger reads as ritual, not abrupt |
| Telegram light/dark theme + safe-area insets | UI-04 | Requires real Telegram WebView (SDK insets, not env()) | Open in Telegram on a notched device, toggle app theme; confirm colors adapt and content respects safe-area top/bottom |
| Per-deck theme carries into ritual/reveal/result | UI-02 (carry) / D-08 | Visual continuity judgment | Pick different decks; confirm ritual/reveal/result backgrounds + accents match the deck palette |
| Sticky bottom CTA not obscured by iOS keyboard | UI-01 / HOME-07 | Mobile WebView keyboard overlap (research pitfall) | Focus the question field on iOS; confirm «Начать расклад» stays reachable |

---

## Validation Sign-Off

- [ ] All automatable tasks have a unit test or Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive automatable tasks without a verify
- [ ] Visual/feel/Telegram-client items recorded as Manual-Only (route to HUMAN-UAT at verify)
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter (after planner fills per-task map)

**Approval:** pending
