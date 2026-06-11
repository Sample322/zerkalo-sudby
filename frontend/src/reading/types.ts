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
