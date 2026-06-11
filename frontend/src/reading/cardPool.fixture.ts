// Bundled client-side card pool (D-06) — a curated Major-Arcana subset transcribed from
// the Phase-1 backend seed (backend/app/seed/data/cards.json) for name/meaning fidelity.
// No GET /api/cards this phase: createReading draws from this fixture. Mirrors the
// `TOPICS` typed-const-array shape (CatalogScreen.tsx). All copy is brand-safe RU — the
// seed already models the soft voice (perevёрnutaya = задержка, not «беда»).

export interface PoolCard {
  name: string;
  shortMeaning: string;
}

// 22 Major Arcana — enough variety to populate 3–4-card spreads without repetition.
export const CARD_POOL: readonly PoolCard[] = [
  { name: "Шут", shortMeaning: "Начало пути, открытость новому и спокойный первый шаг." },
  { name: "Маг", shortMeaning: "Воля и ресурсы уже в руках — момент действовать осознанно." },
  { name: "Жрица", shortMeaning: "Внутреннее знание и интуиция, к которым стоит прислушаться." },
  { name: "Императрица", shortMeaning: "Забота, рост и мягкое изобилие в выбранной теме." },
  { name: "Император", shortMeaning: "Опора, структура и спокойная устойчивость." },
  { name: "Иерофант", shortMeaning: "Традиция, наставничество и проверенный путь." },
  { name: "Влюблённые", shortMeaning: "Выбор сердца и важная связь между людьми." },
  { name: "Колесница", shortMeaning: "Движение вперёд через собранность и направленную волю." },
  { name: "Сила", shortMeaning: "Мягкая внутренняя стойкость, а не давление." },
  { name: "Отшельник", shortMeaning: "Пауза, тишина и взгляд внутрь себя." },
  { name: "Колесо", shortMeaning: "Перемена ритма и поворот в естественном цикле." },
  { name: "Справедливость", shortMeaning: "Баланс, ясность и честный взгляд на ситуацию." },
  { name: "Повешенный", shortMeaning: "Смена угла зрения и принятие паузы." },
  { name: "Перерождение", shortMeaning: "Завершение одного этапа и переход к другому." },
  { name: "Умеренность", shortMeaning: "Сочетание, мера и плавное соединение разного." },
  { name: "Тень", shortMeaning: "Скрытое напряжение, которое стоит увидеть без страха." },
  { name: "Башня", shortMeaning: "Резкое освобождение от того, что держалось из последних сил." },
  { name: "Звезда", shortMeaning: "Тихая надежда, ясность и восстановление." },
  { name: "Луна", shortMeaning: "Туман чувств и образы, в которых проступает важное." },
  { name: "Солнце", shortMeaning: "Тепло, ясность и открытая радость." },
  { name: "Суд", shortMeaning: "Внутренний зов, итог и честный пересмотр." },
  { name: "Мир", shortMeaning: "Целостность, завершённость и ощущение пути пройденного." },
] as const;
