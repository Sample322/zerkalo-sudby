// AdminScreen — the read-only admin dashboard (AUTH-05). Reachable only from the admin entry in
// Profile (shown when `GET /api/me` returns `is_admin`); the backend independently gates
// /api/admin/stats on ADMIN_TELEGRAM_IDS, so a forged client can never read it. Shows aggregate
// counts + the per-deck / per-topic / per-answer-style distributions (the answer-style split is
// the MVP A/B signal). No personal data is fetched or shown.

import * as m from "motion/react-m";

import { useAdminStats } from "../../hooks/useAdminStats";
import { useMe } from "../../hooks/useMe";
import { getContentSafeAreaInsets } from "../../lib/telegram";
import { useSelection } from "../../stores/selection";
import { NAV_BACK } from "../../reading/copy";
import type { StatItem } from "../../api/admin";
import { PromptVersions } from "./PromptVersions";

export function AdminScreen() {
  const back = useSelection((s) => s.back);
  const insets = getContentSafeAreaInsets();

  const me = useMe();
  const isAdmin = me.data?.is_admin ?? false;
  const { data, isPending, isError } = useAdminStats(isAdmin);

  return (
    <main
      className="flex min-h-full flex-col gap-6 px-6 pb-12"
      style={{ paddingTop: 16 + insets.top, color: "var(--deck-soft)" }}
    >
      <header className="flex items-center gap-3">
        <m.button
          type="button"
          whileTap={{ scale: 0.94 }}
          onClick={back}
          aria-label={NAV_BACK}
          className="grid h-11 w-11 shrink-0 place-items-center rounded-full text-[18px] outline-none focus-visible:ring-2"
          style={{
            background: "color-mix(in srgb, var(--deck-deep) 55%, transparent)",
            border: "1px solid color-mix(in srgb, var(--deck-accent) 24%, transparent)",
            color: "var(--deck-accent)",
            cursor: "pointer",
          }}
        >
          <span aria-hidden="true">←</span>
        </m.button>
        <div className="flex flex-col">
          <span className="eyebrow">Зеркало Судьбы</span>
          <h1 className="font-display metal-text text-[28px] leading-tight">Статистика</h1>
        </div>
      </header>

      {!isAdmin ? (
        <Muted>Доступ только для администратора.</Muted>
      ) : (
        <>
          {isPending ? (
            <Muted>Собираю статистику…</Muted>
          ) : isError || !data ? (
            <Muted>Не удалось загрузить статистику.</Muted>
          ) : (
            <>
              <section className="grid grid-cols-2 gap-3">
                <Metric label="Пользователей" value={data.total_users} />
                <Metric label="Раскладов всего" value={data.total_readings} />
                <Metric label="Активных за 7д" value={data.active_users_7d} />
                <Metric label="Раскладов за 7д" value={data.readings_7d} />
                <Metric label="Сегодня" value={data.readings_today} />
                <Metric label="Завершено" value={data.completed_readings} />
                <Metric label="Сбоев" value={data.failed_readings} />
                <Metric label="Безлимит" value={data.unlimited_users} />
              </section>

              <Distribution title="Стиль ответа" items={data.by_answer_style} />
              <Distribution title="По колодам" items={data.by_deck} />
              <Distribution title="По темам" items={data.by_topic} />
            </>
          )}

          <PromptVersions isAdmin={isAdmin} />
        </>
      )}
    </main>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-1 text-[16px] italic" style={{ color: "var(--color-mist-dim)" }}>
      {children}
    </p>
  );
}

/** A single metric card — eyebrow label + a big metal number. */
function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="panel flex flex-col gap-1 p-4">
      <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
        {label}
      </span>
      <span className="font-display metal-text text-[26px] leading-none">{value}</span>
    </div>
  );
}

/** A labelled distribution — each bucket as a label + count + a proportional metal bar. */
function Distribution({ title, items }: { title: string; items: StatItem[] }) {
  if (items.length === 0) {
    return (
      <section className="flex flex-col gap-3">
        <h2 className="eyebrow px-1">{title}</h2>
        <Muted>Пока нет данных.</Muted>
      </section>
    );
  }
  const max = Math.max(1, ...items.map((i) => i.count));
  const total = items.reduce((sum, i) => sum + i.count, 0) || 1;
  return (
    <section className="flex flex-col gap-3">
      <h2 className="eyebrow px-1">{title}</h2>
      <div className="panel flex flex-col gap-3 p-4">
        {items.map((item) => (
          <div key={item.key} className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-[16px]" style={{ color: "var(--deck-soft)" }}>
                {item.label}
              </span>
              <span className="text-[14px]" style={{ color: "var(--color-mist-dim)" }}>
                {item.count} · {Math.round((item.count / total) * 100)}%
              </span>
            </div>
            <div
              className="h-2 w-full overflow-hidden rounded-full"
              style={{ background: "color-mix(in srgb, var(--deck-soft) 14%, transparent)" }}
            >
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.max(4, Math.round((item.count / max) * 100))}%`,
                  background: "linear-gradient(90deg, var(--deck-soft), var(--deck-accent))",
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default AdminScreen;
