import { useEffect, useState } from "react";
import { getHealth, type HealthResult } from "./lib/api";

// Ritual-framed labels — deliberately mystical, never technical (brand voice).
const STATUS_LABEL: Record<string, string> = {
  ok: "пробуждено",
  down: "молчит",
  unknown: "неясно",
};

type Phase = "listening" | "ready" | "clouded";

function App() {
  const [health, setHealth] = useState<HealthResult | null>(null);
  const [phase, setPhase] = useState<Phase>("listening");

  useEffect(() => {
    let active = true;
    getHealth()
      .then((result) => {
        if (!active) return;
        setHealth(result);
        const allAwake = result.db === "ok" && result.redis === "ok";
        setPhase(allAwake ? "ready" : "clouded");
      })
      .catch(() => {
        if (active) setPhase("clouded");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="flex min-h-full flex-col items-center justify-center gap-8 px-6 text-center">
      <h1
        className="text-4xl font-semibold tracking-wide"
        style={{ color: "var(--color-glow)" }}
      >
        Зеркало Судьбы
      </h1>

      {phase === "listening" && (
        <p className="text-lg opacity-70">Зеркало пробуждается…</p>
      )}

      {phase === "ready" && (
        <p className="text-lg">Зеркало готово принять твой вопрос.</p>
      )}

      {phase === "clouded" && (
        <p className="text-lg opacity-80">
          Зеркало пока мутнеет — загляни чуть позже.
        </p>
      )}

      {health && (
        <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm opacity-70">
          <dt className="text-right">Хранилище</dt>
          <dd className="text-left">{STATUS_LABEL[health.db] ?? health.db}</dd>
          <dt className="text-right">Эхо</dt>
          <dd className="text-left">{STATUS_LABEL[health.redis] ?? health.redis}</dd>
        </dl>
      )}
    </main>
  );
}

export default App;
