# Phase 5: History & Profile - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-13
**Phase:** 5-history-profile
**Areas discussed:** History list, Soft delete & free-10 retention, Personalization opt-in, Profile/Settings, Navigation

---

## History list

### Pagination (free ≤10 readings, more with subscription)?
| Option | Description | Selected |
|--------|-------------|----------|
| «Показать ещё» (load-more) | Button; API paginates (limit/offset). Simple for a small list, scales. | ✓ |
| Infinite scroll | useInfiniteQuery + IntersectionObserver. Overkill for ≤10, more code. | |
| Pages | Numbered pages. Unusual in a mini app. | |

### Filters in the MVP list?
| Option | Description | Selected |
|--------|-------------|----------|
| No, chronological | Reverse-chronological; API keeps topic/deck params for later. | ✓ |
| Yes, topic + deck | Filter chips (HIST-02). Useful only with large history. | |
| Search only | Full-text on question. Extra complexity, not for MVP. | |

### Reopening a past reading?
| Option | Description | Selected |
|--------|-------------|----------|
| Straight to result | Static ResultScreen, cards already open, no ritual/reveal. | |
| Light fade-in | Straight to result, cards softly stagger-in (opacity). | ✓ |
| Replay reveal | Full flip animation again. Atmospheric but slow each time. | |

**User's choice:** load-more / no filters (chronological) / light fade-in.

---

## Soft delete & free-10 retention

### Confirmation on delete?
| Option | Description | Selected |
|--------|-------------|----------|
| Undo snackbar | Delete immediately + Отменить ~5s; soft-delete makes undo trivial. | ✓ |
| Confirm dialog | «Удалить расклад?» yes/no. Familiar but extra step. | |
| Immediate, no undo | Silent delete. Risk of accidental loss. | |

### Where does delete live?
| Option | Description | Selected |
|--------|-------------|----------|
| Button in detail | «Удалить» inside the detail view. Simple, explicit, no gestures. | |
| Swipe in list | swipe-to-delete on the list card. Mobile-native, more touch code. | ✓ |
| Both | Swipe + button. More code. | |

### What does "free last 10" (HIST-06) mean technically?
| Option | Description | Selected |
|--------|-------------|----------|
| Hide beyond 10, retain data | List shows last 10; older stay in DB (subscription reveals later). Reversible. | ✓ |
| Hard-prune beyond 10 | Older-than-10 actually deleted (irreversible). | |
| No cap in MVP | Show everything, defer the 10-limit. Violates HIST-06. | |

**User's choice:** undo snackbar / swipe-to-delete / hide-beyond-10-retain-data.

---

## Personalization opt-in

### How is the opt-in presented?
| Option | Description | Selected |
|--------|-------------|----------|
| Toggle + explanation | Settings toggle, default OFF, plain explanation + privacy note. Explicit (ТЗ §2.2). | ✓ |
| One-time prompt | Ask once after a few readings. Pushier; risk of accidental consent. | |
| Toggle, no explanation | Just a switch. Opaque for privacy. | |

### Does Phase 5 build the personalization, or just consent + gate?
| Option | Description | Selected |
|--------|-------------|----------|
| Flag + gate, toggle visible | Store consent + GUARANTEE history isn't fed to the §18 prompt without it (HIST-05). Real "повторный анализ" = v2 (ENG-02). Clean scope. | ✓ |
| Full personalization | Build history_context + feed into §18 when ON. Scope creep into a v2 feature. | |
| Gate + stub | Flag + wiring present but empty/minimal. | |

**User's choice:** toggle + explanation (default OFF) / flag + gate only (real personalization = v2).

---

## Profile / Settings

### What's on the profile screen in MVP?
| Option | Description | Selected |
|--------|-------------|----------|
| Name/avatar + settings | Telegram name + photo + toggles. Minimal, clean. | ✓ |
| + stats | Also readings-done / favorite deck. More work; overlaps Phase 8 analytics. | |
| Settings only | No profile header. Dry. | |

### "Available readings" + subscription when limits/payments aren't built (Phase 6/7)?
| Option | Description | Selected |
|--------|-------------|----------|
| Hide until Phase 6/7 | Profile = identity + settings; count/subscription block added when numbers are real. API may return fields, UI hides. | ✓ |
| Real user_limits read | Read free_used_this_week. But without the weekly reset (Phase 6) the count is wrong after a week. | |
| Neutral badge | Show «бесплатный» without numbers. Honest but half-empty. | |

**User's choice:** name/avatar + settings / hide count+subscription until Phase 6/7.

---

## Navigation

### How to reach History/Profile (app is an immersive flow-stepper)?
| Option | Description | Selected |
|--------|-------------|----------|
| Icons in Home header | Profile + history icons in the selection-screen atmospheric header (§9.2); ritual/reveal/result stay chrome-free; «история» from result also routes there. | ✓ |
| Bottom tab bar | Persistent Главная/История/Профиль tabs. Discoverable but fights the immersive ritual + sticky CTA. | |
| Only from result + menu | History from result, profile via menu/icon. Less discoverable. | |

### Back from History/Profile/detail?
| Option | Description | Selected |
|--------|-------------|----------|
| In-app button → Home | Consistent with Phase 3 D-03 (in-app, not Telegram native). History/Profile → Home; detail → History. | ✓ |
| Telegram BackButton | Native. Reverses the Phase-3 decision. | |
| Swipe back | Gesture. Extra code, may conflict with horizontal carousels. | |

**User's choice:** icons in Home header / in-app back button → Home.

---

## Claude's Discretion

- Empty-history copy (§9.6) + settings/personalization explainer copy (brand-voice clean).
- History/Profile as new `step` values vs a light route layer — planner, constrained by D-02/D-10/D-11.
- "Last 10" note wording (or none).
- History list-item layout (§9.6 / HIST-02) — reuse card/CardArtFallback patterns.
- Dedicated history/profile service vs extend ReadingService/users router.

## Deferred Ideas

- Real history-based personalization / повторный анализ — v2 (ENG-02).
- Subscription/extended-history reveal + readings-count block — Phase 6 / Phase 7.
- History filters / search — when history grows large (subscription).
- Profile stats — Phase 8 (admin/analytics).
- Share-card / «сохранить карточку» — Phase 8.
- Telegram native BackButton — chose in-app back.
