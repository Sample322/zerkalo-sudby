// OnboardingFlow — the first screen a new user sees (ONB-01..04). A 3–4 slide, full-bleed,
// vertically-centered atmosphere sequence: three intro slides (ONBOARDING_SLIDES) + a plain-
// language reversed-cards explainer (ONB-03, REVERSED_EXPLAINER) folded in as a dedicated 4th
// slide, then a final «Сделать первый расклад» CTA. A persistent «Пропустить» (ONB-02) is on
// every slide. Finishing or skipping persists the localStorage flag (ONB-04 / D-11) and
// advances the flow to `selection`; FlowRoot already routes returning users straight there.
//
// This component renders INSIDE FlowRoot's <LazyMotion features={domAnimation}>, so all motion
// uses `m.*` from "motion/react-m" — NEVER a stray full `motion.*` (D-10 / PATTERNS Pitfall 5).
// Slide navigation is a local `index` + the same AnimatePresence primitive FlowRoot uses — no
// carousel library (RESEARCH "Don't Hand-Roll"). Atmosphere color reads the deck vars
// (--deck-accent / --deck-soft); pre-selection the root default palette applies (UI-SPEC).
// All user-visible copy is sourced from reading/copy.ts (SAFE-06 ban-list-gated) and rendered
// as React text nodes only — no dangerouslySetInnerHTML (threat T-3-05).

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

// Compose the slide deck from the centralized copy bank: the three intro slides, then the
// reversed-cards explainer (ONB-03) as a dedicated final slide. The «Это не приговор…» intro
// slide (index 2) sets up the explainer that immediately follows. No copy is inlined here.
const SLIDES: readonly Slide[] = [
  ...ONBOARDING_SLIDES.map((s) => ({ title: s.title, subtitle: s.subtitle })),
  { title: null, subtitle: REVERSED_EXPLAINER },
];

// Locked screen-enter tokens (UI-SPEC): compositor-only opacity + small y, ease-out-expo.
const SLIDE_TRANSITION = { duration: 0.28, ease: [0.16, 1, 0.3, 1] as const };

export function OnboardingFlow() {
  const goTo = useSelection((s) => s.goTo);
  const patchSettings = usePatchSettings();
  const [index, setIndex] = useState(0);

  const isLast = index === SLIDES.length - 1;
  const slide = SLIDES[index];

  // ONB-04 / D-09 / D-11: both the final CTA and «Пропустить» complete onboarding, then advance
  // the flow to selection. The onboarding flag is now SERVER-PRIMARY (D-09): completion fires a
  // `PATCH /api/me/settings { onboarding_completed: true }` so the server records it (FlowRoot's
  // gate reads `GET /api/me` as the truth). `markOnboardingSeen()` keeps the localStorage write
  // as the BOOT FALLBACK only, so a returning user is skipped past onboarding on the first paint
  // before `useMe` resolves. The optimistic PATCH never blocks navigation (fire-and-forget; its
  // own rollback handles a failed write — worst case onboarding cosmetically re-shows next boot).
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
    <main
      className="relative flex min-h-full flex-1 flex-col px-6 pt-12 pb-10"
      style={{ background: "var(--deck-bg)" }}
    >
      {/* Persistent «Пропустить» (ONB-02) — present on every slide, top-right, ≥44px tap target. */}
      <div className="flex justify-end">
        <button
          type="button"
          onClick={finishOnboarding}
          className="rounded-full px-4 py-2 text-sm opacity-70 transition-opacity hover:opacity-100"
          style={{ color: "var(--deck-soft)" }}
        >
          {ONBOARDING_SKIP}
        </button>
      </div>

      {/* Vertically-centered hero — mirrors AuthGate's centered layout, deck-var tinted. */}
      <div className="flex flex-1 flex-col items-center justify-center gap-8 text-center">
        <AnimatePresence mode="wait" initial={false}>
          <m.section
            key={index}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={SLIDE_TRANSITION}
            className="flex flex-col items-center gap-6"
            aria-label="Слайд онбординга"
          >
            {/* Decorative accent sigil — inline serif glyph tinted with the deck accent (UI-SPEC). */}
            <span
              aria-hidden="true"
              className="text-4xl leading-none"
              style={{ color: "var(--deck-accent)" }}
            >
              ✦
            </span>

            {slide.title && (
              <h1
                className="max-w-xs text-[28px] font-semibold leading-[1.15]"
                style={{ color: "var(--deck-soft)" }}
              >
                {slide.title}
              </h1>
            )}

            <p className="max-w-xs text-base leading-[1.5] opacity-80">
              {slide.subtitle}
            </p>
          </m.section>
        </AnimatePresence>
      </div>

      {/* Slide progress + primary advance/finish control. */}
      <div className="flex flex-col items-center gap-6">
        <div className="flex items-center gap-2" aria-hidden="true">
          {SLIDES.map((_, i) => (
            <span
              key={i}
              className="h-1.5 w-1.5 rounded-full transition-opacity"
              style={{
                background: "var(--deck-accent)",
                opacity: i === index ? 1 : 0.3,
              }}
            />
          ))}
        </div>

        <m.button
          type="button"
          onClick={handleNext}
          whileTap={{ scale: 0.97 }}
          className="w-full max-w-xs rounded-2xl px-6 py-3 text-base font-semibold"
          style={{
            background: "var(--deck-accent)",
            color: "var(--deck-bg)",
            boxShadow: "0 14px 44px -18px var(--deck-accent)",
          }}
        >
          {isLast ? ONBOARDING_CTA : ONBOARDING_NEXT}
        </m.button>
      </div>
    </main>
  );
}
