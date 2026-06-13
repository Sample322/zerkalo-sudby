// THE PHASE-4 SEAM (D-05), now swapped to the real source. Phase 3 built a MockReading
// locally from the bundled fixture; Phase 4 replaces ONLY the body with an authenticated
// POST /api/readings (the §14.5 contract) through the existing apiFetch Bearer seam,
// PRESERVING the exported signature and the `MockReading` return type — so the
// ritual/reveal/result screens are untouched (D-07 "mechanical swap").
//
// ARCHITECTURE GUARD (Phase-3 D-05, locked): the reading stays an ephemeral value held in
// the Zustand `reading` slot (written by CatalogScreen via setReading). It is deliberately
// NOT moved into a TanStack Query mutation — RESEARCH Pattern 6 suggested a Query mutation,
// but the locked D-05 decision keeps it in the store, so this seam keeps its plain
// async-function signature and the store hand-off is unchanged.

import { apiFetch } from "../api/client";
import { SHORT_PHRASES } from "./copy";
import type {
  MockReading,
  MockReadingCard,
  MockReadingSummary,
  Orientation,
  ReadingOutResponse,
} from "./types";

export interface CreateReadingParams {
  question: string | null;
  topic: string;
  deckSlug: string;
  spreadSlug: string;
  reversalsEnabled: boolean;
  /**
   * The chosen spread's positions, passed through from the trusted Phase-2 spreads query.
   * Mock-only legacy: the real backend draws + titles its own positions server-side, so the
   * positions are NOT sent in the request body (cards/titles come back authoritative). Kept
   * on the params so the caller's call site is unchanged across the swap.
   */
  positions?: { title: string }[];
}

/** §14.5 request body field names — exactly what `ReadingCreate` validates server-side. */
interface ReadingCreateBody {
  question: string | null;
  topic: string;
  deck_slug: string;
  spread_slug: string;
  reversals_enabled: boolean;
}

/** Narrow the server-sent orientation string to the closed Orientation union. */
function toOrientation(value: string): Orientation {
  return value === "reversed" ? "reversed" : "upright";
}

/**
 * Map one backend `ReadingCardOutResponse` (snake_case) onto a `MockReadingCard`
 * (camelCase). `shortPhrase` has no backend field — the result UI shows a short
 * in-character lead-in, so it is sourced from the brand-safe copy bank, cycled by index.
 */
function mapCard(
  card: ReadingOutResponse["cards"][number],
  index: number,
): MockReadingCard {
  return {
    name: card.name,
    positionTitle: card.position_title,
    orientation: toOrientation(card.orientation),
    shortMeaning: card.short_meaning,
    interpretation: card.interpretation,
    deckAccent: card.deck_accent,
    shortPhrase: SHORT_PHRASES[index % SHORT_PHRASES.length],
  };
}

/** Map the §14.5 summary (already pre-named server-side) onto `MockReadingSummary`. */
function mapSummary(
  summary: NonNullable<ReadingOutResponse["summary"]>,
): MockReadingSummary {
  return {
    linkage: summary.linkage,
    mainFactor: summary.main_factor,
    attention: summary.attention,
    softAdvice: summary.soft_advice,
    closingPhrase: summary.closing_phrase,
  };
}

/**
 * Create a real per-deck reading via `POST /api/readings` and resolve to a `MockReading`.
 *
 * The promise REJECTS on any failure so the caller's `catch` surfaces the §9.8 copy and
 * the D-08 retry/change-deck UX without advancing the ritual (D-07/D-09):
 *   - a non-OK HTTP status, OR
 *   - a soft honest-fail/paywall/refusal body (`status !== "completed"`, or no cards, or a
 *     missing summary) — on those paths the limit is NOT consumed server-side, so a retry
 *     is free.
 */
export async function createReading(
  params: CreateReadingParams,
): Promise<MockReading> {
  const { question, topic, deckSlug, spreadSlug, reversalsEnabled } = params;

  const body: ReadingCreateBody = {
    question, // null => general reading (HOME-02 / D-13)
    topic,
    deck_slug: deckSlug,
    spread_slug: spreadSlug,
    reversals_enabled: reversalsEnabled,
  };

  const response = await apiFetch("/api/readings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    // Soft §9.8 path is the caller's concern — reject so the ritual does not advance.
    throw new Error(`createReading failed: HTTP ${response.status}`);
  }

  const data = (await response.json()) as ReadingOutResponse;

  // Honest-fail / safety / paywall: a soft 200 body with status=failed + empty cards (the
  // §9.8 copy rides in summary.soft_advice). Reject — the reveal must not show an empty
  // reading and the limit was not consumed (D-09).
  if (data.status !== "completed" || data.cards.length === 0 || data.summary === null) {
    throw new Error(`createReading not completed: status=${data.status}`);
  }

  return {
    question,
    topic,
    deckSlug,
    spreadSlug,
    createdAt: new Date().toISOString(),
    cards: data.cards.map(mapCard),
    summary: mapSummary(data.summary),
  };
}
