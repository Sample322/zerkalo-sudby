// RitualScreen — the emotional centerpiece (READ-07 / D-08). The real ~3s, 3-beat ritual:
// «Колода слышит вопрос…» → «Карты перемешиваются…» → «Три знака уже рядом…», each crossfading
// over a breathing sigil halo on the deck-tinted canvas, with a dimming vignette and the
// compositor-only <Particles/> field underneath. On the final beat a success haptic fires and the
// flow advances to `reveal`. Tap-to-skip is active ONLY after the first beat (D-08). During the
// ~3s the reveal/result card faces are mounted warm offscreen so the next screen paints with no
// pop-in (D-10 / RESEARCH Pitfall 6).
//
// FlowRoot provides <MotionConfig reducedMotion="never"> + <LazyMotion features={domAnimation}>,
// so all motion uses `m.*` from "motion/react-m". HARD CONTRACT: every animated value is
// `transform` (`y`/`scale`) or `opacity` — no banned layout/paint props (D-10 / Pitfall 2). The
// timer effect mirrors AuthGate's discipline: a StrictMode ref guard, an `active` flag, and a
// cleanup that clears the interval. All copy is from reading/copy.ts, rendered as React text nodes.

import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { haptic } from "../../lib/telegram";
import { useSelection } from "../../stores/selection";
import { RITUAL_BEATS, RITUAL_SKIP } from "../../reading/copy";
import { CardArt } from "../CardArtFallback";
import { Particles } from "./Particles";

/** Per-beat dwell (ms). 3 beats × ~1000ms ≈ the locked ~3s ritual (UI-SPEC / D-08). */
const BEAT_MS = 1000;

/** Skip becomes active only from this beat onward (D-08: after the first beat). */
const SKIP_UNLOCK_BEAT = 1;

// Locked compositor-only crossfade tokens (UI-SPEC): opacity + a small y, ease.
const BEAT_TRANSITION = { duration: 0.6, ease: "easeInOut" as const };

export function RitualScreen() {
  const reading = useSelection((s) => s.reading);

  // The current beat index (0..RITUAL_BEATS.length-1). Drives the crossfade headline.
  const [beat, setBeat] = useState(0);

  // Guard against React StrictMode's dev double-mount firing two timelines (AuthGate pattern).
  const startedRef = useRef(false);
  // True once the timeline has completed (via timer or skip) so a late tick/skip can't re-fire.
  const finishedRef = useRef(false);

  // Complete the ritual: fire the completion haptic once, then advance to reveal (READ-07).
  // Idempotent; `goTo` read at call-time (getState) so this callback stays stable.
  const finish = useRef(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    haptic.notify("success");
    const goTo = useSelection.getState().goTo;
    goTo("reveal");
  }).current;

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    let active = true;
    const interval = setInterval(() => {
      if (!active) return;
      setBeat((prev) => {
        const next = prev + 1;
        if (next >= RITUAL_BEATS.length) {
          clearInterval(interval);
          finish();
          return prev;
        }
        return next;
      });
    }, BEAT_MS);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [finish]);

  // Tap-to-skip: a tap-anywhere completion, but ONLY once the first beat has passed (D-08).
  const canSkip = beat >= SKIP_UNLOCK_BEAT;
  const handleSkip = () => {
    if (!canSkip) return;
    finish();
  };

  const headline = RITUAL_BEATS[beat] ?? RITUAL_BEATS[RITUAL_BEATS.length - 1];

  return (
    <main
      onClick={handleSkip}
      className="relative flex min-h-full flex-1 flex-col items-center justify-center overflow-hidden px-8 py-12 text-center"
      style={{ cursor: canSkip ? "pointer" : "default" }}
    >
      {/* Compositor-only ambient field, deck-tinted, underneath everything. */}
      <Particles />

      {/* Dimming vignette — ONLY opacity animates (D-10). */}
      <m.div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 90% at 50% 42%, transparent, color-mix(in srgb, var(--deck-bg) 92%, #000) 82%)",
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />

      {/* Breathing sigil halo behind the words — a slow opacity/scale pulse (compositor-only). */}
      <m.div
        aria-hidden="true"
        className="pointer-events-none absolute"
        style={{
          width: 260,
          height: 260,
          borderRadius: "50%",
          background:
            "radial-gradient(circle, color-mix(in srgb, var(--deck-glow) 26%, transparent), transparent 66%)",
        }}
        initial={{ opacity: 0.4, scale: 0.92 }}
        animate={{ opacity: [0.4, 0.75, 0.4], scale: [0.92, 1.08, 0.92] }}
        transition={{ duration: 3.4, repeat: Infinity, ease: "easeInOut" }}
      />

      {/* The beat headline — nested AnimatePresence keyed on the beat index for the crossfade. */}
      <div className="relative z-10 flex min-h-[7rem] items-center justify-center">
        <AnimatePresence mode="wait">
          <m.p
            key={beat}
            className="font-display metal-text max-w-[16rem] text-[30px]"
            style={{ lineHeight: 1.18 }}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={BEAT_TRANSITION}
          >
            {headline}
          </m.p>
        </AnimatePresence>
      </div>

      {/* Tap-to-skip — appears only after the first beat (D-08). */}
      <AnimatePresence>
        {canSkip && (
          <m.button
            type="button"
            onClick={handleSkip}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 0.78, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="pill-ghost absolute bottom-14 z-10 px-5 py-2 text-[14px]"
          >
            {RITUAL_SKIP}
          </m.button>
        )}
      </AnimatePresence>

      {/* Art preload (D-10 / Pitfall 6): mount the drawn faces warm but visually hidden so the
          reveal's first paint is already composited. Pure CSS/SVG (no network). */}
      {reading && reading.cards.length > 0 && (
        <div
          aria-hidden="true"
          className="pointer-events-none absolute opacity-0"
          style={{ left: -9999, top: -9999 }}
        >
          {reading.cards.map((card, i) => (
            <CardArt key={`${card.name}-${i}`} src={null} alt={card.name} />
          ))}
        </div>
      )}
    </main>
  );
}

export default RitualScreen;
