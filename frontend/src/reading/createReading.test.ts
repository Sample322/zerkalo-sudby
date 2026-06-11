import { describe, expect, it } from "vitest";

import { BANNED_BRAND_TOKENS } from "./copy";
import { createReading } from "./createReading";

const POSITIONS = [
  { title: "Суть" },
  { title: "Препятствие" },
  { title: "Совет" },
];

function baseParams(overrides: Record<string, unknown> = {}) {
  return {
    question: "Что мне важно увидеть?",
    topic: "love",
    deckSlug: "moon_mirror",
    spreadSlug: "three_card",
    reversalsEnabled: false,
    positions: POSITIONS,
    ...overrides,
  };
}

describe("createReading — the Phase-4 seam (D-05)", () => {
  it("is async and returns a Promise<MockReading>", async () => {
    const result = createReading(baseParams());
    expect(result).toBeInstanceOf(Promise);
    await result;
  });

  it("returns one card per spread position, every READ-05 field populated", async () => {
    const reading = await createReading(baseParams());
    expect(reading.cards).toHaveLength(POSITIONS.length);
    for (const card of reading.cards) {
      expect(card.name).toBeTruthy();
      expect(card.positionTitle).toBeTruthy();
      expect(card.orientation).toMatch(/^(upright|reversed)$/);
      expect(card.shortMeaning).toBeTruthy();
      expect(card.interpretation).toBeTruthy();
      expect(card.deckAccent).toBeTruthy();
      expect(card.shortPhrase).toBeTruthy();
    }
  });

  it("summary has all READ-06 fields populated", async () => {
    const { summary } = await createReading(baseParams());
    expect(summary.linkage).toBeTruthy();
    expect(summary.mainFactor).toBeTruthy();
    expect(summary.attention).toBeTruthy();
    expect(summary.softAdvice).toBeTruthy();
    expect(summary.closingPhrase).toBeTruthy();
  });

  it("echoes the inputs; createdAt is an ISO string", async () => {
    const reading = await createReading(baseParams());
    expect(reading.topic).toBe("love");
    expect(reading.deckSlug).toBe("moon_mirror");
    expect(reading.spreadSlug).toBe("three_card");
    expect(reading.question).toBe("Что мне важно увидеть?");
    expect(() => new Date(reading.createdAt).toISOString()).not.toThrow();
    expect(reading.createdAt).toBe(new Date(reading.createdAt).toISOString());
  });

  it("question is null for a general reading (HOME-02)", async () => {
    const reading = await createReading(baseParams({ question: null }));
    expect(reading.question).toBeNull();
  });

  it("positionTitle of each card comes from the passed positions (spread-driven)", async () => {
    const reading = await createReading(baseParams());
    expect(reading.cards.map((c) => c.positionTitle)).toEqual([
      "Суть",
      "Препятствие",
      "Совет",
    ]);
  });

  it("generated card + summary copy is brand-safe (SAFE-06, incl. ИИ)", async () => {
    const reading = await createReading(baseParams());
    const text = [
      ...reading.cards.flatMap((c) => [
        c.name,
        c.shortMeaning,
        c.interpretation,
        c.deckAccent,
        c.shortPhrase,
      ]),
      ...Object.values(reading.summary),
    ].join(" ");
    expect(BANNED_BRAND_TOKENS.test(text)).toBe(false);
  });
});

describe("reversals (D-07) — deterministic via injected RNG", () => {
  it("OFF → every card orientation is upright (regardless of RNG)", async () => {
    const reading = await createReading(
      baseParams({ reversalsEnabled: false, rng: () => 0 }),
    );
    expect(reading.cards.every((c) => c.orientation === "upright")).toBe(true);
  });

  it("ON + rng < 0.3 → cards are reversed", async () => {
    const reading = await createReading(
      baseParams({ reversalsEnabled: true, rng: () => 0.1 }),
    );
    expect(reading.cards.every((c) => c.orientation === "reversed")).toBe(true);
  });

  it("ON + rng >= 0.3 → cards are upright", async () => {
    const reading = await createReading(
      baseParams({ reversalsEnabled: true, rng: () => 0.9 }),
    );
    expect(reading.cards.every((c) => c.orientation === "upright")).toBe(true);
  });

  it("ON → only 'upright'/'reversed' values ever appear (no other strings)", async () => {
    // A varying RNG cycles through both branches; assert the value domain is closed.
    let n = 0;
    const reading = await createReading(
      baseParams({
        reversalsEnabled: true,
        rng: () => {
          n += 1;
          return (n % 5) / 10; // 0.1, 0.2, 0.3, 0.4, 0 … spans both sides of 0.3
        },
      }),
    );
    for (const card of reading.cards) {
      expect(["upright", "reversed"]).toContain(card.orientation);
    }
  });
});
