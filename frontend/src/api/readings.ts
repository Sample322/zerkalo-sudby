// Readings history API (HIST-02). Fetches the light history list through the Bearer
// `apiFetch` seam and throws a typed error on non-2xx (mirrors api/decks.ts CatalogError).
// `ReadingListItem` is the snake_case mirror of the backend `ReadingListItemOut`
// (backend/app/schemas/reading.py) — only the fields the list card consumes are typed.
//
// The list is the LIGHT shape (date / question / deck / spread / thumbnails / short summary,
// TZ §9.6) — NOT the full per-card interpretation, which belongs to the detail endpoint
// (GET /api/readings/{id}, wired in 05-06). No `any` (TS rule).

import { apiFetch } from "./client";

/** Free-tier history cap (HIST-06 / D-04) — the server bounds the window to the last 10. */
export const HISTORY_LIMIT = 10;

/** One history list item (TZ §9.6 / HIST-02) — mirrors backend `ReadingListItemOut`. */
export interface ReadingListItem {
  /** UUID — for reopening the reading (HIST-03). */
  reading_id: string;
  /** ISO timestamp; the list shows the date, newest-first. */
  created_at: string;
  /** null/empty → general reading (HOME-02 / D-13). */
  question: string | null;
  /** Human deck title (Deck.title). */
  deck_name: string;
  /** Human spread title (SpreadType.title). */
  spread_name: string;
  /** deck_cards.thumbnail_url for the drawn cards (position order); may be empty → CSS fallback. */
  card_thumbnails: string[];
  /** Short summary (readings.summary_short) — NOT the full interpretation. */
  summary_short: string | null;
}

/** Thrown when a history request returns a non-2xx status. */
export class HistoryError extends Error {
  readonly status: number;

  constructor(status: number, message = "history request failed") {
    super(message);
    this.name = "HistoryError";
    this.status = status;
  }
}

/**
 * Fetch the reverse-chronological history list (HIST-02). Calls
 * `GET /api/readings?limit=10` through the Bearer seam; the server scopes by the JWT user
 * (the client never sends a user_id) and bounds the window to the free-tier cap (HIST-06).
 */
export async function fetchReadings(): Promise<ReadingListItem[]> {
  const res = await apiFetch(`/api/readings?limit=${HISTORY_LIMIT}`);
  if (!res.ok) throw new HistoryError(res.status);
  return (await res.json()) as ReadingListItem[];
}
