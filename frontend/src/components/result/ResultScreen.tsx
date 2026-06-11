// STUB — replaced wholesale by plan 03-06 (the result slice).
// Minimal placeholder so FlowRoot can bind the FINAL path now and the Wave-1 build
// type-checks; plan 03-06 overwrites ONLY this file (never FlowRoot).
// TODO(plan 03-06): result screen from the MockReading (READ-09/D-12) — cards, summary, «ещё расклад» wired.

export function ResultScreen() {
  return (
    <main className="flex min-h-full flex-col items-center justify-center px-6 text-center">
      <p className="text-lg opacity-70" style={{ color: "var(--deck-soft)" }}>
        Расклад собирается…
      </p>
    </main>
  );
}
