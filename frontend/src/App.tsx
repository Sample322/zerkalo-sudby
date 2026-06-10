import { useEffect, useState } from "react";
import { getHealth, type HealthResult } from "./lib/api";
import { AuthGate } from "./components/AuthGate";

// Ritual-framed labels — deliberately mystical, never technical (brand voice).
const STATUS_LABEL: Record<string, string> = {
  ok: "пробуждено",
  down: "молчит",
  unknown: "неясно",
};

/** Secondary, authenticated-only panel: the live link to the deck's "storage" + "echo". */
function SanctumStatus() {
  const [health, setHealth] = useState<HealthResult | null>(null);

  useEffect(() => {
    let active = true;
    getHealth()
      .then((result) => {
        if (active) setHealth(result);
      })
      .catch(() => {
        if (active) setHealth({ db: "down", redis: "down" });
      });
    return () => {
      active = false;
    };
  }, []);

  if (!health) return null;

  return (
    <section className="flex flex-1 flex-col items-center justify-center px-6 pb-12 text-center">
      <p className="mb-4 text-lg opacity-80">
        Зеркало готово принять твой вопрос.
      </p>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm opacity-60">
        <dt className="text-right">Хранилище</dt>
        <dd className="text-left">{STATUS_LABEL[health.db] ?? health.db}</dd>
        <dt className="text-right">Эхо</dt>
        <dd className="text-left">{STATUS_LABEL[health.redis] ?? health.redis}</dd>
      </dl>
    </section>
  );
}

function App() {
  return (
    <AuthGate>
      <SanctumStatus />
    </AuthGate>
  );
}

export default App;
