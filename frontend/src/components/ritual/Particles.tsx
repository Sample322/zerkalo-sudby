// Particles — the ritual's compositor-only ambient field (READ-07 / UI-03 / D-10).
// A fixed cap of small deck-tinted dots, each looping a tiny `y` drift + `opacity` pulse
// with a per-particle delay/duration offset, so the dark canvas under the beats feels alive
// without ever leaving the compositor.
//
// This renders INSIDE FlowRoot's <LazyMotion features={domAnimation}>, so every dot is an
// `m.div` from "motion/react-m" — NEVER a stray full `motion.*` (D-10 / PATTERNS Pitfall 5).
// HARD CONTRACT (D-10 / RESEARCH Pitfall 2): the ONLY animated values are `transform`
// (`y` / `scale`) and `opacity`. NEVER animate `top`/`left`/`width`/`height`/`box-shadow`/
// `background`/`border`/`font-size` — `left`/`top` here are STATIC layout (set once, never
// animated). The count is capped by a module constant instead of any reduced-motion downgrade
// (D-10 forbids the `prefers-reduced-motion` path; the cap is how we hold the 60fps budget).
// The whole field is `aria-hidden` — it is purely decorative atmosphere.

import * as m from "motion/react-m";

/** Fixed particle count — capped at ~12–16 to hold the 60fps budget (D-10 / UI-SPEC), no reduced-motion path. */
const PARTICLE_COUNT = 14;

/** One particle's static placement + its per-dot motion offsets (deterministic, index-derived). */
interface Particle {
  id: string;
  /** Static horizontal placement (%) — set once, NEVER animated. */
  left: number;
  /** Static vertical placement (%) — set once, NEVER animated. */
  top: number;
  /** Dot diameter (px) — static. */
  size: number;
  /** Loop duration (s) for this dot's drift/pulse. */
  duration: number;
  /** Stagger so the field shimmers organically rather than pulsing in lockstep. */
  delay: number;
  /** Vertical drift amplitude (px) — animated via `transform: translateY` only. */
  drift: number;
}

// Build the field once at module load: a stable, deterministic spread of dots. Placement is
// index-derived (not Math.random) so the layout is stable across renders and StrictMode
// re-mounts — the *motion* supplies the life, the positions stay put.
const PARTICLES: readonly Particle[] = Array.from(
  { length: PARTICLE_COUNT },
  (_, i): Particle => {
    // Golden-ratio-ish scatter keeps the dots from clustering on a visible grid.
    const left = (i * 61.8) % 100;
    const top = (i * 38.2 + (i % 3) * 17) % 100;
    return {
      id: `ritual-particle-${i}`,
      left,
      top,
      size: 3 + (i % 3),
      duration: 2.4 + (i % 5) * 0.45,
      delay: (i % 7) * 0.32,
      drift: 10 + (i % 4) * 4,
    };
  },
);

// A decorative, deck-tinted, strictly compositor-only particle field for the ritual canvas.
// Tinted with var(--deck-accent) via color-mix (PATTERNS Shared 1) so it shifts per deck.
export function Particles() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 overflow-hidden"
    >
      {PARTICLES.map((p) => (
        <m.div
          key={p.id}
          className="absolute rounded-full"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size,
            height: p.size,
            background:
              "color-mix(in srgb, var(--deck-accent) 70%, transparent)",
          }}
          initial={{ opacity: 0, y: 0, scale: 0.8 }}
          animate={{ opacity: [0, 0.7, 0], y: [0, -p.drift, 0], scale: [0.8, 1, 0.8] }}
          transition={{
            duration: p.duration,
            delay: p.delay,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      ))}
    </div>
  );
}

export default Particles;
