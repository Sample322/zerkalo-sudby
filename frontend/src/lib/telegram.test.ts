import { afterEach, describe, expect, it, vi } from "vitest";
import {
  getColorScheme,
  getContentSafeAreaInsets,
  getInitData,
  getSafeAreaInsets,
  getThemeParams,
  haptic,
} from "./telegram";

afterEach(() => {
  // Reset the injected Telegram namespace and any env stubs between tests.
  delete (window as { Telegram?: unknown }).Telegram;
  vi.unstubAllEnvs();
});

describe("getInitData", () => {
  it("returns the initData string Telegram injects into the WebView", () => {
    const signed = "user=%7B%22id%22%3A42%7D&auth_date=1700000000&hash=abc123";
    (window as { Telegram?: unknown }).Telegram = {
      WebApp: { initData: signed },
    };

    expect(getInitData()).toBe(signed);
  });

  it("returns an empty string (never throws) when Telegram is absent and no dev mock is set", () => {
    // No window.Telegram, and no VITE_DEV_INIT_DATA.
    vi.stubEnv("VITE_DEV_INIT_DATA", "");

    expect(() => getInitData()).not.toThrow();
    expect(getInitData()).toBe("");
  });

  it("returns an empty string when WebApp is present but initData is missing", () => {
    (window as { Telegram?: unknown }).Telegram = { WebApp: {} };
    vi.stubEnv("VITE_DEV_INIT_DATA", "");

    expect(getInitData()).toBe("");
  });
});

describe("theme + safe-area readers default safely outside Telegram (UI-04)", () => {
  it("getColorScheme defaults to 'dark' (premium baseline) when Telegram is absent", () => {
    expect(getColorScheme()).toBe("dark");
  });

  it("getColorScheme reflects Telegram's colorScheme when present", () => {
    (window as { Telegram?: unknown }).Telegram = {
      WebApp: { colorScheme: "light" },
    };
    expect(getColorScheme()).toBe("light");
  });

  it("getThemeParams defaults to an empty object when absent", () => {
    expect(getThemeParams()).toEqual({});
  });

  it("getSafeAreaInsets / getContentSafeAreaInsets default to all-zeros when absent", () => {
    expect(getSafeAreaInsets()).toEqual({ top: 0, bottom: 0, left: 0, right: 0 });
    expect(getContentSafeAreaInsets()).toEqual({
      top: 0,
      bottom: 0,
      left: 0,
      right: 0,
    });
  });

  it("getSafeAreaInsets returns Telegram's insets when present", () => {
    (window as { Telegram?: unknown }).Telegram = {
      WebApp: { safeAreaInset: { top: 44, bottom: 34, left: 0, right: 0 } },
    };
    expect(getSafeAreaInsets()).toEqual({ top: 44, bottom: 34, left: 0, right: 0 });
  });
});

describe("haptic is a callable no-op outside Telegram, and forwards when present", () => {
  it("impact / notify / selection do not throw when Telegram is absent", () => {
    expect(() => haptic.impact()).not.toThrow();
    expect(() => haptic.impact("heavy")).not.toThrow();
    expect(() => haptic.notify("success")).not.toThrow();
    expect(() => haptic.selection()).not.toThrow();
  });

  it("forwards to the Telegram HapticFeedback API with the exact arg values", () => {
    const impactOccurred = vi.fn();
    const notificationOccurred = vi.fn();
    const selectionChanged = vi.fn();
    (window as { Telegram?: unknown }).Telegram = {
      WebApp: {
        HapticFeedback: { impactOccurred, notificationOccurred, selectionChanged },
      },
    };

    haptic.impact(); // default style
    haptic.notify("warning");
    haptic.selection();

    expect(impactOccurred).toHaveBeenCalledWith("light");
    expect(notificationOccurred).toHaveBeenCalledWith("warning");
    expect(selectionChanged).toHaveBeenCalledTimes(1);
  });
});
