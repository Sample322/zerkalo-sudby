import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { hasSeenOnboarding, markOnboardingSeen } from "./useOnboardingSeen";

const KEY = "zerkalo.onboarding_completed";

beforeEach(() => {
  localStorage.removeItem(KEY);
});

afterEach(() => {
  localStorage.removeItem(KEY);
});

describe("useOnboardingSeen (ONB-04 / D-11)", () => {
  it("hasSeenOnboarding is false initially", () => {
    expect(hasSeenOnboarding()).toBe(false);
  });

  it("hasSeenOnboarding is true after markOnboardingSeen", () => {
    markOnboardingSeen();
    expect(hasSeenOnboarding()).toBe(true);
    // The flag persists in localStorage under the documented key.
    expect(localStorage.getItem(KEY)).toBe("1");
  });

  it("never throws (graceful even if storage were unavailable)", () => {
    expect(() => hasSeenOnboarding()).not.toThrow();
    expect(() => markOnboardingSeen()).not.toThrow();
  });
});
