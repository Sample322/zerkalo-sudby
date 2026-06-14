// Centralized brand-safe RU copy (SAFE-06 gate target). EVERY new user-facing string in
// Phase 3 lives here so reading/copy.test.ts can scan the whole module against the ban-list.
// Voice mirrors AuthGate / CatalogScreen («Колода…», «Зеркало…») — soft, non-fatalistic.
// HARD RULE: zero occurrences of AI / ИИ / нейросеть / модель / сгенерировано, and no
// fatalistic «плохо»/«приговор»/«беда»/«узнай правду пока не поздно» framing.

// ---------------------------------------------------------------------------------------
// SAFE-06 canonical ban-list (W-1). The single source every plan reuses — Wave-2 component
// tests import BANNED_BRAND_TOKENS / containsBannedBrandToken from here INSTEAD of
// re-declaring the ad-hoc /ai|нейросет|модель|сгенерирован/i regex, so the standalone
// Cyrillic `ИИ` branch is inherited everywhere from one place.
//
// The `ии` alternative is anchored to Cyrillic-word boundaries — `(?:^|[^а-яё])ии(?:[^а-яё]|$)`
// — so it matches a bare «ИИ» and «сгенерировано ИИ» WITHOUT false-positiving inside benign
// words that merely contain the «ии» bigram (гармонии / линии / версии / комиссии).
// Stateless: a NON-global regex (no /g) so .test() never advances lastIndex.
export const BANNED_BRAND_TOKENS =
  /ai|нейросет|модель|сгенерирован|(?:^|[^а-яё])ии(?:[^а-яё]|$)/i;

/** True if `text` contains any banned brand token. Stateless (non-global regex). */
export function containsBannedBrandToken(text: string): boolean {
  return BANNED_BRAND_TOKENS.test(text);
}

// ---------------------------------------------------------------------------------------
// Onboarding (ONB-01..03) — 3 atmosphere slides + a reversed-cards explainer, final CTA.
export interface OnboardingSlide {
  title: string;
  subtitle: string;
}

export const ONBOARDING_SLIDES: readonly OnboardingSlide[] = [
  {
    title: "Добро пожаловать в Зеркало Судьбы",
    subtitle: "Задай вопрос — и колода подсветит то, что важно увидеть сейчас.",
  },
  {
    title: "Выбирай не только расклад, но и атмосферу",
    subtitle:
      "Классика, Луна, Тени, Любовь, Путь или Лесной Оракул — каждая колода говорит своим языком.",
  },
  {
    title: "Это не приговор, а подсказка",
    subtitle:
      "Карты помогают посмотреть на ситуацию с другой стороны. Решение всегда остаётся за тобой.",
  },
] as const;

// ONB-03 reversed-cards explainer — plain, non-scary (задержка / внутреннее сопротивление /
// скрытое напряжение), never «плохо».
export const REVERSED_EXPLAINER =
  "Иногда карта ложится перевёрнутой. Это не значит, что она плохая — чаще это знак задержки, внутреннего сопротивления или скрытого напряжения, которое пока проявляется не напрямую.";

export const ONBOARDING_CTA = "Сделать первый расклад";
export const ONBOARDING_SKIP = "Пропустить";
export const ONBOARDING_NEXT = "Далее";

// ---------------------------------------------------------------------------------------
// Selection screen (HOME-01/02/07).
export const QUESTION_PLACEHOLDER = "О чём спросим колоду?";
export const QUESTION_EMPTY_HELPER =
  "Можно спросить колоду о чём-то конкретном или сделать общий расклад.";
export const QUESTION_TOO_SHORT_HINT =
  "Попробуй сказать чуть подробнее — так колода услышит точнее.";
export const START_GATE_HINT =
  "Выбери тему, колоду и расклад — и колода будет готова.";
export const START_CTA = "Начать расклад";

// ---------------------------------------------------------------------------------------
// Ritual prep (READ-07/D-08) — 3 beats + skip + the reveal-entry line.
export const RITUAL_BEATS: readonly string[] = [
  "Колода слышит вопрос…",
  "Карты перемешиваются…",
  "Три знака уже рядом…",
] as const;

export const RITUAL_SKIP = "Пропустить";
export const REVEAL_ENTRY = "Открой первую карту";

// ---------------------------------------------------------------------------------------
// Reveal (READ-08/D-09).
export const REVEAL_OPEN_CARD = "Открыть карту";
export const REVEAL_OPEN_ALL = "Раскрыть все";
export const REVEAL_READ_MEANING = "Прочитать значение";

// Sample bank of in-character short phrases shown before a card's interpretation.
export const SHORT_PHRASES: readonly string[] = [
  "Эта карта говорит о том, что в центре ситуации.",
  "Здесь колода показывает скрытое напряжение.",
  "Последняя карта звучит как мягкий совет.",
  "Эта карта подсвечивает то, что уже зреет внутри.",
  "Колода обращает внимание на тихий, но важный поворот.",
] as const;

// Advance reveal -> result, and the shared in-app back affordance (D-03).
export const REVEAL_TO_RESULT = "Перейти к итогу";
export const NAV_BACK = "Назад";

