import { useDecks } from "../hooks/useDecks";
import { useRecommendation, useSpreads } from "../hooks/useSpreads";
import { useSelection } from "../stores/selection";
import { useDeckTheme } from "../theme/useDeckTheme";
import { DeckCarousel } from "./DeckCarousel";
import { SpreadCard } from "./SpreadCard";
import { TopicChip } from "./TopicChip";

// The 7 MVP topics (REQUIREMENTS HOME-03) — slug -> RU label.
const TOPICS: { slug: string; label: string }[] = [
  { slug: "love", label: "Любовь" },
  { slug: "work", label: "Работа" },
  { slug: "money", label: "Деньги" },
  { slug: "choice", label: "Выбор" },
  { slug: "day", label: "День" },
  { slug: "self_reflection", label: "Саморефлексия" },
  { slug: "general", label: "Общий вопрос" },
];

// The catalog browsing surface: topics + decks + spreads + a topic recommendation, wired to
// the selection store and live per-deck theming. Server state stays in TanStack Query; this
// screen only reads it. The "Начать расклад" ritual is Phase 3 (not built here).
export function CatalogScreen() {
  useDeckTheme(); // selecting a deck re-themes the whole surface (UI-02)

  const topic = useSelection((s) => s.topic);
  const deckSlug = useSelection((s) => s.deckSlug);
  const setTopic = useSelection((s) => s.setTopic);
  const setDeck = useSelection((s) => s.setDeck);

  const decksQuery = useDecks();
  const spreadsQuery = useSpreads(topic, deckSlug);
  const recommendation = useRecommendation(topic, deckSlug);

  return (
    <main
      className="flex flex-1 flex-col gap-6 px-4 pb-24"
      style={{ background: "var(--deck-bg)" }}
    >
      <section aria-label="Темы">
        <div className="flex gap-2 overflow-x-auto pb-1">
          {TOPICS.map((t) => (
            <TopicChip
              key={t.slug}
              topic={t.slug}
              label={t.label}
              active={topic === t.slug}
              onSelect={setTopic}
            />
          ))}
        </div>
      </section>

      {recommendation.data && (
        <section
          aria-label="Рекомендация"
          className="rounded-2xl border p-4"
          style={{
            borderColor: "var(--deck-accent)",
            background: "color-mix(in srgb, var(--deck-accent) 10%, transparent)",
          }}
        >
          <p className="text-xs uppercase tracking-wide opacity-70">Колода советует</p>
          <p className="text-lg font-semibold" style={{ color: "var(--deck-soft)" }}>
            {recommendation.data.recommended_spread.title}
          </p>
          <p className="mt-1 text-sm opacity-80">{recommendation.data.reason}</p>
        </section>
      )}

      <section aria-label="Колоды" className="flex flex-col gap-3">
        <h2 className="px-1 text-sm uppercase tracking-wide opacity-70">Колоды</h2>
        {decksQuery.isPending ? (
          <p className="px-1 opacity-70">Колода раскладывается…</p>
        ) : decksQuery.isError ? (
          <p className="px-1 opacity-70">Колода сейчас молчит. Загляни чуть позже.</p>
        ) : decksQuery.data && decksQuery.data.length > 0 ? (
          <DeckCarousel
            decks={decksQuery.data}
            selectedSlug={deckSlug}
            onSelect={setDeck}
          />
        ) : (
          <p className="px-1 opacity-60">Колоды ещё в тишине.</p>
        )}
      </section>

      <section aria-label="Расклады" className="flex flex-col gap-3">
        <h2 className="px-1 text-sm uppercase tracking-wide opacity-70">Расклады</h2>
        {spreadsQuery.isPending ? (
          <p className="px-1 opacity-70">Расклады собираются…</p>
        ) : spreadsQuery.isError ? (
          <p className="px-1 opacity-70">Расклады не отозвались. Попробуй позже.</p>
        ) : spreadsQuery.data && spreadsQuery.data.length > 0 ? (
          <div className="flex flex-col gap-3">
            {spreadsQuery.data.map((s) => (
              <SpreadCard
                key={s.slug}
                spread={s}
                recommended={
                  recommendation.data?.recommended_spread.slug === s.slug
                }
              />
            ))}
          </div>
        ) : (
          <p className="px-1 opacity-60">Здесь пока пусто.</p>
        )}
      </section>
    </main>
  );
}
