// Phase-6 pure limit-copy helpers (D-04 / D-09 / D-10). These compose the runtime-interpolated
// strings the static constants in copy.ts can't hold: the remaining-count line «Осталось N из M»
// and the per-user paywall reset countdown («через N дней» / an absolute genitive date / a
// «совсем скоро» fallback). Kept in this module (imported by copy.ts's siblings) so reading/
// copy.test.ts scans the leads they build on; these functions are pure (no I/O, no Date.now
// unless `now` is omitted) and NaN/invalid-guarded so the UI never flashes «NaN» or an empty
// broken countdown — the count is non-essential chrome (UI-SPEC: render nothing rather than
// a broken value). No banned brand token (SAFE-06): plain «осталось / расклад / неделя».

import { LIMIT_REMAINING_PREFIX } from "./copy";

/** One day in milliseconds — the relative/absolute split + day-delta rounding base. */
const MS_PER_DAY = 86_400_000;

/**
 * The window beyond which the reset is shown as an absolute date instead of relative days
 * (~48h per the UI-SPEC). At or under this many whole days out → «через N дней»; beyond → a
 * genitive date «D MMMM».
 */
const RELATIVE_DAYS_MAX = 2;

/**
 * Compose the remaining-count line «Осталось {left} из {total}» (D-09). `left` is clamped to
 * ≥ 0 (a backend over-count can never render «Осталось -1 …»). If either argument is NaN the
 * count is non-essential chrome, so we return the empty string and the caller renders nothing
 * — never «NaN из 3».
 */
export function formatRemaining(left: number, total: number): string {
  if (Number.isNaN(left) || Number.isNaN(total)) return "";
  const safeLeft = Math.max(0, left);
  return `${LIMIT_REMAINING_PREFIX}${safeLeft} из ${total}`;
}

/** RU genitive month names (for the absolute «16 июня» reset date). Index 0 = January. */
const MONTHS_GENITIVE = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
] as const;

/**
 * Choose the RU plural form of «день» for a whole-day count: 1 → день, 2–4 → дня, else → дней
 * (the standard Russian one/few/many rule, with the 11–14 exception). Within the relative
 * window only 1 and 2 occur, but the chooser is general so it stays correct if the window widens.
 */
function pluralDay(n: number): string {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "дней";
  const mod10 = n % 10;
  if (mod10 === 1) return "день";
  if (mod10 >= 2 && mod10 <= 4) return "дня";
  return "дней";
}

/**
 * Render the per-user paywall reset moment (D-04) as a brand-safe phrase:
 *   - within ~48h → relative days «через N дней» (rounded UP so a sub-day reset is «через 1
 *     день», never «через 0 дней»),
 *   - beyond → an absolute genitive date «16 июня»,
 *   - absent / unparseable → «совсем скоро» (a non-numeric reassurance — never «NaN», never
 *     empty), so a missing reset_at still reads as a hopeful, not broken, countdown.
 *
 * Pure: `now` defaults to the current time only when omitted (tests pass a fixed `now`).
 */
export function formatReset(resetAt: string | Date, now: Date = new Date()): string {
  // Guard falsy input FIRST: `new Date(null)`/`new Date("")` would coerce to the epoch (a valid
  // Date), not Invalid Date — so a null reset_at off the wire must short-circuit to the fallback
  // before construction, never «через N дней» counted from 1970.
  if (!resetAt) return "совсем скоро";
  const reset = resetAt instanceof Date ? resetAt : new Date(resetAt);
  if (Number.isNaN(reset.getTime())) return "совсем скоро";

  const diffMs = reset.getTime() - now.getTime();
  // Round up to the next whole day so a 6h reset reads «через 1 день» (never «через 0 дней»);
  // an already-elapsed reset (diffMs ≤ 0) clamps to 1 day so the copy stays forward-looking.
  const days = Math.max(1, Math.ceil(diffMs / MS_PER_DAY));

  if (days <= RELATIVE_DAYS_MAX) {
    return `через ${days} ${pluralDay(days)}`;
  }

  return `${reset.getUTCDate()} ${MONTHS_GENITIVE[reset.getUTCMonth()]}`;
}

// ---------------------------------------------------------------------------------------
// Phase-7 shop formatters (PAY-01/08). Pure, NaN-guarded — a broken price/hint renders nothing
// rather than «NaN ₽» (mirrors formatRemaining). SAFE-06: plain «₽ / расклад / день», no brand token.

/** Format a whole-ruble price as «299 ₽» (backend `price_rub` is an integer in rubles, A1). */
export function formatRub(rub: number): string {
  if (Number.isNaN(rub)) return "";
  return `${rub} ₽`;
}

/** Choose the RU plural of «расклад»: 1 → расклад, 2–4 → расклада, else → раскладов (11–14 excepted). */
function pluralSpread(n: number): string {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 14) return "раскладов";
  const mod10 = n % 10;
  if (mod10 === 1) return "расклад";
  if (mod10 >= 2 && mod10 <= 4) return "расклада";
  return "раскладов";
}

/** The pack per-reading hint «3 расклада» (grammatically-agreed count). Empty on NaN. */
export function formatSpreads(n: number): string {
  if (Number.isNaN(n)) return "";
  return `${n} ${pluralSpread(n)}`;
}

/** The subscription duration hint «30 дней» (reuses the day pluralizer). Empty on NaN. */
export function formatDays(n: number): string {
  if (Number.isNaN(n)) return "";
  return `${n} ${pluralDay(n)}`;
}
