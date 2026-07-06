// PromptVersions — the admin prompt-template safety valve (ADMIN-05). Lists every template by slug
// with its versions; the operator can ACTIVATE (roll back to) any version — exactly one is active
// per slug — or PUBLISH a new version live, with no redeploy. The backend gates every route on
// ADMIN_TELEGRAM_IDS. This is a deliberately MINIMAL operator surface (the operator is technical),
// not a rich editor. Reachable only from the admin dashboard. No banned brand tokens in copy.

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as m from "motion/react-m";

import {
  activatePromptVersion,
  fetchPromptSlugs,
  publishPromptVersion,
  type PromptSlug,
} from "../../api/admin";

const PROMPTS_KEY = ["admin", "prompts"] as const;

export function PromptVersions({ isAdmin }: { isAdmin: boolean }) {
  const { data, isPending, isError } = useQuery({
    queryKey: PROMPTS_KEY,
    queryFn: fetchPromptSlugs,
    enabled: isAdmin,
  });

  if (!isAdmin) return null;

  return (
    <section className="flex flex-col gap-3">
      <h2 className="eyebrow px-1">Промпты — версии</h2>
      {isPending ? (
        <Muted>Загружаю версии…</Muted>
      ) : isError || !data ? (
        <Muted>Не удалось загрузить версии.</Muted>
      ) : data.length === 0 ? (
        <Muted>Пока нет шаблонов.</Muted>
      ) : (
        <div className="flex flex-col gap-3">
          {data.map((slug) => (
            <SlugCard key={slug.slug} slug={slug} />
          ))}
        </div>
      )}
    </section>
  );
}

function SlugCard({ slug }: { slug: PromptSlug }) {
  const queryClient = useQueryClient();
  const [publishing, setPublishing] = useState(false);

  const activate = useMutation({
    mutationFn: (version: string) => activatePromptVersion(slug.slug, version),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROMPTS_KEY }),
  });

  return (
    <div className="panel flex flex-col gap-3 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[16px]" style={{ color: "var(--deck-soft)" }}>
          {slug.slug}
        </span>
        <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
          {slug.type}
        </span>
      </div>

      <ul className="flex flex-col gap-2">
        {slug.versions.map((v) => (
          <li key={v.version} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-[15px]" style={{ color: "var(--deck-soft)" }}>
              {v.version}
              {v.is_active && (
                <span
                  className="rounded-full px-2 py-0.5 text-[11px]"
                  style={{
                    background: "color-mix(in srgb, var(--deck-accent) 22%, transparent)",
                    color: "var(--deck-accent)",
                  }}
                >
                  активна
                </span>
              )}
            </span>
            {!v.is_active && (
              <m.button
                type="button"
                whileTap={{ scale: 0.95 }}
                disabled={activate.isPending}
                onClick={() => activate.mutate(v.version)}
                className="rounded-full px-3 py-1 text-[13px] outline-none focus-visible:ring-2"
                style={{
                  border: "1px solid color-mix(in srgb, var(--deck-accent) 30%, transparent)",
                  color: "var(--deck-accent)",
                  cursor: activate.isPending ? "default" : "pointer",
                }}
              >
                Откатить
              </m.button>
            )}
          </li>
        ))}
      </ul>

      {activate.isError && <Muted>Не удалось активировать версию.</Muted>}

      {publishing ? (
        <PublishForm slug={slug.slug} onDone={() => setPublishing(false)} />
      ) : (
        <button
          type="button"
          onClick={() => setPublishing(true)}
          className="self-start text-[13px] underline-offset-2 hover:underline"
          style={{ color: "var(--color-mist-dim)", cursor: "pointer" }}
        >
          + новая версия
        </button>
      )}
    </div>
  );
}

function PublishForm({ slug, onDone }: { slug: string; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [version, setVersion] = useState("");
  const [text, setText] = useState("");

  const publish = useMutation({
    mutationFn: () => publishPromptVersion(slug, { version: version.trim(), template_text: text }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROMPTS_KEY });
      onDone();
    },
  });

  const canSubmit = version.trim().length > 0 && text.trim().length > 0 && !publish.isPending;

  return (
    <div className="flex flex-col gap-2">
      <input
        value={version}
        onChange={(e) => setVersion(e.target.value)}
        placeholder="Метка версии (напр. v3)"
        className="rounded-lg px-3 py-2 text-[14px] outline-none"
        style={{
          background: "color-mix(in srgb, var(--deck-deep) 55%, transparent)",
          border: "1px solid color-mix(in srgb, var(--deck-soft) 18%, transparent)",
          color: "var(--deck-soft)",
        }}
      />
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Текст шаблона"
        rows={4}
        className="rounded-lg px-3 py-2 text-[14px] outline-none"
        style={{
          background: "color-mix(in srgb, var(--deck-deep) 55%, transparent)",
          border: "1px solid color-mix(in srgb, var(--deck-soft) 18%, transparent)",
          color: "var(--deck-soft)",
        }}
      />
      {publish.isError && <Muted>Не удалось опубликовать (проверьте, что метка новая).</Muted>}
      <div className="flex items-center gap-3">
        <m.button
          type="button"
          whileTap={{ scale: 0.95 }}
          disabled={!canSubmit}
          onClick={() => publish.mutate()}
          className="rounded-full px-4 py-1.5 text-[13px] outline-none focus-visible:ring-2"
          style={{
            background: canSubmit ? "color-mix(in srgb, var(--deck-accent) 22%, transparent)" : "transparent",
            border: "1px solid color-mix(in srgb, var(--deck-accent) 30%, transparent)",
            color: "var(--deck-accent)",
            cursor: canSubmit ? "pointer" : "default",
          }}
        >
          Опубликовать и активировать
        </m.button>
        <button
          type="button"
          onClick={onDone}
          className="text-[13px]"
          style={{ color: "var(--color-mist-dim)", cursor: "pointer" }}
        >
          Отмена
        </button>
      </div>
    </div>
  );
}

function Muted({ children }: { children: React.ReactNode }) {
  return (
    <p className="px-1 text-[15px] italic" style={{ color: "var(--color-mist-dim)" }}>
      {children}
    </p>
  );
}

export default PromptVersions;
