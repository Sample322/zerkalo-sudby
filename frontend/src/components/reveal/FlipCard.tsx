import type { CSSProperties } from "react";
import * as m from "motion/react-m";

import { CardArt } from "../CardArtFallback";
import { haptic } from "../../lib/telegram";
import type { MockReadingCard } from "../../reading/types";

interface FlipCardProps {
  /** The card to reveal (only the name is needed for the face's accessible label). */
  card: Pick<MockReadingCard, "name">;
  /** Whether the card is turned face-up. Owned by RevealScreen so it can «Раскрыть все». */
  flipped: boolean;
  /** Tap handler — RevealScreen flips this card. */
  onFlip: () => void;
}

const SIZE: CSSProperties = { width: 120, height: 192 };

const FACE: CSSProperties = {
  position: "absolute",
  inset: 0,
  borderRadius: 12,
  backfaceVisibility: "hidden",
  WebkitBackfaceVisibility: "hidden",
};

// READ-08 / D-09 — a single tap-to-flip 3D card. The flip is a COMPOSITOR-ONLY rotateY with a
// spring (260/26); the parent owns `flipped` so RevealScreen can orchestrate «Раскрыть все». The
// edge-glow is the OPACITY of a pre-rendered accent border — never an animated box-shadow/layout
// prop (Pitfall 2). A light haptic fires once the flip settles. The 120×192 button meets the
// ≥44px tap floor.
export function FlipCard({ card, flipped, onFlip }: FlipCardProps) {
  return (
    <button
      type="button"
      onClick={onFlip}
      aria-pressed={flipped}
      aria-label={flipped ? card.name : "Открыть карту"}
      style={{
        ...SIZE,
        perspective: 1000,
        padding: 0,
        border: "none",
        background: "transparent",
        cursor: "pointer",
        display: "block",
      }}
    >
      <m.div
        animate={{ rotateY: flipped ? 180 : 0 }}
        transition={{ type: "spring", stiffness: 260, damping: 26 }}
        onAnimationComplete={() => {
          if (flipped) haptic.impact("light");
        }}
        style={{ ...SIZE, position: "relative", transformStyle: "preserve-3d" }}
      >
        {/* Back (рубашка) at 0deg — an ornate deck-tinted card back: double gold hairline, halo,
            sigil, corner ✦. */}
        <div
          aria-hidden="true"
          style={{
            ...FACE,
            overflow: "hidden",
            background: "linear-gradient(152deg, var(--deck-deep), var(--deck-bg) 78%)",
            border: "1px solid color-mix(in srgb, var(--deck-accent) 50%, transparent)",
            boxShadow: "inset 0 0 20px color-mix(in srgb, var(--deck-glow) 16%, transparent)",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 6,
              borderRadius: 8,
              border: "1px solid color-mix(in srgb, var(--deck-accent) 28%, transparent)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(70% 55% at 50% 44%, color-mix(in srgb, var(--deck-glow) 22%, transparent), transparent 70%)",
            }}
          />
          <span
            style={{
              position: "absolute",
              inset: 0,
              display: "grid",
              placeItems: "center",
              fontFamily: "var(--font-display), Georgia, serif",
              fontSize: 38,
              fontWeight: 600,
              color: "var(--deck-soft)",
              textShadow: "0 0 10px color-mix(in srgb, var(--deck-glow) 55%, transparent)",
            }}
          >
            ✦
          </span>
          <span style={{ position: "absolute", top: 9, left: 10, fontSize: 11, color: "color-mix(in srgb, var(--deck-accent) 70%, transparent)" }}>✦</span>
          <span style={{ position: "absolute", bottom: 9, right: 10, fontSize: 11, color: "color-mix(in srgb, var(--deck-accent) 70%, transparent)" }}>✦</span>
        </div>

        {/* Front (the card face, reused from CardArt) at 180deg. */}
        <div aria-hidden="true" style={{ ...FACE, transform: "rotateY(180deg)" }}>
          <CardArt src={null} alt={card.name} />
          {/* Edge-glow = opacity of a pre-rendered accent border (compositor-only). */}
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              inset: 0,
              borderRadius: 12,
              border: "1px solid var(--deck-accent)",
              boxShadow: "0 0 22px -2px color-mix(in srgb, var(--deck-glow) 70%, transparent)",
              opacity: flipped ? 1 : 0,
              transition: "opacity 280ms cubic-bezier(0.16, 1, 0.3, 1)",
              pointerEvents: "none",
            }}
          />
        </div>
      </m.div>
    </button>
  );
}

export default FlipCard;
