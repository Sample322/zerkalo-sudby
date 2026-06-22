// OnboardingFlow — the first screen a new user sees (ONB-01..04). A 4-slide, full-bleed,
// vertically-centered atmosphere sequence: three intro slides + a plain-language reversed-cards
// explainer (ONB-03) as a dedicated 4th slide, then a «Сделать первый расклад» CTA. A persistent
// «Пропустить» (ONB-02) is on every slide. Finishing or skipping persists the localStorage flag
// (ONB-04 / D-11) and advances to `selection`; FlowRoot routes returning users straight there.
//
// Renders INSIDE FlowRoot's <LazyMotion features={domAnimation}>, so all motion uses `m.*` from
// "motion/react-m". Slide navigation is a local `index` + AnimatePresence (no carousel library).
// All copy is from reading/copy.ts (SAFE-06), rendered as React text nodes only.

import { useState } from "react";
import { AnimatePresence } from "motion/react";
import * as m from "motion/react-m";

import { markOnboardingSeen } from "../../hooks/useOnboardingSeen";
import { usePatchSettings } from "../../hooks/useMe";
import { useSelection } from "../../stores/selection";
import {
  ONBOARDING_CTA,
  ONBOARDING_NEXT,
  ONBOARDING_SKIP,
  ONBOARDING_SLIDES,
  REVERSED_EXPLAINER,
} from "../../reading/copy";

/** One onboarding slide: a Display title + a Body subtitle (the reversed-cards slide has no title). */
interface Slide {
  title: string | null;
  subtitle: string;
}

// Compose the deck from the centralized copy bank: three intro slides, then the reversed-cards
// explainer (ONB-03) as the final slide. No copy is inlined here.
const SLIDES: readonly Slide[] = [
  ...ONBOARDING_SLIDES.map((s) => ({ title: s.title, subtitle: s.subtitle })),
  { title: null, subtitle: REVERSED_EXPLAINER },
];

const SLIDE_TRANSITION = { duration: 0.28, ease: [0.16, 1, 0.3, 1] as const };

export function OnboardingFlow() {
  const goTo = useSelection((s) => s.goTo);
  const patchSettings = usePatchSettings();
  const [index, setIndex] = useState(0);

  const isLast = index === SLIDES.length - 1;
  const slide = SLIDES[index];

  // ONB-04 / D-09 / D-11: both the CTA and «Пропустить» complete onboarding then advance to
  // selection. Server-primary: a fire-and-forget PATCH records it; markOnboardingSeen is the boot
  // fallback. The optimistic PATCH never blocks navigation.
  function finishOnboarding(): void {
    markOnboardingSeen();
    patchSettings.mutate({ onboarding_completed: true });
    goTo("selection");
  }

  function handleNext(): void {
    if (isLast) {
      finishOnboarding();
      return;
    }
    setIndex((i) => Math.min(i + 1, SLIDES.length - 1));
  }

  return (
    <main className="relative flex min-h-full flex-1 flex-col px-7 pb-10 pt-12">
      {/* Persistent «Пропустить» (ONB-02) — every slide, top-right, ≥44px tap target. */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={finishOnboarding}
          className="font-display rounded-full px-4 py-2 text-[14px] tracking-wide opacity-65 transition-opacity hover:opacity-100"
          style={{ color: "var(--deck-soft)" }}
        >
          {ONBOARDING_SKIP}
        </button>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center gap-9 text-center">
        <AnimatePresence mode="wait" initial={false}>
          <m.section
            key={index}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={SLIDE_TRANSITION}
            className="flex flex-col items-center gap-7"
            aria-label="Слайд онбординга"
          >
            <span
              aria-hidden="true"
              className="font-display metal-text text-[46px] leading-none"
              style={{ textShadow: "0 0 24px color-mix(in srgb, var(--deck-glow) 40%, transparent)" }}
            >
              ✦
            </span>

            {slide.title && (
              <h1 className="font-display metal-text max-w-xs text-[30px] leading-[1.15]">
                {slide.title}
              </h1>
            )}

            <p className="max-w-xs text-[18px] leading-relaxed" style={{ color: "var(--color-mist)" }}>
              {slide.subtitle}
            </p>
          </m.section>
        </AnimatePresence>
      </div>

      <div className="flex flex-col items-center gap-6">
        <div className="flex items-center gap-2" aria-hidden="true">
          {SLIDES.map((_, i) => (
            <span
              key={i}
              className="h-1.5 rounded-full transition-all duration-300"
              style={{
                width: i === index ? 18 : 6,
                background: "var(--deck-accent)",
                opacity: i === index ? 1 : 0.32,
              }}
            />
          ))}
        </div>

        <m.button
          type="button"
          onClick={handleNext}
          whileTap={{ scale: 0.97 }}
          className="pill-primary w-full max-w-xs px-6 py-3.5 text-[17px]"
        >
          {isLast ? ONBOARDING_CTA : ONBOARDING_NEXT}
        </m.button>
      </div>
    </main>
  );
}
