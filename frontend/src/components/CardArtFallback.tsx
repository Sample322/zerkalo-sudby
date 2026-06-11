import type { CSSProperties } from "react";

interface CardArtProps {
  /** Card art URL. In Phase 2 this is always null/absent (no deck_cards seeded). */
  src?: string | null;
  /** Accessible name for the card slot. */
  alt: string;
  /** Optional sigil; defaults to a deck-level mark when no per-card glyph is given. */
  glyph?: string;
}

const FRAME: CSSProperties = {
  width: 120,
  height: 192,
  borderRadius: 12,
  display: "block",
};

// DECK-05: when a card has no art, render an atmospheric deck-tinted CSS/SVG
// placeholder (role="img", no <img>, no network request) instead of a broken image.
export function CardArt({ src, alt, glyph }: CardArtProps) {
  if (src) {
    return (
      <img
        src={src}
        alt={alt}
        width={120}
        height={192}
        loading="lazy"
        style={{ ...FRAME, objectFit: "cover" }}
      />
    );
  }

  const sigil = glyph ?? (alt.trim().charAt(0).toUpperCase() || "✦");

  return (
    <div
      role="img"
      aria-label={alt}
      style={{
        ...FRAME,
        position: "relative",
        overflow: "hidden",
        background: "linear-gradient(160deg, var(--deck-bg), var(--deck-deep))",
        border: "1px solid color-mix(in srgb, var(--deck-accent) 35%, transparent)",
      }}
    >
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(80% 60% at 50% 18%, color-mix(in srgb, var(--deck-accent) 22%, transparent), transparent 70%)",
        }}
      />
      <svg
        viewBox="0 0 100 160"
        aria-hidden="true"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      >
        <text
          x="50"
          y="92"
          textAnchor="middle"
          fontSize="46"
          fontFamily="ui-serif, Georgia, serif"
          fill="var(--deck-accent)"
        >
          {sigil}
        </text>
      </svg>
    </div>
  );
}

export default CardArt;
