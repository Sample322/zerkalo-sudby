// STUB — replaced wholesale by plan 03-05 (the flip-reveal slice).
// Minimal placeholder so FlowRoot can bind the FINAL path now and the Wave-1 build
// type-checks; plan 03-05 overwrites ONLY this file (never FlowRoot).
// TODO(plan 03-05): staggered flip-reveal of cards (READ-08/D-09) — tap-to-flip + «раскрыть все».

export function RevealScreen() {
  return (
    <main className="flex min-h-full flex-col items-center justify-center px-6 text-center">
      <p className="text-lg opacity-70" style={{ color: "var(--deck-soft)" }}>
        Карты ложатся…
      </p>
    </main>
  );
}
