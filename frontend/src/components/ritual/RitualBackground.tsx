import { useMemo } from "react";

// The fixed, app-wide atmosphere (mounted once in App, behind every screen at z-0). It reads
// the live deck CSS vars, so it recolours through the body transition when the active deck
// changes — obsidian depth + a breathing glow at the crown + a starfield + a whisper of grain.
// Pure CSS/divs (no motion runtime) so it's alive even during the pre-LazyMotion auth boot.

interface Star {
  top: string;
  left: string;
  size: number;
  delay: string;
  twinkle: boolean;
}

// Deterministic starfield (seeded) — organic spread without a random reflow each mount.
function buildStars(count: number): Star[] {
  let seed = 0x9e3779b9;
  const rand = () => {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return Array.from({ length: count }, () => {
    const size = rand() < 0.78 ? 1.5 : 2.5 + rand() * 1.5;
    return {
      top: `${(rand() * 92).toFixed(2)}%`,
      left: `${(rand() * 96).toFixed(2)}%`,
      size: Number(size.toFixed(1)),
      delay: `${(rand() * 4).toFixed(2)}s`,
      twinkle: rand() < 0.55,
    };
  });
}

const GRAIN =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")";

export function RitualBackground() {
  const stars = useMemo(() => buildStars(34), []);

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      {/* Obsidian depth — deck deep collapsing into deck bg. */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(125% 92% at 50% -8%, color-mix(in srgb, var(--deck-deep) 82%, transparent), var(--deck-bg) 60%)",
        }}
      />
      {/* Crown glow — slow breath of the deck's starlight. */}
      <div
        className="zs-glow absolute left-1/2 top-0 h-[360px] w-[360px] rounded-full"
        style={{
          background:
            "radial-gradient(circle, color-mix(in srgb, var(--deck-glow) 30%, transparent), transparent 66%)",
        }}
      />
      {/* Starfield. */}
      {stars.map((s, i) => (
        <span
          key={i}
          className={`absolute rounded-full${s.twinkle ? " zs-twinkle" : ""}`}
          style={{
            top: s.top,
            left: s.left,
            width: s.size,
            height: s.size,
            background: "var(--deck-soft)",
            opacity: s.twinkle ? undefined : 0.28,
            animationDelay: s.delay,
            boxShadow: s.size > 2 ? "0 0 6px var(--deck-soft)" : undefined,
          }}
        />
      ))}
      {/* Grain — barely-there texture so flat fields never look plasticky. */}
      <div
        className="absolute inset-0"
        style={{ backgroundImage: GRAIN, backgroundRepeat: "repeat", opacity: 0.05, mixBlendMode: "overlay" }}
      />
      {/* Floor vignette — grounds the sticky CTAs. */}
      <div
        className="absolute inset-x-0 bottom-0 h-1/3"
        style={{ background: "linear-gradient(to top, var(--deck-bg), transparent)" }}
      />
    </div>
  );
}

export default RitualBackground;
