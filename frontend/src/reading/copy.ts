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
// Replay entry on the question step — re-run the intro/atmosphere/reversed-cards explainer on demand.
export const ONBOARDING_REPLAY = "Как это работает";

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
// The ritual headlines crossfade one per ~second and CYCLE while the reading is still being
// prepared, so the shuffle never freezes on a single line during a longer wait (D «надписей мало,
// анимация останавливается»). Brand-safe (SAFE-06) + non-fatalistic.
export const RITUAL_BEATS: readonly string[] = [
  "Колода слышит твой вопрос…",
  "Карты приходят в движение…",
  "Шёпот колоды становится тише…",
  "Узор расклада складывается…",
  "Скрытое выходит к свету…",
  "Три знака уже ищут тебя…",
  "Колода почти готова ответить…",
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
// Phase 6 — free-limit surfaces (LIMIT-01/03/05, D-03/04/08/09/10). The verbatim UI-SPEC
// Copywriting-Contract strings for the soft paywall sheet, the transient throttle toast, and
// the subtle remaining-count line. SAFE-06 hard gate: zero AI/ИИ/нейросеть/модель, no fear /
// «приговор» / pressure — show «открыть ещё», never «купи» (TZ §11.2). The interpolated
// countdown + count are composed by the pure helpers in limitCopy.ts (kept there so this
// module stays a flat constant bank; limitCopy re-uses these leads).

// Soft paywall bottom-sheet (D-03/D-04). Adopts TZ §9.8's first sentence, replaces «подождать
// обновления лимита» with the concrete reset countdown, and drops the «…за Stars» clause
// (payments are Phase 7) — substituted by PAYWALL_SOON_NOTE.
export const PAYWALL_TITLE =
  "На этой неделе бесплатные расклады закончились";
// Reset lead-in — the countdown value (formatReset) is appended after the trailing space.
export const PAYWALL_RESET_LEAD = "Бесплатные расклады вернутся ";
export const PAYWALL_SOON_NOTE =
  "А ещё совсем скоро колоду можно будет открыть ещё — без ожидания.";
export const PAYWALL_DISMISS = "Закрыть";

// Transient throttle toast (D-08, HTTP 429) — «one breath, then continue», never an alarm.
export const THROTTLE_MESSAGE =
  "Колода переводит дыхание. Подожди мгновение и попробуй снова.";

// Remaining-count line (D-09/D-10) — composed as «Осталось {N} из {total}» by formatRemaining;
// the lead lives here so the ban-list scan covers it. LIMIT_LAST_ONE_HINT is the single gentle
// accent at exactly 1 remaining; PROFILE_LIMIT_LABEL is the un-hidden profile block eyebrow.
export const LIMIT_REMAINING_PREFIX = "Осталось ";
export const LIMIT_LAST_ONE_HINT = "Последний расклад на этой неделе";
export const PROFILE_LIMIT_LABEL = "Бесплатные расклады";

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
// Phase 7 — shop / tariffs (PAY-01/08, D-12/D-13). Brand-safe (SAFE-06): zero AI/ИИ/нейросеть/
// модель, no pressure — «Открыть», never «купи». Honest on failure (D-13): «деньги не списаны».
export const SHOP_TITLE = "Пополнить колоду";
export const SHOP_BALANCE_LABEL = "Куплено раскладов";
export const SHOP_SUBSCRIPTION_LABEL = "Лунный доступ";
export const SHOP_SUB_ACTIVE_PREFIX = "активна до ";
export const SHOP_BUY_CTA = "Открыть";
export const SHOP_SUCCESS = "Доступ открыт";
export const SHOP_PENDING = "Ждём подтверждение оплаты…";
export const SHOP_FAILURE =
  "Оплата не прошла — деньги не списаны, доступ не выдан. Попробуй ещё раз.";
export const SHOP_CANCEL_SUB = "Отменить продление";

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
