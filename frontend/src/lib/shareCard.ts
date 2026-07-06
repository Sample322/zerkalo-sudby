// Privacy-safe share-card (UI-06). Renders a completed reading — deck name, spread name, the drawn
// cards, and a short closing line — to an image entirely CLIENT-side (an offscreen canvas), then
// shares it via the Web Share API with a download fallback. The personal QUESTION is EXCLUDED by
// construction: `ShareCardInput` has no question field, so it can never be drawn. Framework-free so
// it unit-tests without React. Brand-safe: no «AI/нейросеть/модель» text anywhere on the card.

export interface ShareCardCard {
  name: string;
  positionTitle: string;
  orientation: "upright" | "reversed";
}

/** The ONLY data the card renders. Deliberately has NO `question` field (privacy — UI-06). */
export interface ShareCardInput {
  deckName: string;
  spreadName: string;
  cards: ShareCardCard[];
  /** A single evocative line (the reading's closing phrase) — never the question. */
  summary: string;
}

const WIDTH = 1080;
const HEIGHT = 1350;
const MARGIN = 96;
const OBSIDIAN = "#0b0a12";
const OBSIDIAN_2 = "#171326";
const GOLD = "#d9b775";
const MIST = "#e7e2f0";
const MIST_DIM = "#9c96ad";
const MAX_CARDS = 4;

/** Wrap `text` to `maxWidth` using the context's current font; returns the line list. */
function wrapLines(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(/\s+/).filter(Boolean);
  const lines: string[] = [];
  let line = "";
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (ctx.measureText(candidate).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = candidate;
    }
  }
  if (line) lines.push(line);
  return lines;
}

/**
 * Render the share-card to a PNG `Blob` (offscreen canvas, devicePixelRatio-scaled). Rejects if a
 * 2D context or `toBlob` is unavailable (headless/unsupported) so the caller can fall back cleanly.
 */
export async function renderShareCard(input: ShareCardInput): Promise<Blob> {
  const dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH * dpr;
  canvas.height = HEIGHT * dpr;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("share-card: 2D canvas context unavailable");
  ctx.scale(dpr, dpr);

  // Obsidian background + a soft gold vignette (the brand direction).
  const bg = ctx.createLinearGradient(0, 0, 0, HEIGHT);
  bg.addColorStop(0, OBSIDIAN_2);
  bg.addColorStop(1, OBSIDIAN);
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  // Gold hairline frame.
  ctx.strokeStyle = GOLD;
  ctx.lineWidth = 2;
  ctx.globalAlpha = 0.5;
  ctx.strokeRect(MARGIN / 2, MARGIN / 2, WIDTH - MARGIN, HEIGHT - MARGIN);
  ctx.globalAlpha = 1;

  const serif = '"Forum", "Playfair Display", Georgia, serif';
  const body = '"Lora", Georgia, serif';

  // Eyebrow — spread name.
  ctx.textAlign = "center";
  ctx.fillStyle = GOLD;
  ctx.font = `28px ${body}`;
  ctx.fillText(`✦  ${input.spreadName.toUpperCase()}  ✦`, WIDTH / 2, MARGIN + 40);

  // Title — deck name.
  ctx.fillStyle = MIST;
  ctx.font = `76px ${serif}`;
  for (const [i, line] of wrapLines(ctx, input.deckName, WIDTH - MARGIN * 2).slice(0, 2).entries()) {
    ctx.fillText(line, WIDTH / 2, MARGIN + 140 + i * 84);
  }

  // Cards — up to 4, "Позиция — Карта (перевёрнутая?)".
  ctx.font = `36px ${body}`;
  const cards = input.cards.slice(0, MAX_CARDS);
  let y = 460;
  for (const card of cards) {
    ctx.fillStyle = MIST_DIM;
    ctx.fillText(card.positionTitle, WIDTH / 2, y);
    ctx.fillStyle = MIST;
    ctx.font = `44px ${serif}`;
    const glyph = card.orientation === "reversed" ? " ⟲" : "";
    ctx.fillText(`${card.name}${glyph}`, WIDTH / 2, y + 52);
    ctx.font = `36px ${body}`;
    y += 128;
  }

  // Summary — the closing line, wrapped, near the bottom.
  ctx.fillStyle = MIST;
  ctx.font = `italic 38px ${body}`;
  const summaryLines = wrapLines(ctx, input.summary, WIDTH - MARGIN * 2).slice(0, 4);
  const summaryTop = HEIGHT - MARGIN - 120 - (summaryLines.length - 1) * 50;
  summaryLines.forEach((line, i) => ctx.fillText(line, WIDTH / 2, summaryTop + i * 50));

  // Brand mark.
  ctx.fillStyle = GOLD;
  ctx.font = `26px ${body}`;
  ctx.fillText("Зеркало Судьбы", WIDTH / 2, HEIGHT - MARGIN + 4);

  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error("share-card: toBlob returned null"));
    }, "image/png");
  });
}

/**
 * Share the blob via the Web Share API when files are supported, else download it. A user-cancelled
 * share (`AbortError`) is swallowed. Returns `"shared" | "downloaded"` for the caller's UX hint.
 */
export async function shareOrDownload(blob: Blob, filename: string): Promise<"shared" | "downloaded"> {
  const file = new File([blob], filename, { type: "image/png" });
  const nav = navigator as Navigator & {
    canShare?: (data?: unknown) => boolean;
    share?: (data?: unknown) => Promise<void>;
  };
  if (nav.canShare?.({ files: [file] }) && nav.share) {
    try {
      await nav.share({ files: [file], title: "Зеркало Судьбы" });
      return "shared";
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return "shared"; // user cancelled
      // fall through to download on any other share error
    }
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
  return "downloaded";
}
