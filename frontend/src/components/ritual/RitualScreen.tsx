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
import { DeckShuffle } from "./DeckShuffle";
import { Particles } from "./Particles";

/** Phrase cadence (ms) — how slowly the ritual headlines crossfade while we wait. Decoupled from
 *  the reveal timing below, so a calmer cadence never delays the actual result. */
export const BEAT_MS = 2400;

/** Minimum on-screen ritual time before the reveal — keeps the shuffle feeling like a real ritual
 *  even when the cards arrive fast, WITHOUT being tied to how many phrases have shown. */
export const MIN_DWELL_MS = 3500;

/** Skip becomes active only from this beat onward (D-08: after the first beat). */
const SKIP_UNLOCK_BEAT = 1;

// Locked compositor-only crossfade tokens (UI-SPEC): opacity + a small y, ease.
const BEAT_TRANSITION = { duration: 0.6, ease: "easeInOut" as const };

export function RitualScreen() {
  const reading = useSelection((s) => s.reading);
  const startFailure = useSelection((s) => s.startFailure);

  // The current beat index (0..RITUAL_BEATS.length-1). Drives the crossfade headline.
  const [beat, setBeat] = useState(0);
  // True once the beat timeline has played its minimum (all beats shown). The reveal waits for
  // BOTH this and the cards, so the ritual always plays in full — never a flash, even if the
  // backgrounded generation finished first.
  const [minDwellPassed, setMinDwellPassed] = useState(false);

  // Guard against React StrictMode's dev double-mount firing two timelines (AuthGate pattern).
  const startedRef = useRef(false);
  // True once the flow has left the ritual (reveal, skip, or failure-bounce) so a late tick can't re-fire.
  const finishedRef = useRef(false);

  // The cards are ready once the backgrounded POST /api/readings deposited a non-empty reading.
  const ready = reading !== null && reading.cards.length > 0;

  // Complete the ritual: fire the completion haptic once, then advance to reveal (READ-07).
  // Idempotent; `goTo` read at call-time (getState) so this callback stays stable.
  const finish = useRef(() => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    haptic.notify("success");
    useSelection.getState().goTo("reveal");
  }).current;

  // Phrase cadence: CYCLE the headlines while we wait, so the shuffle never freezes on one line
  // during a longer generation. Purely visual — it does NOT gate the reveal.
  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    let active = true;
    const interval = setInterval(() => {
      if (!active) return;
      if (finishedRef.current) {
        clearInterval(interval);
        return;
      }
      setBeat((prev) => (prev + 1) % RITUAL_BEATS.length);
    }, BEAT_MS);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, []);

  // Minimum ritual dwell — a fixed, short window (not tied to the phrase count) so the reveal is
  // never a flash, but a fast generation isn't held back by a slow phrase cadence.
  useEffect(() => {
    const t = setTimeout(() => setMinDwellPassed(true), MIN_DWELL_MS);
    return () => clearTimeout(t);
  }, []);

  // Reveal once BOTH the minimum dwell has passed AND the cards have landed.
  useEffect(() => {
    if (ready && minDwellPassed) finish();
  }, [ready, minDwellPassed, finish]);

  // Generation failed underneath the ritual → leave the ritual; the selection screen surfaces the
  // reason (throttle toast / paywall sheet / §9.8 band) on return.
  useEffect(() => {
    if (!startFailure || finishedRef.current) return;
    finishedRef.current = true;
    haptic.notify("error");
    useSelection.getState().goTo("selection");
  }, [startFailure]);

  // Tap-to-skip: a tap-anywhere completion, but ONLY after the first beat (D-08) AND once the
  // cards are ready — skipping earlier would land on an empty reveal.
  const canSkip = beat >= SKIP_UNLOCK_BEAT && ready;
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

      {/* GSAP deck shuffle — the ritual centrepiece (lazy-loaded chunk; calm fan→gather loop, a
          static fan on reduced-motion). Sits above the beat headline. */}
      <div className="relative z-10 mb-2">
        <DeckShuffle />
      </div>

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