// READ-08 положение карты (D-07) — RU labels for the orientation enum.
export const ORIENTATION_LABELS: Record<"upright" | "reversed", string> = {
  upright: "Прямое положение",
  reversed: "Перевёрнутое положение",
};

// ---------------------------------------------------------------------------------------
// Result (READ-09/D-12).
export const RESULT_HEADER = "Расклад готов";
export const RESULT_AGAIN_CTA = "Ещё расклад";
export const RESULT_SAVE_CTA = "Сохранить карточку";
export const RESULT_HISTORY_CTA = "История";
export const RESULT_SOON_BADGE = "скоро";
// Shown in the meta row when the reading has no question (HOME-02 / D-13).
export const RESULT_GENERAL = "Общий расклад";

// Meta-row labels (тема / колода / расклад / дата / вопрос).
export const RESULT_LABELS = {
  question: "Вопрос",
  topic: "Тема",
  deck: "Колода",
  spread: "Расклад",
  date: "Дата",
} as const;

// Summary-panel section heads (READ-06).
export const SUMMARY_LABELS = {
  linkage: "Связка карт",
  mainFactor: "Главный фактор",
  attention: "На что обратить внимание",
  softAdvice: "Мягкий совет",
  closingPhrase: "Завершение",
} as const;

// ---------------------------------------------------------------------------------------
// History & Profile (Phase 5 — HIST-01/02/06, PROF-01/02). Centralized here so 05-06/07
// import without re-editing copy.ts; the personalization explainer is described as «история
// раскладов»/«колода помнит» — NEVER the mechanism (no AI/нейросеть/модель/ИИ — Pitfall 6).

// History list (HIST-02 / §9.6).
export const HISTORY_HEADER = "История раскладов";
// §9.6 empty-state copy — soft, inviting, non-fatalistic (Claude's discretion per D-01/§9.6).
export const HISTORY_EMPTY =
  "Пока здесь тихо. Первый расклад появится в истории, когда колода даст ответ.";
// D-04 «последние 10» note — quiet, brand-safe (the subscription upsell is Phase 6/7).
export const HISTORY_LAST_TEN_NOTE = "Здесь хранятся последние десять раскладов.";
// Label for a list-item that has no question (HOME-02 / D-13 — mirrors RESULT_GENERAL).
export const HISTORY_GENERAL = "Общий расклад";
// In-character loading / error lines for the list (TanStack Query states).
export const HISTORY_LOADING = "Колода листает страницы памяти…";
export const HISTORY_ERROR = "История сейчас молчит. Загляни чуть позже.";
// Consumed by 05-06's delete + undo snackbar (centralized now so that plan adds no copy).
export const HISTORY_DELETED_NOTICE = "Расклад убран из истории.";
export const HISTORY_DELETE_UNDO = "Вернуть";

// Profile & settings (PROF-01/02 — body lands in 05-07; strings centralized here).
export const PROFILE_HEADER = "Профиль";
export const SETTINGS_REVERSALS_LABEL = "Перевёрнутые карты";
export const SETTINGS_PERSONALIZATION_LABEL = "Колода помнит мои расклады";
// Plain-language explainer + privacy note — describes the felt feature («история раскладов»/
// «колода помнит»), never the mechanism. Brand-safe (SAFE-06 / Pitfall 6).
export const SETTINGS_PERSONALIZATION_EXPLAINER =
  "Если включить, колода сможет опираться на твою историю раскладов, чтобы ответы со временем звучали ближе к тебе. История остаётся только твоей и никуда не передаётся.";

// ---------------------------------------------------------------------------------------
// Error state (TZ §9.8) — the generation-failure copy + the D-08 recovery affordances.
// On a failed reading the selection screen shows READING_ERROR plus two buttons: Повторить
// (re-run the same reading — the limit was NOT consumed, so the retry is free) and Сменить
// колоду (stay on selection, pick a different deck; the question is preserved, D-04).
export const READING_ERROR =
  "Колода замолчала на мгновение. Попробуй открыть расклад ещё раз — вопрос уже сохранён.";
export const READING_RETRY = "Повторить";
export const READING_CHANGE_DECK = "Сменить колоду";

// ---------------------------------------------------------------------------------------
// Brand-safe building blocks createReading uses to assemble per-card + summary copy.
export const DECK_ACCENT_PHRASES: readonly string[] = [
  "Колода произносит это тихо, своим языком.",
  "В голосе колоды слышится мягкое, но ясное напоминание.",
  "Колода добавляет к этому тёплый оттенок смысла.",
] as const;

export const SUMMARY_TEMPLATES = {
  linkage:
    "Карты складываются в общий узор — вместе они говорят об одном внутреннем движении.",
  mainFactor:
    "Главный акцент сейчас — на спокойном внимании к тому, что уже происходит.",
  attention:
    "Стоит обратить внимание на чувства, которые проявляются не сразу.",
  softAdvice:
    "Двигайся мягко и без спешки — у этой темы есть свой ритм.",
  closingPhrase:
    "Колода остаётся рядом: ответ всегда остаётся за тобой.",
} as const;
