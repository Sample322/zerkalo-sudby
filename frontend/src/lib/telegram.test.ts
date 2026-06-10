import { afterEach, describe, expect, it, vi } from "vitest";
import { getInitData } from "./telegram";

describe("getInitData", () => {
  afterEach(() => {
    // Reset the injected Telegram namespace and any env stubs between tests.
    delete (window as { Telegram?: unknown }).Telegram;
    vi.unstubAllEnvs();
  });

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
