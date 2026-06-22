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

/** The discriminable kind of a createReading rejection (D-08 — the seam that splits the three
 *  surfaces). `throttle` = HTTP 429 (the Redis burst gate, 06-03, transient toast); `paywall` =
 *  the 200 limit-block body (06-02, `reason='paywall'`, persistent sheet, carries `resetAt`);
 *  `failure` = any other non-OK status or a non-completed/empty body (the existing §9.8 band). */
export type ReadingErrorKind = "throttle" | "paywall" | "failure";

/**
 * The typed rejection createReading throws so ONE `catch` in CatalogScreen.handleStart can route
 * to three distinct surfaces without conflating them (D-08). The throttle and the paywall are
 * NEVER the same transport: 429 → `throttle`, the 200 `reason='paywall'` body → `paywall` (with
 * the per-user `resetAt` for the D-04 countdown), everything else → `failure`. createReading's
 * SUCCESS path, signature, and `MockReading` return type are unchanged — only the error type is
 * new (D-05/D-07 architecture guard).
 */
export class ReadingError extends Error {
  readonly kind: ReadingErrorKind;
  /** The per-user reopen moment (`reset_at`, = week_start + 7d). Set ONLY on the paywall kind. */
  readonly resetAt?: string | null;

  constructor(kind: ReadingErrorKind, message: string, resetAt?: string | null) {
    super(message);
    this.name = "ReadingError";
    this.kind = kind;
    this.resetAt = resetAt;
  }
}

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
  /**
   * Human RU labels for the result meta. The backend request carries the slugs (deck_slug /
   * spread_slug / topic), but the result screen must show these titles — never the English
   * slugs. Sourced by the caller from the loaded decks/spreads/topics. Optional: falls back to
   * the slug when absent (e.g. a future caller that lacks the catalog).
   */
  deckTitle?: string;
  spreadTitle?: string;
  topicLabel?: string;
  /** Answer-style preference (Ясный/Бережный/Таинственный) → tunes the generation + tracked. */
  answerStyle?: string;
}

/** §14.5 request body field names — exactly what `ReadingCreate` validates server-side. */
interface ReadingCreateBody {
  question: string | null;
  topic: string;
  deck_slug: string;
  spread_slug: string;
  reversals_enabled: boolean;
  answer_style: string;
}

/**
 * The non-content meta fields a `MockReading` carries that the §14.5 `ReadingOut` body does
 * NOT (question / topic / deckSlug / spreadSlug / createdAt). The live-flow seam sources them
 * from the request params; the history-detail seam (05-06) sources them from the tapped list
 * item — both feed them into the ONE shared mapper below (DRY).
 */
export interface ReadingMeta {
  question: string | null;
  topic: string;
  deckSlug: string;
  spreadSlug: string;
  createdAt: string;
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
 * THE single `ReadingOut` → `MockReading` transform (DRY). Both the live-flow `createReading`
 * seam and the history-detail fetcher (05-06) map through this one function so the
 * snake→camel per-card + summary mapping exists in exactly one place. The content (cards +
 * summary) comes from the immutable §14.5 body; the `meta` (question/topic/deck/spread/date)
 * is passed in by the caller because §14.5 `ReadingOut` does not carry those fields.
 *
 * @throws if `data.summary` is null — callers must guard non-completed bodies first
 *   (createReading rejects them; the detail endpoint only ever returns completed readings).
 */
export function mapReadingOutToMock(
  data: ReadingOutResponse,
  meta: ReadingMeta,
): MockReading {
  if (data.summary === null) {
    throw new Error("mapReadingOutToMock: summary is null (non-completed reading)");
  }
  return {
    question: meta.question,
    topic: meta.topic,
    deckSlug: meta.deckSlug,
    spreadSlug: meta.spreadSlug,
    createdAt: meta.createdAt,
    cards: data.cards.map(mapCard),
    summary: mapSummary(data.summary),
  };
}

/**
 * Create a real per-deck reading via `POST /api/readings` and resolve to a `MockReading`.
 *
 * The promise REJECTS with a discriminated {@link ReadingError} (D-08) so the caller's ONE
 * `catch` routes to three distinct surfaces without conflating them — the throttle, the
 * paywall, and a generation failure are never the same transport:
 *   - HTTP 429 (the Redis burst gate, 06-03) → `kind:"throttle"` (transient toast),
 *   - a 200 limit-block body (`status !== "completed"` AND `reason === "paywall"`, 06-02) →
 *     `kind:"paywall"` carrying `resetAt` (= `reset_at` = week_start + 7d) for the D-04 countdown,
 *   - any other non-OK status, or a non-completed/empty/summary-less body → `kind:"failure"`
 *     (the existing §9.8 «Колода замолчала…» band).
 * On every rejection the limit was NOT consumed server-side, so a retry is free (D-09). The
 * success path / signature / `MockReading` return are unchanged (D-05/D-07 guard).
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
    answer_style: params.answerStyle ?? "berezhny",
  };

  const response = await apiFetch("/api/readings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    // D-08: a 429 is the Redis burst gate (06-03) — the FIRST gate, distinct from the paywall.
    // Any other non-OK status is a generic failure. Reject so the ritual does not advance.
    throw new ReadingError(
      response.status === 429 ? "throttle" : "failure",
      `createReading failed: HTTP ${response.status}`,
    );
  }

  const data = (await response.json()) as ReadingOutResponse;

  // A soft 200 body that is not a completed reading. Two cases, kept DISTINCT (D-08):
  //   - the 06-02 limit block carries `reason === "paywall"` (no draw) → the paywall sheet,
  //     carrying `reset_at` for the D-04 countdown. The limit was NOT consumed (the gate
  //     blocked before the draw), so this is not an error — it's the weekly exhaustion state.
  //   - otherwise it's the Phase-4 honest-fail / refusal / redirect (§9.8 copy in
  //     summary.soft_advice) → the existing failure band; the limit was refunded server-side.
  if (data.status !== "completed" || data.cards.length === 0 || data.summary === null) {
    if (data.reason === "paywall") {
      throw new ReadingError("paywall", "createReading blocked: free limit reached", data.reset_at);
    }
    throw new ReadingError("failure", `createReading not completed: status=${data.status}`);
  }

  // Map through the ONE shared transform (DRY). The result meta shows the RU titles (the slugs
  // go to the backend; the human labels go on screen) — fall back to the slug only if a label
  // wasn't supplied. createdAt is "now" (the reading was just generated).
  return mapReadingOutToMock(data, {
    question,
    topic: params.topicLabel ?? topic,
    deckSlug: params.deckTitle ?? deckSlug,
    spreadSlug: params.spreadTitle ?? spreadSlug,
    createdAt: new Date().toISOString(),
  });
}
