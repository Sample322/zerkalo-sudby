// FlowRoot — the Phase-3 navigation spine (D-02). A single Zustand `step` field drives one
// <AnimatePresence mode="wait"> switch across the five screens. This is the AuthGate child
// (App.tsx). Each Wave-2 slice plan replaces ONLY its own screen file (the stubs imported
// below), never this file — that is the seam that removes the multi-writer conflict.
//
// Motion is locked per D-01/D-10 (RESEARCH Pattern 1, UI-SPEC tokens):
//   - <MotionConfig reducedMotion="never">  — full animations always, no reduced-motion downgrade
//   - <LazyMotion features={domAnimation}>  — ship ~4.6kb, not ~34kb (D-01 bundle budget)
//   - m.* from "motion/react-m"             — NEVER a stray full `motion.*` inside LazyMotion (Pitfall 5)

import { useEffect, useRef } from "react";
import {
  AnimatePresence,
  domAnimation,
  LazyMotion,
  MotionConfig,
} from "motion/react";
import * as m from "motion/react-m";

import { hasSeenOnboarding } from "../hooks/useOnboardingSeen";
import { useMe, usePatchSettings } from "../hooks/useMe";
import { useSelection } from "../stores/selection";
import { CatalogScreen } from "../components/CatalogScreen";
import { OnboardingFlow } from "../components/onboarding/OnboardingFlow";
import { RitualScreen } from "../components/ritual/RitualScreen";
import { RevealScreen } from "../components/reveal/RevealScreen";
import { ResultScreen } from "../components/result/ResultScreen";
import { HistoryScreen } from "../components/history/HistoryScreen";
import { ProfileScreen } from "../components/profile/ProfileScreen";
import type { Step } from "./steps";

// Map each step token to its screen component. `selection` reuses the existing CatalogScreen
// (extended by plan 03-03). The Phase-5 off-flow destinations (D-10/D-11): `history` →
// HistoryScreen, `profile` → ProfileScreen (its body lands in 05-07), and `readingDetail`
// REUSES ResultScreen (D-02 — reopening a past reading goes straight to the result view; 05-06
// extends ResultScreen to read `detailReadingId`). Each Wave-3 plan replaces ONLY its own
// screen file, never this registry beyond these stubs.
const SCREENS: Record<Step, () => React.JSX.Element> = {
  onboarding: OnboardingFlow,
  selection: CatalogScreen,
  ritual: RitualScreen,
  reveal: RevealScreen,
  result: ResultScreen,
  history: HistoryScreen,
  profile: ProfileScreen,
  readingDetail: ResultScreen,
};

export function FlowRoot() {
  const step = useSelection((s) => s.step);

  // Onboarding gate is now SERVER-PRIMARY (D-09 / RESEARCH OQ3): `GET /api/me`
  // `settings.onboarding_completed` is the truth; localStorage is only a boot fallback so the
  // first paint doesn't flash onboarding for a known returning user while the query is in flight.
  const { data: me } = useMe();
  const patchSettings = usePatchSettings();
  // The reconcile PATCH must fire AT MOST once per mount (a returning user whose server flag is
  // still stale-`false` but whose localStorage says seen).
  const reconciledRef = useRef(false);

  // Boot fallback: only while `useMe` is still resolving, fall back to the localStorage flag so
  // a known returning user is skipped past onboarding on the first paint (no flash). Server takes
  // over below once it resolves. Direct setState (not goTo) so the correction leaves no phantom
  // "onboarding" on the back history. Acts ONLY on the default onboarding + empty-history window.
  useEffect(() => {
    if (me) return; // server has resolved → the server-primary effect owns the decision
    const current = useSelection.getState();
    if (current.step === "onboarding" && current.history.length === 0 && hasSeenOnboarding()) {
      useSelection.setState({ step: "selection" });
    }
  }, [me]);

  // Server-primary decision (D-09): once `GET /api/me` resolves, skip onboarding when the server
  // records it complete, and reconcile a stale-`false` server flag for a returning user (one PATCH).
  useEffect(() => {
    if (!me) return;
    const current = useSelection.getState();
    const onlyAtMount = current.step === "onboarding" && current.history.length === 0;

    if (me.settings.onboarding_completed) {
      // Server says complete → skip ahead (only during the mount-correction window).
      if (onlyAtMount) useSelection.setState({ step: "selection" });
      return;
    }

    // Server says NOT complete but localStorage says seen → a returning user from before this
    // phase. Reconcile the server once, then skip onboarding for them too.
    if (hasSeenOnboarding() && !reconciledRef.current) {
      reconciledRef.current = true;
      patchSettings.mutate({ onboarding_completed: true });
      if (onlyAtMount) useSelection.setState({ step: "selection" });
    }
  }, [me, patchSettings]);

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
