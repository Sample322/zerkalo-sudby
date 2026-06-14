// Readings history API (HIST-02). Fetches the light history list through the Bearer
// `apiFetch` seam and throws a typed error on non-2xx (mirrors api/decks.ts CatalogError).
// `ReadingListItem` is the snake_case mirror of the backend `ReadingListItemOut`
// (backend/app/schemas/reading.py) — only the fields the list card consumes are typed.
//
// The list is the LIGHT shape (date / question / deck / spread / thumbnails / short summary,
// TZ §9.6) — NOT the full per-card interpretation, which belongs to the detail endpoint
// (GET /api/readings/{id}, wired in 05-06). No `any` (TS rule).

import { apiFetch } from "./client";
import type { ReadingOutResponse } from "../reading/types";

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

/**
 * Fetch a single immutable reading (HIST-03) via `GET /api/readings/{id}` through the Bearer
 * seam. The server scopes by the JWT user and returns the same heavy `ReadingOut` (§14.5) the
 * create endpoint does — re-reading NEVER regenerates (05-04), so two GETs are byte-identical.
 * A non-owned / deleted id 404s server-side (closes T-05 IDOR) → thrown as `HistoryError`.
 */
export async function fetchReadingDetail(id: string): Promise<ReadingOutResponse> {
  const res = await apiFetch(`/api/readings/${id}`);
  if (!res.ok) throw new HistoryError(res.status);
  return (await res.json()) as ReadingOutResponse;
}

/**
 * Soft-delete a reading (HIST-04 / D-03) via `DELETE /api/readings/{id}` through the Bearer
 * seam. The server sets `deleted_at` (retain-data, 05-04) and scopes by the JWT user; a
 * non-owned / already-deleted id 404s (no existence leak — T-05 IDOR). Throws on non-2xx so
 * the optimistic mutation can roll its cache back (Pattern 3 `onError`).
 */
export async function deleteReading(id: string): Promise<void> {
  const res = await apiFetch(`/api/readings/${id}`, { method: "DELETE" });
  if (!res.ok) throw new HistoryError(res.status);
}

/**
 * Restore a soft-deleted reading (HIST-04 undo / D-03) via `POST /api/readings/{id}/restore`
 * through the Bearer seam — the dedicated route that nulls `deleted_at` (05-04, RESEARCH OQ1;
 * no `deleted_at` column is ever leaked over the API). User-scoped server-side. Throws on
 * non-2xx so the undo surfaces failure rather than silently dropping the reading.
 */
export async function restoreReading(id: string): Promise<void> {
  const res = await apiFetch(`/api/readings/${id}/restore`, { method: "POST" });
  if (!res.ok) throw new HistoryError(res.status);
}
