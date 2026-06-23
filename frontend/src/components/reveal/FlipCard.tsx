import { useRef, type CSSProperties } from "react";
import * as m from "motion/react-m";

import { CardArt } from "../CardArtFallback";
import { haptic } from "../../lib/telegram";
import { EASE, SPRING } from "../../lib/motion";
import type { MockReadingCard } from "../../reading/types";

/**
 * A subtle gold spark burst at the just-revealed card (lazy `@tsparticles/confetti` → its own
 * chunk, never in the initial bundle). Tuned to a quiet astral sparkle, not casino confetti:
 * few particles, gold/lilac, small scalar. No-op when the element isn't laid out (jsdom/tests),
 * and `disableForReducedMotion` honours the OS preference.
 */
function fireSparks(el: HTMLButtonElement | null): void {
  if (!el || typeof window === "undefined") return;
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return; // not painted (tests) → skip entirely
  const x = ((r.left + r.width / 2) / window.innerWidth) * 100;
  const y = ((r.top + r.height / 2) / window.innerHeight) * 100;
  import("@tsparticles/confetti")
    .then(({ confetti }) =>
      confetti({
        position: { x, y },
        count: 16,
        spread: 70,
        startVelocity: 16,
        gravity: 0.55,
        decay: 0.92,
        ticks: 70,
        scalar: 0.7,
        shapes: ["circle", "star"],
        colors: ["#e5d3a3", "#c9a45c", "#d8c7e0"],
        disableForReducedMotion: true,
      }),
    )
    .catch(() => {
      /* confetti chunk failed / unsupported — the flip + edge-glow already carry the reveal */
    });
}

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
  const btnRef = useRef<HTMLButtonElement>(null);
  return (
    <button
      ref={btnRef}
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
        animate={{ rotateY: flipped ? 180 : 0, y: flipped ? -6 : 0 }}
        transition={SPRING.card}
        onAnimationComplete={() => {
          if (flipped) {
            haptic.impact("light");
            fireSparks(btnRef.current);
          }
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

        {/* Front (the card face, reused from CardArt) at 180deg. Overflow-clipped so the shimmer
            sweep stays within the card silhouette. */}
        <div aria-hidden="true" style={{ ...FACE, transform: "rotateY(180deg)", overflow: "hidden" }}>
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
          {/* Shimmer — a single diagonal light sweep just after the flip settles (transform/opacity
              only, blended for a metal-leaf gleam). One-shot, gated on `flipped`. */}
          <m.div
            aria-hidden="true"
            initial={false}
            animate={
              flipped
                ? { x: ["-140%", "140%"], opacity: [0, 0.85, 0] }
                : { x: "-140%", opacity: 0 }
            }
            transition={flipped ? { duration: 0.7, delay: 0.32, ease: EASE.softOut } : { duration: 0.2 }}
            style={{
              position: "absolute",
              top: -4,
              bottom: -4,
              width: "55%",
              background:
                "linear-gradient(105deg, transparent, color-mix(in srgb, var(--deck-soft) 70%, transparent), transparent)",
              mixBlendMode: "screen",
              pointerEvents: "none",
            }}
          />
        </div>
      </m.div>
    </button>
  );
}

export default FlipCard;
