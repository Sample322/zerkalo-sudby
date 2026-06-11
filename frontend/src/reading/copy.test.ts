import { describe, expect, it } from "vitest";

import * as copy from "./copy";
import {
  BANNED_BRAND_TOKENS,
  containsBannedBrandToken,
  REVERSED_EXPLAINER,
} from "./copy";

// A fresh, non-global regex per assertion would be needed if BANNED_BRAND_TOKENS were
// global; it is intentionally NON-global (stateless) so .test() is reusable. We still
// guard that property here.
describe("BANNED_BRAND_TOKENS (SAFE-06 canonical ban-list — W-1)", () => {
  it("is a stateless (non-global) regex so .test() never advances lastIndex", () => {
    expect(BANNED_BRAND_TOKENS.global).toBe(false);
    expect(BANNED_BRAND_TOKENS.test("ai")).toBe(true);
    // A second call on the same input must still match (would fail if /g).
    expect(BANNED_BRAND_TOKENS.test("ai")).toBe(true);
  });

  it("matches each banned stem in isolation", () => {
    expect(containsBannedBrandToken("это AI")).toBe(true);
    expect(containsBannedBrandToken("нейросеть")).toBe(true);
    expect(containsBannedBrandToken("нейросети")).toBe(true);
    expect(containsBannedBrandToken("модель")).toBe(true);
    expect(containsBannedBrandToken("сгенерировано")).toBe(true);
    expect(containsBannedBrandToken("сгенерирован")).toBe(true);
  });

  it("matches the standalone Cyrillic token ИИ / ии (case-insensitive) — W-1", () => {
    expect(containsBannedBrandToken("ИИ")).toBe(true);
    expect(containsBannedBrandToken("ии")).toBe(true);
    expect(containsBannedBrandToken("сгенерировано ИИ")).toBe(true);
    expect(containsBannedBrandToken("текст ии текст")).toBe(true);
    expect(containsBannedBrandToken("вопрос к ИИ.")).toBe(true);
  });

  it("does NOT false-positive on benign Cyrillic words containing the «ии» bigram", () => {
    expect(containsBannedBrandToken("гармонии")).toBe(false);
    expect(containsBannedBrandToken("линии")).toBe(false);
    expect(containsBannedBrandToken("версии")).toBe(false);
    expect(containsBannedBrandToken("комиссии")).toBe(false);
    expect(containsBannedBrandToken("в гармонии с собой")).toBe(false);
  });
});

describe("copy.ts module is brand-safe (SAFE-06)", () => {
  // Concatenate EVERY exported string in the module so a single scan covers the bank.
  function collectStrings(value: unknown): string[] {
    if (typeof value === "string") return [value];
    if (Array.isArray(value)) return value.flatMap(collectStrings);
    if (value && typeof value === "object") {
      return Object.values(value).flatMap(collectStrings);
    }
    return [];
  }

  const allCopy = collectStrings(copy).join(" \n ");

  it("contains zero banned brand tokens across all exports (AI/нейросеть/модель/сгенерировано/ИИ)", () => {
    expect(BANNED_BRAND_TOKENS.test(allCopy)).toBe(false);
  });

  it("the reversed-cards explainer carries no fatalistic framing (плохо/приговор/беда/негатив)", () => {
    expect(/плохо|приговор|беда|негатив/i.test(REVERSED_EXPLAINER)).toBe(false);
    // It still names the allowed plain-language framing (ONB-03).
    expect(/задержк|сопротивлен|напряжен/i.test(REVERSED_EXPLAINER)).toBe(true);
  });

  it("no fatalistic doom-framing anywhere in the module", () => {
    // The brand voice forbids fatalistic pressure. Note the APPROVED onboarding line
    // «Это не приговор, а подсказка» deliberately uses «не приговор» (a negation), so we
    // guard the doom phrases themselves, not the negated word in isolation.
    expect(/узнай правду пока не поздно/i.test(allCopy)).toBe(false);
    // Every literal «приговор» in the module must be the negated «не приговор».
    const verdictHits = allCopy.match(/приговор/gi) ?? [];
    for (const _ of verdictHits) {
      expect(/не\s+приговор/i.test(allCopy)).toBe(true);
    }
  });
});
