// Phase-6 limit-copy helper tests (D-09/D-10 + D-04). The two PURE helpers compose the
// remaining-count line and the per-user paywall reset countdown from brand-safe templates.
// Both live in limitCopy.ts so reading/copy.test.ts's ban-list scan reaches their constants
// (PAYWALL_RESET_LEAD etc. live in copy.ts); here we test the interpolation contracts:
// clamp ≥0, NaN-guard, RU plural день/дня/дней, the absolute genitive date, and the «совсем
// скоро» fallback (never «NaN», never empty).

import { describe, expect, it } from "vitest";

import { BANNED_BRAND_TOKENS } from "./copy";
import { formatRemaining, formatReset } from "./limitCopy";

describe("formatRemaining (D-09 count line «Осталось N из M»)", () => {
  it("composes «Осталось N из M» for a normal in-range count", () => {
    expect(formatRemaining(2, 3)).toBe("Осталось 2 из 3");
    expect(formatRemaining(1, 3)).toBe("Осталось 1 из 3");
  });

  it("clamps a negative left to 0 (never shows «Осталось -1 …»)", () => {
    expect(formatRemaining(-1, 3)).toBe("Осталось 0 из 3");
    expect(formatRemaining(-5, 3)).toBe("Осталось 0 из 3");
  });

  it("shows «Осталось 0 из M» when exhausted (the profile may render this)", () => {
    expect(formatRemaining(0, 3)).toBe("Осталось 0 из 3");
  });

  it("guards NaN on either argument with a safe fallback (never «NaN из …»)", () => {
    expect(formatRemaining(Number.NaN, 3)).not.toContain("NaN");
    expect(formatRemaining(2, Number.NaN)).not.toContain("NaN");
    // The fallback is the empty string so the caller renders nothing (non-essential chrome).
    expect(formatRemaining(Number.NaN, 3)).toBe("");
    expect(formatRemaining(2, Number.NaN)).toBe("");
  });

  it("carries no banned brand token", () => {
    expect(BANNED_BRAND_TOKENS.test(formatRemaining(2, 3))).toBe(false);
  });
});

describe("formatReset (D-04 paywall countdown)", () => {
  // A fixed "now" so the relative/absolute split is deterministic.
  const now = new Date("2026-06-15T12:00:00Z");

  it("returns «через 1 день» when the reset is ~1 day out (RU singular)", () => {
    const resetAt = new Date("2026-06-16T12:00:00Z");
    expect(formatReset(resetAt, now)).toBe("через 1 день");
  });

  it("returns «через 2 дня» when the reset is ~2 days out (RU 2–4 form)", () => {
    const resetAt = new Date("2026-06-17T11:00:00Z");
    expect(formatReset(resetAt, now)).toBe("через 2 дня");
  });

  it("accepts an ISO string for resetAt (the backend reset_at is a string)", () => {
    expect(formatReset("2026-06-16T12:00:00Z", now)).toBe("через 1 день");
  });

  it("returns an absolute RU-genitive date beyond ~48h (e.g. «20 июня»)", () => {
    const resetAt = new Date("2026-06-20T12:00:00Z");
    expect(formatReset(resetAt, now)).toBe("20 июня");
  });

  it("returns «совсем скоро» (never «NaN»/empty) when resetAt is absent or invalid", () => {
    expect(formatReset("", now)).toBe("совсем скоро");
    expect(formatReset("not-a-date", now)).toBe("совсем скоро");
    // @ts-expect-error — runtime guard for a null reset_at coming off the wire.
    expect(formatReset(null, now)).toBe("совсем скоро");
    expect(formatReset("not-a-date", now)).not.toContain("NaN");
  });

  it("never produces «через 0 дней» at the boundary — a sub-day reset rounds up to 1 день", () => {
    const resetAt = new Date("2026-06-15T18:00:00Z"); // 6h out
    expect(formatReset(resetAt, now)).toBe("через 1 день");
  });

  it("carries no banned brand token for any branch", () => {
    expect(BANNED_BRAND_TOKENS.test(formatReset("2026-06-16T12:00:00Z", now))).toBe(false);
    expect(BANNED_BRAND_TOKENS.test(formatReset("2026-06-20T12:00:00Z", now))).toBe(false);
    expect(BANNED_BRAND_TOKENS.test(formatReset("bad", now))).toBe(false);
  });
});
