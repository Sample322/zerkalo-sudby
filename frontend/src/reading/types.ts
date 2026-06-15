// The mock reading data contract (D-05). These field names MIRROR the future real
// backend contract (READ-05 per-card fields + READ-06 summary fields) so Phase 4 swaps
// ONLY the data source (POST /api/readings) — the reveal/result UI stays untouched.
// Interface style mirrors api/spreads.ts (exported interfaces, nullable fields explicit,
// nested types named). This is a pure type module — no behavior, no runtime values.

export type Orientation = "upright" | "reversed";

export interface MockReadingCard {
  /** READ-05 название — the card's name. */
  name: string;
  /** READ-05 позиция — the position title from the chosen spread. */
  positionTitle: string;
  /** READ-05 положение — upright/reversed (D-07 toggle). */
  orientation: Orientation;
  /** READ-05 короткое значение — the rough universal meaning. */
  shortMeaning: string;
  /** READ-05 глубокая интерпретация под вопрос. */
  interpretation: string;
  /** READ-05 мистический акцент колоды — deck micro-text. */
  deckAccent: string;
  /** READ-08 short in-character phrase shown before the interpretation. */
  shortPhrase: string;
}

export interface MockReadingSummary {
  /** READ-06 связка карт — how the cards relate. */
  linkage: string;
  /** READ-06 главный фактор. */
  mainFactor: string;
  /** READ-06 на что обратить внимание. */
  attention: string;
  /** READ-06 мягкий совет. */
  softAdvice: string;
  /** READ-06 завершающая фраза в стиле колоды. */
  closingPhrase: string;
}

export interface MockReading {
  /** null => general reading (HOME-02 / D-13). */
  question: string | null;
  topic: string;
  deckSlug: string;
  spreadSlug: string;
  /** ISO timestamp; the result screen shows the date (READ-09). */
  createdAt: string;
  cards: MockReadingCard[];
  summary: MockReadingSummary;
}

// ---------------------------------------------------------------------------------------
// Phase-4 backend contract (POST /api/readings response, TZ §14.5). These mirror the
// backend `ReadingOut` / `ReadingCardOut` / `ReadingSummaryOut` (snake_case) so the
// createReading seam can map them onto the camelCase MockReading shape above mechanically
// (D-07). The backend already pre-maps the LLM summary names (connection→linkage,
// attention_point→attention, advice→soft_advice, closing_phrase) — see
// backend/app/schemas/reading.py `ReadingSummaryOut`. Declared here (not `any`) so the
// mapping in createReading.ts is fully typed (web TS rules: no `any`).

/** One drawn card in the §14.5 response — the authoritative server-side per-card row. */
export interface ReadingCardOutResponse {
  name: string;
  position_title: string;
  /** "upright" | "reversed" — server-decided (D-13 70/30 CSPRNG). */
  orientation: string;
  short_meaning: string;
  interpretation: string;
  deck_accent: string;
}

/** The §14.5 response summary — all five §18 fields, already named for the frontend. */
export interface ReadingSummaryOutResponse {
  linkage: string;
  main_factor: string;
  attention: string;
  soft_advice: string;
  closing_phrase: string;
}

/**
 * The `POST /api/readings` response body (TZ §14.5). On the soft/honest-fail paths
 * (paywall / refusal / redirect / generation failure) `status` is `failed`, `cards` is
 * empty, and the §9.8 in-character copy rides in `summary.soft_advice` — the seam treats
 * any non-`completed` status (or an empty card list) as a failure and rejects (D-08/D-09).
 */
export interface ReadingOutResponse {
  reading_id: string;
  status: string;
  cards: ReadingCardOutResponse[];
  summary: ReadingSummaryOutResponse | null;
  remaining_limits: number | null;
  /**
   * Phase-6 limit-block discriminant (06-02). On the soft paywall body this is `"paywall"`
   * (HTTP 200, status != "completed", no draw); `null` on success / refusal / redirect /
   * honest-fail. The createReading catch branches on this — NOT on string-matching the copy.
   */
  reason?: string | null;
  /**
   * Phase-6 per-user reopen moment (06-02): `week_start + 7d`, fuelling the D-04 countdown
   * («вернутся через N»). Present on the paywall body, `null` otherwise.
   */
  reset_at?: string | null;
}
