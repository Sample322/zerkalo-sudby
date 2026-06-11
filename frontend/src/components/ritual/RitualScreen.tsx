// RitualScreen — the emotional centerpiece (READ-07 / D-08). Replaces the 03-01 stub with the
// real ~3s, 3-beat ritual: «Колода слышит вопрос…» → «Карты перемешиваются…» → «Три знака уже
// рядом…», each crossfading on a dark, deck-tinted canvas with a dimming overlay and the
// compositor-only <Particles/> field underneath. On the final beat a success haptic fires
// (notify("success")) and the flow advances to `reveal`. Tap-to-skip is active ONLY after the
// first beat (D-08). During the ~3s the reveal/result card faces are mounted warm offscreen so
// the next screen paints composited with no pop-in (D-10 / RESEARCH Pitfall 6).
//
// FlowRoot already routes step==="ritual" here and provides <MotionConfig reducedMotion="never">
// + <LazyMotion features={domAnimation}>, so all motion uses `m.*` from "motion/react-m" — NEVER
// a stray full `motion.*` (D-10 / PATTERNS Pitfall 5). HARD CONTRACT: every animated value is
// `transform` (`y`) or `opacity` — no banned layout/paint props (D-10 / Pitfall 2). The timer
// effect mirrors AuthGate's discipline exactly: a ref guard against StrictMode's dev double-mount,
// an `active` flag, and a cleanup that clears the interval — so the timeline can never double-run
// or leak across mounts (threat T-3-07). All copy is sourced from reading/copy.ts (SAFE-06) and
// rendered as React text nodes — no dangerouslySetInnerHTML (threat T-3-05).

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
  // Idempotent — a second call (e.g. the timer landing right as the user skips) is a no-op.
  // `goTo` is read from the store at call-time (getState) so this callback stays stable and the
  // beat-timer effect can run exactly once without re-subscribing on the action's identity.
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
          // Past the last beat's dwell — complete the ritual and stop the timer.
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
      className="relative flex min-h-full flex-1 flex-col items-center justify-center overflow-hidden px-6 py-12 text-center"
      style={{ background: "var(--deck-bg)", cursor: canSkip ? "pointer" : "default" }}
    >
      {/* Compositor-only ambient field, deck-tinted, underneath everything. */}
      <Particles />

      {/* Dimming overlay — ONLY its opacity animates (never box-shadow/background) (D-10). */}
      <m.div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(120% 90% at 50% 40%, transparent, color-mix(in srgb, var(--deck-bg) 92%, #000) 80%)",
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
      />

      {/* The beat headline — nested AnimatePresence keyed on the beat index for the crossfade. */}
      <div className="relative z-10 flex min-h-[6rem] items-center justify-center">
        <AnimatePresence mode="wait">
          <m.p
            key={beat}
            className="max-w-xs text-2xl font-semibold"
            style={{ color: "var(--deck-soft)", lineHeight: 1.2 }}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={BEAT_TRANSITION}
          >
            {headline}
          </m.p>
        </AnimatePresence>
      </div>

      {/* Tap-to-skip affordance — appears only after the first beat (D-08). Crossfades in. */}
      <AnimatePresence>
        {canSkip && (
          <m.button
            type="button"
            onClick={handleSkip}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 0.7, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="absolute bottom-12 z-10 rounded-full px-5 py-2 text-sm"
            style={{
              color: "var(--deck-soft)",
              border: "1px solid color-mix(in srgb, var(--deck-soft) 28%, transparent)",
            }}
          >
            {RITUAL_SKIP}
          </m.button>
        )}
      </AnimatePresence>

      {/* Art preload (D-10 / Pitfall 6): mount the drawn cards' faces warm but visually hidden so
          the reveal's first paint is already composited. CardArt is pure CSS/SVG (no network);
          this never blocks the timeline. Absolutely-positioned + opacity:0 (not display:none) so
          the browser still rasterizes it. aria-hidden — it is not part of the ritual UI. */}
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
