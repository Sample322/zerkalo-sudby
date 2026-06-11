// STUB — replaced wholesale by plan 03-02 (the onboarding slice).
// This minimal placeholder exists so FlowRoot can import the FINAL path today and the
// Wave-1 build type-checks; plan 03-02 overwrites ONLY this file (never FlowRoot), which
// is the integration seam that removes the multi-writer conflict on FlowRoot.
// TODO(plan 03-02): real 3–4-slide onboarding (ONB-01..04) — skippable, localStorage-gated.

export function OnboardingFlow() {
  return (
    <main className="flex min-h-full flex-col items-center justify-center px-6 text-center">
      <p className="text-lg opacity-70" style={{ color: "var(--deck-soft)" }}>
        Зеркало готовится…
      </p>
    </main>
  );
}
