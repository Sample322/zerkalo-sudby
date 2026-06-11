// FlowRoot — the Phase-3 navigation spine (D-02). A single Zustand `step` field drives one
// <AnimatePresence mode="wait"> switch across the five screens. This is the AuthGate child
// (App.tsx). Each Wave-2 slice plan replaces ONLY its own screen file (the stubs imported
// below), never this file — that is the seam that removes the multi-writer conflict.
//
// Motion is locked per D-01/D-10 (RESEARCH Pattern 1, UI-SPEC tokens):
//   - <MotionConfig reducedMotion="never">  — full animations always, no reduced-motion downgrade
//   - <LazyMotion features={domAnimation}>  — ship ~4.6kb, not ~34kb (D-01 bundle budget)
//   - m.* from "motion/react-m"             — NEVER a stray full `motion.*` inside LazyMotion (Pitfall 5)

import { useEffect } from "react";
import {
  AnimatePresence,
  domAnimation,
  LazyMotion,
  MotionConfig,
} from "motion/react";
import * as m from "motion/react-m";

import { hasSeenOnboarding } from "../hooks/useOnboardingSeen";
import { useSelection } from "../stores/selection";
import { CatalogScreen } from "../components/CatalogScreen";
import { OnboardingFlow } from "../components/onboarding/OnboardingFlow";
import { RitualScreen } from "../components/ritual/RitualScreen";
import { RevealScreen } from "../components/reveal/RevealScreen";
import { ResultScreen } from "../components/result/ResultScreen";
import type { Step } from "./steps";

// Map each step token to its screen component. `selection` reuses the existing
// CatalogScreen (extended by plan 03-03); the other four are the Wave-2 stubs above.
const SCREENS: Record<Step, () => React.JSX.Element> = {
  onboarding: OnboardingFlow,
  selection: CatalogScreen,
  ritual: RitualScreen,
  reveal: RevealScreen,
  result: ResultScreen,
};

export function FlowRoot() {
  const step = useSelection((s) => s.step);

  // Initial-step gate (ONB-04): only when the store is still at its default `onboarding`
  // do we skip ahead to `selection` for returning users. Done as a direct setState (not
  // goTo) so the mount correction never leaves a phantom "onboarding" on the back history.
  useEffect(() => {
    const current = useSelection.getState();
    if (current.step === "onboarding" && current.history.length === 0 && hasSeenOnboarding()) {
      useSelection.setState({ step: "selection" });
    }
  }, []);

  const Screen = SCREENS[step];

  return (
    <MotionConfig reducedMotion="never">
      <LazyMotion features={domAnimation}>
        <AnimatePresence mode="wait" initial={false}>
          <m.div
            key={step}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
            className="flex min-h-full flex-1 flex-col"
          >
            <Screen />
          </m.div>
        </AnimatePresence>
      </LazyMotion>
    </MotionConfig>
  );
}
