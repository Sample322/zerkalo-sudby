// A physical deck that fans out and gathers back while the reading is prepared — the ritual's
// centrepiece. GSAP is LAZY-imported (dynamic import → its own chunk, never in the initial
// bundle) and only here, so the landing payload is untouched. Compositor-only (transform/opacity)
// and calm, never chaotic (no casino flurry). On reduced-motion or a load failure the cards stay
// in a static fan, so nothing ever breaks — the ritual's beats/sigil still carry the moment.

import { useEffect, useRef } from "react";

/** How many card backs are in the shuffling deck. */
const CARD_COUNT = 6;

/** One ornate deck-tinted card back (mirrors FlipCard's back, compact). */
function cardBackStyle(): React.CSSProperties {
  return {
    position: "absolute",
    left: "50%",
    top: "50%",
    width: 64,
    height: 100,
    marginLeft: -32,
    marginTop: -50,
    borderRadius: 9,
    background: "linear-gradient(152deg, var(--deck-deep), var(--deck-bg) 80%)",
    border: "1px solid color-mix(in srgb, var(--deck-accent) 46%, transparent)",
    boxShadow: "inset 0 0 14px color-mix(in srgb, var(--deck-glow) 16%, transparent)",
    display: "grid",
    placeItems: "center",
    fontFamily: "var(--font-display), Georgia, serif",
    fontSize: 22,
    color: "color-mix(in srgb, var(--deck-soft) 80%, transparent)",
    willChange: "transform",
  };
}

export function DeckShuffle() {
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);

  useEffect(() => {
    const cards = cardsRef.current.filter(Boolean) as HTMLDivElement[];
    if (cards.length === 0) return;

    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const mid = (CARD_COUNT - 1) / 2;

    // Reduced-motion: settle into a calm static fan, no timeline.
    if (reduce) {
      for (const [i, el] of cards.entries()) {
        el.style.transform = `translate(${(i - mid) * 18}px, 0) rotate(${(i - mid) * 4}deg)`;
      }
      return;
    }

    let killed = false;
    let cleanup: (() => void) | undefined;

    import("gsap")
      .then(({ gsap }) => {
        if (killed) return;
        const tl = gsap.timeline({
          repeat: -1,
          repeatDelay: 0.5,
          defaults: { ease: "power3.inOut" },
        });
        // Fan out — each card slides + tilts off the stack.
        tl.to(cards, {
          x: (i: number) => (i - mid) * 30,
          y: (i: number) => Math.abs(i - mid) * -4,
          rotate: (i: number) => (i - mid) * 7,
          duration: 0.85,
          stagger: 0.05,
        });
        // Gather back into the deck (from the outer cards in).
        tl.to(
          cards,
          {
            x: 0,
            y: 0,
            rotate: 0,
            duration: 0.85,
            stagger: { each: 0.05, from: "end" },
          },
          "+=0.55",
        );
        cleanup = () => tl.kill();
      })
      .catch(() => {
        // gsap chunk failed to load — leave the static stack; the ritual still reads fine.
      });

    return () => {
      killed = true;
      cleanup?.();
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      className="relative z-10"
      style={{ width: 200, height: 150 }}
    >
      {Array.from({ length: CARD_COUNT }, (_, i) => (
        <div
          key={i}
          ref={(el) => {
            cardsRef.current[i] = el;
          }}
          style={cardBackStyle()}
        >
          ✦
        </div>
      ))}
    </div>
  );
}

export default DeckShuffle;
