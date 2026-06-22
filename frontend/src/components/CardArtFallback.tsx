import type { CSSProperties } from "react";

interface CardArtProps {
  /** Card art URL. Until real deck art is uploaded this is null → atmospheric fallback. */
  src?: string | null;
  /** Accessible name for the card slot. */
  alt: string;
  /** Optional sigil; defaults to the card's initial (or a star) when no glyph is given. */
  glyph?: string;
  /** Frame width in px (height derives from the tarot 5:8 ratio). Default 120. */
  width?: number;
  /** Float the card gently (the result/reveal hero treatment). Default false. */
  float?: boolean;
}

// DECK-05: when a card has no art, render an atmospheric deck-tinted CSS/SVG placeholder
// (role="img", no <img>, no network request). The «obsidian + metal» treatment: a double gold
// hairline frame, a radial halo, a luminous serif sigil, and corner ✦ marks — a real card back,
// not a broken-image slot. The same gold frame wraps a real <img> once art exists.
export function CardArt({ src, alt, glyph, width = 120, float = false }: CardArtProps) {
  const height = Math.round((width * 8) / 5);
  const frame: CSSProperties = {
    width,
    height,
    borderRadius: Math.round(width / 10),
    position: "relative",
    flex: "none",
    overflow: "hidden",
    border: "1px solid color-mix(in srgb, var(--deck-accent) 52%, transparent)",
    boxShadow:
      "0 10px 26px rgba(0,0,0,0.5), inset 0 0 22px color-mix(in srgb, var(--deck-glow) 14%, transparent)",
  };

  if (src) {
    return (
      <div role="img" aria-label={alt} className={float ? "zs-float" : undefined} style={frame}>
        <img
          src={src}
          alt=""
          width={width}
          height={height}
          loading="lazy"
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
        />
        <div
          aria-hidden="true"
          style={{
            position: "absolute",
            inset: 5,
            borderRadius: Math.round(width / 14),
            border: "1px solid color-mix(in srgb, var(--deck-soft) 30%, transparent)",
          }}
        />
      </div>
    );
  }

  const sigil = glyph ?? (alt.trim().charAt(0).toUpperCase() || "✦");

  return (
    <div
      role="img"
      aria-label={alt}
      className={float ? "zs-float" : undefined}
      style={{
        ...frame,
        background: "linear-gradient(158deg, var(--deck-deep), var(--deck-bg) 78%)",
      }}
    >
      {/* Halo behind the sigil. */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(78% 58% at 50% 40%, color-mix(in srgb, var(--deck-glow) 26%, transparent), transparent 70%)",
        }}
      />
      {/* Inner hairline frame. */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: Math.round(width / 22),
          borderRadius: Math.round(width / 16),
          border: "1px solid color-mix(in srgb, var(--deck-accent) 30%, transparent)",
        }}
      />
      {/* Luminous serif sigil. */}
      <svg
        viewBox="0 0 100 160"
        aria-hidden="true"
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
      >
        <text
          x="50"
          y="94"
          textAnchor="middle"
          fontSize="48"
          fontFamily="var(--font-display), Georgia, serif"
          fontWeight="600"
          fill="var(--deck-soft)"
          style={{ filter: "drop-shadow(0 0 8px color-mix(in srgb, var(--deck-glow) 60%, transparent))" }}
        >
          {sigil}
        </text>
      </svg>
      {/* Corner marks. */}
      <span style={cornerStyle(width, "tl")}>✦</span>
      <span style={cornerStyle(width, "br")}>✦</span>
    </div>
  );
}

function cornerStyle(width: number, corner: "tl" | "br"): CSSProperties {
  const inset = Math.round(width / 14);
  return {
    position: "absolute",
    [corner === "tl" ? "top" : "bottom"]: inset,
    [corner === "tl" ? "left" : "right"]: inset,
    fontSize: Math.max(9, Math.round(width / 13)),
    lineHeight: 1,
    color: "color-mix(in srgb, var(--deck-accent) 68%, transparent)",
  };
}

export default CardArt;
