// Particles — the ritual's compositor-only ambient field (READ-07 / UI-03 / D-10).
// A fixed cap of small deck-tinted motes, each looping a tiny `y` drift + `opacity` pulse with a
// per-particle delay/duration offset, so the dark canvas under the beats feels alive without ever
// leaving the compositor. A STATIC glow (box-shadow, never animated) makes each mote read as
// starlight rather than a flat dot.
//
// Renders INSIDE FlowRoot's <LazyMotion features={domAnimation}>, so every mote is an `m.div` from
// "motion/react-m". HARD CONTRACT (D-10 / Pitfall 2): the ONLY animated values are `transform`
// (`y`/`scale`) and `opacity`. `left`/`top`/`box-shadow` here are STATIC. The count is capped by a
// module constant (no reduced-motion downgrade — the cap holds the 60fps budget). aria-hidden.

import * as m from "motion/react-m";

/** Fixed particle count — capped to hold the 60fps budget (D-10 / UI-SPEC). */
const PARTICLE_COUNT = 16;

/** One particle's static placement + its per-mote motion offsets (deterministic, index-derived). */
interface Particle {
  id: string;
  left: number;
  top: number;
  size: number;
  duration: number;
  delay: number;
  drift: number;
}

// Build the field once at module load: a stable, deterministic spread (index-derived, not
// Math.random) so the layout is stable across renders + StrictMode re-mounts.
const PARTICLES: readonly Particle[] = Array.from(
  { length: PARTICLE_COUNT },
  (_, i): Particle => {
    const left = (i * 61.8) % 100;
    const top = (i * 38.2 + (i % 3) * 17) % 100;
    return {
      id: `ritual-particle-${i}`,
      left,
      top,
      size: 2 + (i % 3),
      duration: 2.4 + (i % 5) * 0.45,
      delay: (i % 7) * 0.32,
      drift: 10 + (i % 4) * 4,
    };
  },
);

// A decorative, deck-tinted, strictly compositor-only mote field for the ritual canvas.
export function Particles() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
      {PARTICLES.map((p) => (
        <m.div
          key={p.id}
          className="absolute rounded-full"
          style={{
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size,
            height: p.size,
            background: "var(--deck-soft)",
            boxShadow: "0 0 7px color-mix(in srgb, var(--deck-glow) 70%, transparent)",
          }}
          initial={{ opacity: 0, y: 0, scale: 0.8 }}
          animate={{ opacity: [0, 0.85, 0], y: [0, -p.drift, 0], scale: [0.8, 1, 0.8] }}
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
