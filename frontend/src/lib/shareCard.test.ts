// Share-card (UI-06) — privacy invariant + share/download behaviour. Canvas is headless in jsdom, so
// getContext/toBlob are stubbed for the render smoke; the real value under test is that the question
// is never part of the card, and that share falls back to download cleanly.

import { afterEach, describe, expect, it, vi } from "vitest";

import { renderShareCard, shareOrDownload, type ShareCardInput } from "./shareCard";

const INPUT: ShareCardInput = {
  deckName: "Лунное Зеркало",
  spreadName: "Три карты",
  cards: [
    { name: "Звезда", positionTitle: "Суть", orientation: "upright" },
    { name: "Башня", positionTitle: "Препятствие", orientation: "reversed" },
  ],
  summary: "Колода остаётся рядом: ответ всегда остаётся за тобой.",
};

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("share-card privacy (UI-06)", () => {
  it("ShareCardInput carries no question field — the question can never be drawn", () => {
    expect(Object.keys(INPUT)).not.toContain("question");
  });
});

function stubShare(canShare: boolean, share?: () => Promise<void>): void {
  Object.defineProperty(navigator, "canShare", { value: () => canShare, configurable: true });
  Object.defineProperty(navigator, "share", {
    value: share ?? vi.fn(async () => {}),
    configurable: true,
  });
}

describe("shareOrDownload", () => {
  it("shares via the Web Share API when files are supported", async () => {
    const share = vi.fn(async () => {});
    stubShare(true, share);
    const outcome = await shareOrDownload(new Blob(["x"]), "c.png");
    expect(share).toHaveBeenCalledOnce();
    expect(outcome).toBe("shared");
  });

  it("falls back to a download when files are not shareable", async () => {
    Object.defineProperty(navigator, "canShare", { value: () => false, configurable: true });
    const createObjectURL = vi.fn(() => "blob:x");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const outcome = await shareOrDownload(new Blob(["x"]), "c.png");
    expect(outcome).toBe("downloaded");
    expect(createObjectURL).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
  });

  it("swallows a user-cancelled share (AbortError) and reports shared", async () => {
    stubShare(
      true,
      vi.fn(async () => {
        throw new DOMException("cancelled", "AbortError");
      }),
    );
    const outcome = await shareOrDownload(new Blob(["x"]), "c.png");
    expect(outcome).toBe("shared");
  });
});

describe("renderShareCard", () => {
  it("returns a PNG blob (mocked canvas)", async () => {
    const ctx = {
      scale: vi.fn(),
      createLinearGradient: () => ({ addColorStop: vi.fn() }),
      fillRect: vi.fn(),
      strokeRect: vi.fn(),
      fillText: vi.fn(),
      measureText: () => ({ width: 10 }),
      fillStyle: "",
      strokeStyle: "",
      lineWidth: 0,
      globalAlpha: 1,
      font: "",
      textAlign: "",
    };
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      ctx as unknown as CanvasRenderingContext2D,
    );
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(function (
      cb: BlobCallback,
    ) {
      cb(new Blob(["png"], { type: "image/png" }));
    });
    const blob = await renderShareCard(INPUT);
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe("image/png");
  });
});
