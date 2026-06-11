// STUB — replaced wholesale by plan 03-04 (the ritual-prep slice).
// Minimal placeholder so FlowRoot can bind the FINAL path now and the Wave-1 build
// type-checks; plan 03-04 overwrites ONLY this file (never FlowRoot).
// TODO(plan 03-04): auto-advancing ~3s ritual timeline (READ-07/D-08) — beats, particles, completion haptic.

export function RitualScreen() {
  return (
    <main className="flex min-h-full flex-col items-center justify-center px-6 text-center">
      <p className="text-lg opacity-70" style={{ color: "var(--deck-soft)" }}>
        Колода готовится…
      </p>
    </main>
  );
}
