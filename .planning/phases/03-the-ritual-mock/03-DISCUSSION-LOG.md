# Phase 3: The Ritual (mock) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-11
**Phase:** 03-the-ritual-mock
**Areas discussed:** Поток и навигация, Данные mock-расклада, Контракт анимаций

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Поток и навигация | state-machine vs router vs стек; «Назад»; пересъёмка | ✓ |
| Данные mock-расклада | фикстура vs генерация vs schema-faithful; пул карт; reversals | ✓ |
| Контракт анимаций | ритуал-подготовка + reveal + reduced-motion | ✓ |
| Границы заглушек | onboarding persist, save-card/история, пустой вопрос | (not selected — sensible defaults locked) |

---

## Поток и навигация

**Q1 — Чем рулим переходами?**

| Option | Description | Selected |
|--------|-------------|----------|
| State-machine в Zustand | один контейнер по полю step; без новой зависимости | (interpreted as chosen) |
| react-router | URL на каждый шаг; лишняя зависимость, рывки истории | |
| Стек экранов вручную | push/pop массив; гибко, больше кода | |

**User's choice:** Free-text — *"Мне главное, чтобы все действия и анимации были очень плавными, без рывков, без просто появления и при этом все должно быстро грузится."*
**Notes:** User did not pick a mechanism; set a non-functional bar (smoothness + fast load) and delegated the mechanism. Interpreted → Zustand state-machine + `motion` AnimatePresence (D-02), react-router rejected. Smoothness captured as governing NFR D-01.

**Q2 — Как работает «Назад»?**

| Option | Description | Selected |
|--------|-------------|----------|
| Telegram BackButton | нативная кнопка управляет шагами | |
| Свои in-app кнопки | кнопка назад внутри UI на экране | ✓ |
| Оба | и нативная, и in-app | |

**User's choice:** Свои in-app кнопки (D-03).

**Q3 — Что делает «ещё расклад»?**

| Option | Description | Selected |
|--------|-------------|----------|
| К выбору, вопрос сохранён | возврат на экран выбора, вопрос/тема предзаполнены | ✓ |
| Полный сброс | чистый старт | |
| Сразу новый ритуал | пропустить выбор, та же конфигурация | |

**User's choice:** К выбору, вопрос сохранён (D-04).

---

## Данные mock-расклада

**Q1 — Насколько точно мок повторяет будущий ответ?**

| Option | Description | Selected |
|--------|-------------|----------|
| Schema-faithful под READ-05/06 | точная форма будущего POST /api/readings | ✓ |
| Простая фикстура | 1–2 захардкоженных примера | |
| Генерация из каталога | сборка из /api/decks,/api/spreads | |

**User's choice:** Schema-faithful под READ-05/06 (D-05).

**Q2 — Откуда карты для мока?**

| Option | Description | Selected |
|--------|-------------|----------|
| Bundled фикстура карт | малый клиентский JSON | ✓ |
| Новый GET /api/cards | эндпоинт базовых карт сейчас | |
| Только арт/фолбэк | без реальных названий | |

**User's choice:** Bundled фикстура карт (D-06).

**Q3 — Прямые/перевёрнутые в моке?**

| Option | Description | Selected |
|--------|-------------|----------|
| Локальный тумблер 70/30 | вкл → 70/30, выкл → all upright | ✓ |
| Всегда upright | без перевёрнутых | |
| Демо: показать оба | принудительно ≥1 перевёрнутая | |

**User's choice:** Локальный тумблер 70/30 (D-07).

---

## Контракт анимаций

**Q1 — Экран ритуал-подготовки?**

| Option | Description | Selected |
|--------|-------------|----------|
| Авто-таймлайн ~3с, tap-to-skip | три бита кроссфейдом, частицы, haptic | ✓ |
| Только по тапу | каждый бит ждёт тапа | |
| Фикс длительность, без пропуска | полный ритуал всегда | |

**User's choice:** Авто-таймлайн ~3с, tap-to-skip (D-08).

**Q2 — Раскрытие карт?**

| Option | Description | Selected |
|--------|-------------|----------|
| Tap-to-flip + «раскрыть все» | по одной тапом, потом раскрыть все | ✓ |
| Авто-стаггер | сами по очереди | |
| Все сразу | мгновенно | |

**User's choice:** Tap-to-flip + «раскрыть все» (D-09).

**Q3 — Производительность/доступность?**

| Option | Description | Selected |
|--------|-------------|----------|
| prefers-reduced-motion fallback | частицы/флип → fade при reduced-motion | |
| Полные анимации всегда | без fallback | ✓ |
| Свой тумблер «упростить» | переключатель в настройках (Phase 5) | |

**User's choice:** Полные анимации всегда (D-10).
**Notes:** Mild tension with the D-01 smoothness bar — no degraded mode means engineering must enforce compositor-only animation, 60fps budget, lazy-load + art preload. Reduced-motion accessibility recorded as a deferred tradeoff.

---

## Claude's Discretion

- Navigation mechanism (Zustand state-machine + AnimatePresence) — user delegated, set smoothness constraint.
- "Границы заглушек" area (not deep-discussed): onboarding_completed → localStorage (Phase 5 = PATCH /api/me); «сохранить карточку»/«история» present-but-stubbed; empty question → general reading; limits/paywall out of phase. (D-11..D-14)
- Onboarding screen copy/order, particle style/density, beat durations, easing, result-screen layout.

## Deferred Ideas

- prefers-reduced-motion / vestibular accessibility fallback (post-MVP).
- Real generation / safety / CSPRNG / generation_logs (Phase 4).
- History, profile & settings persistence (Phase 5).
- Share-card export (later).
- Limits, paywall, Telegram Stars (Phase 4+).
- Telegram native BackButton (revisitable; in-app chosen).
