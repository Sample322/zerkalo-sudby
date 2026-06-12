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

// READ-08 / D-09 — a single tap-to-flip 3D card. The flip is a COMPOSITOR-ONLY rotateY
// (transform) with a spring (260/26); the parent owns `flipped` so RevealScreen can
// orchestrate «Раскрыть все». The edge-glow is the OPACITY of a pre-rendered accent
// border layer — never an animated box-shadow/layout prop (Pitfall 2). A light haptic
// fires once the flip settles (UI-03). The 120×192 button satisfies the ≥44px tap floor.
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
        {/* Back (рубашка) at 0deg — a deck-tinted card back. */}
        <div
          aria-hidden="true"
          style={{
            ...FACE,
            display: "grid",
            placeItems: "center",
            background: "linear-gradient(150deg, var(--deck-deep), var(--deck-bg))",
            border: "1px solid color-mix(in srgb, var(--deck-accent) 40%, transparent)",
          }}
        >
          <span
            aria-hidden="true"
            style={{
              fontFamily: "ui-serif, Georgia, serif",
              fontSize: 34,
              color: "var(--deck-accent)",
              opacity: 0.85,
            }}
          >
            ✦
          </span>
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
