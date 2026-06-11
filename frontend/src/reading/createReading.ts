// THE PHASE-4 SEAM (D-05). Phase 3 builds a MockReading locally from the bundled fixture
// (D-06) with client-side reversals (D-07); Phase 4 replaces the body with POST /api/readings
// keeping the SAME return type, so the swap is mechanical. Signature/return shape mirrors
// fetchSpreads (api/spreads.ts) so the later boundary is a drop-in (PATTERNS Shared 5).

import { CARD_POOL } from "./cardPool.fixture";
import {
  DECK_ACCENT_PHRASES,
  SHORT_PHRASES,
  SUMMARY_TEMPLATES,
} from "./copy";
import type {
  MockReading,
  MockReadingCard,
  MockReadingSummary,
  Orientation,
} from "./types";

/** Reversed-card probability when the toggle is on (~70% upright / 30% reversed, D-07). */
const REVERSED_PROBABILITY = 0.3;

export interface CreateReadingParams {
  question: string | null;
  topic: string;
  deckSlug: string;
  spreadSlug: string;
  reversalsEnabled: boolean;
  positions: { title: string }[];
  /**
   * Injectable RNG (default Math.random) — D-07 is deliberately NON-security (the real
   * CSPRNG draw is a Phase-4 backend concern, threat T-3-03). Injection makes the
   * reversed/upright branches deterministically testable.
   */
  rng?: () => number;
}

/** Pick `count` cards from the pool without repetition (wraps if count exceeds the pool). */
function drawCards(count: number, rng: () => number): typeof CARD_POOL[number][] {
  const indices = CARD_POOL.map((_, i) => i);
  // Fisher–Yates with the injected RNG so a seeded test is fully deterministic.
  for (let i = indices.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rng() * (i + 1));
    [indices[i], indices[j]] = [indices[j], indices[i]];
  }
  return Array.from({ length: count }, (_, i) => CARD_POOL[indices[i % indices.length]]);
}

function orientationFor(reversalsEnabled: boolean, rng: () => number): Orientation {
  if (!reversalsEnabled) return "upright";
  return rng() < REVERSED_PROBABILITY ? "reversed" : "upright";
}

function interpretationFor(card: { name: string; shortMeaning: string }, position: string): string {
  return `В позиции «${position}» карта «${card.name}» звучит так: ${card.shortMeaning} Это мягкая подсказка, а не предсказание — взгляд на тему с новой стороны.`;
}

function buildSummary(): MockReadingSummary {
  return {
    linkage: SUMMARY_TEMPLATES.linkage,
    mainFactor: SUMMARY_TEMPLATES.mainFactor,
    attention: SUMMARY_TEMPLATES.attention,
    softAdvice: SUMMARY_TEMPLATES.softAdvice,
    closingPhrase: SUMMARY_TEMPLATES.closingPhrase,
  };
}

/**
 * Build the mock reading. Returns a fully-populated MockReading mirroring the future
 * READ-05/06 contract; `question` passes through (null => general reading).
 */
export async function createReading(
  params: CreateReadingParams,
): Promise<MockReading> {
  const {
    question,
    topic,
    deckSlug,
    spreadSlug,
    reversalsEnabled,
    positions,
    rng = Math.random,
  } = params;

  const drawn = drawCards(positions.length, rng);

  const cards: MockReadingCard[] = positions.map((position, i) => {
    const card = drawn[i];
    return {
      name: card.name,
      positionTitle: position.title,
      orientation: orientationFor(reversalsEnabled, rng),
      shortMeaning: card.shortMeaning,
      interpretation: interpretationFor(card, position.title),
      deckAccent: DECK_ACCENT_PHRASES[i % DECK_ACCENT_PHRASES.length],
      shortPhrase: SHORT_PHRASES[i % SHORT_PHRASES.length],
    };
  });

  return {
    question,
    topic,
    deckSlug,
    spreadSlug,
    createdAt: new Date().toISOString(),
    cards,
    summary: buildSummary(),
  };
}
