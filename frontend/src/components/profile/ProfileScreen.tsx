// ProfileScreen — the Profile/Settings surface (PROF-01 / PROF-02 / D-07). Shows the Telegram
// identity (name + photo from `GET /api/me`) and the two user-facing toggles — reversals and
// history-personalization — each persisted via `PATCH /api/me/settings` with an OPTIMISTIC cache
// update. The personalization toggle defaults OFF and carries a plain-language privacy explainer
// (SAFE-06 — all strings from copy.ts, never the mechanism).
//
// FREE-COUNT BLOCK (D-09, Phase 6): a small glass block between identity and settings shows the
// FREE count ONLY (formatRemaining) — subscription/paid surface stays out until Phase 7.
//
// Renders inside FlowRoot's <LazyMotion features={domAnimation}> (m.* only). Identity values are
// React text nodes (T-05-XSS).

import * as m from "motion/react-m";

import { useMe, usePatchSettings } from "../../hooks/useMe";
import { useSelection } from "../../stores/selection";
import { getContentSafeAreaInsets } from "../../lib/telegram";
import type { SessionSettings, SessionUser } from "../../api/auth";
import {
  HISTORY_ERROR,
  HISTORY_LOADING,
  NAV_BACK,
  PROFILE_HEADER,
  PROFILE_LIMIT_LABEL,
  SETTINGS_PERSONALIZATION_EXPLAINER,
  SETTINGS_PERSONALIZATION_LABEL,
  SETTINGS_REVERSALS_LABEL,
} from "../../reading/copy";
import { formatRemaining } from "../../reading/limitCopy";

/** Compose the display name from the Telegram profile, falling back gracefully when absent. */
function displayName(user: SessionUser): string {
  const parts = [user.first_name, user.last_name].filter(
    (p): p is string => Boolean(p && p.trim().length > 0),
  );
  if (parts.length > 0) return parts.join(" ");
  if (user.username) return `@${user.username}`;
  return "Странник"; // brand-safe neutral fallback (SAFE-06).
}

/** Initial for the avatar fallback when no photo_url is present. */
function avatarInitial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "·";
}

interface SettingRowProps {
  label: string;
  description?: string;
  checked: boolean;
  disabled: boolean;
  onChange: (next: boolean) => void;
}

/** One settings toggle row — a label (+ optional explainer) and an accessible switch button. */
function SettingRow({ label, description, checked, disabled, onChange }: SettingRowProps) {
  return (
    <div className="panel flex flex-col gap-2 p-4">
      <div className="flex items-start justify-between gap-4">
        <span className="text-[17px]" style={{ color: "var(--deck-soft)" }}>
          {label}
        </span>
        <m.button
          type="button"
          role="switch"
          aria-checked={checked}
          aria-label={label}
          disabled={disabled}
          whileTap={disabled ? undefined : { scale: 0.94 }}
          onClick={() => onChange(!checked)}
          className="relative h-7 w-12 shrink-0 rounded-full outline-none transition-colors focus-visible:ring-2 disabled:opacity-50"
          style={{
            background: checked
              ? "linear-gradient(180deg, var(--deck-soft), var(--deck-accent))"
              : "color-mix(in srgb, var(--deck-soft) 24%, transparent)",
            boxShadow: checked ? "0 4px 14px color-mix(in srgb, var(--deck-accent) 36%, transparent)" : undefined,
            cursor: disabled ? "default" : "pointer",
          }}
        >
          <span
            aria-hidden="true"
            className="absolute top-0.5 h-6 w-6 rounded-full transition-[left]"
            style={{ left: checked ? 22 : 2, background: "var(--deck-bg)" }}
          />
        </m.button>
      </div>
      {description && (
        <p className="text-[15px] leading-relaxed" style={{ color: "var(--color-mist-dim)" }}>
          {description}
        </p>
      )}
    </div>
  );
}

/** Shared back-header — eyebrow + title + a single in-app back affordance → Home (D-11). */
function ProfileHeader({ onBack, topInset }: { onBack: () => void; topInset: number }) {
  return (
    <header className="flex items-center gap-3" style={{ paddingTop: 16 + topInset }}>
      <m.button
        type="button"
        whileTap={{ scale: 0.94 }}
        onClick={onBack}
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
        <span className="eyebrow">Твой путь</span>
        <h1 className="font-display metal-text text-[28px] leading-tight">{PROFILE_HEADER}</h1>
      </div>
    </header>
  );
}

export function ProfileScreen() {
  const back = useSelection((s) => s.back);
  const insets = getContentSafeAreaInsets();

  const { data, isPending, isError } = useMe();
  const patchSettings = usePatchSettings();

  function toggle(flag: keyof SessionSettings, next: boolean): void {
    patchSettings.mutate({ [flag]: next });
  }

  const body = (() => {
    if (isPending) {
      return <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>{HISTORY_LOADING}</p>;
    }
    if (isError || !data) {
      return <p className="px-1 italic" style={{ color: "var(--color-mist-dim)" }}>{HISTORY_ERROR}</p>;
    }

    const name = displayName(data.user);
    const settings = data.settings;

    return (
      <>
        {/* Telegram identity — photo (or an initial fallback) + name. */}
        <section className="panel flex items-center gap-4 p-5">
          {data.user.photo_url ? (
            <img
              src={data.user.photo_url}
              alt=""
              width={60}
              height={60}
              referrerPolicy="no-referrer"
              className="h-[60px] w-[60px] shrink-0 rounded-full object-cover"
              style={{ border: "1px solid color-mix(in srgb, var(--deck-accent) 40%, transparent)", boxShadow: "0 0 18px -4px color-mix(in srgb, var(--deck-glow) 60%, transparent)" }}
            />
          ) : (
            <span
              aria-hidden="true"
              className="font-display grid h-[60px] w-[60px] shrink-0 place-items-center rounded-full text-2xl"
              style={{
                background: "color-mix(in srgb, var(--deck-accent) 16%, transparent)",
                border: "1px solid color-mix(in srgb, var(--deck-accent) 36%, transparent)",
                color: "var(--deck-accent)",
              }}
            >
              {avatarInitial(name)}
            </span>
          )}
          <span className="font-display metal-text text-[24px] leading-tight">{name}</span>
        </section>

        {/* Free-readings count (D-09) — free count ONLY (no subscription/paid/buy — Phase 7). */}
        {data.limits && (
          <section className="panel flex flex-col gap-1 p-5">
            <span className="eyebrow" style={{ color: "var(--color-mist-dim)" }}>
              {PROFILE_LIMIT_LABEL}
            </span>
            <span className="font-display text-[20px]" style={{ color: "var(--deck-soft)" }}>
              {formatRemaining(
                Math.max(0, data.limits.free_weekly_limit - data.limits.free_used_this_week),
                data.limits.free_weekly_limit,
              )}
            </span>
          </section>
        )}

        {/* The two user-facing toggles (D-07). */}
        <section aria-label="Настройки" className="flex flex-col gap-3">
          <SettingRow
            label={SETTINGS_REVERSALS_LABEL}
            checked={settings.reversals_enabled}
            disabled={false}
            onChange={(next) => toggle("reversals_enabled", next)}
          />
          <SettingRow
            label={SETTINGS_PERSONALIZATION_LABEL}
            description={SETTINGS_PERSONALIZATION_EXPLAINER}
            checked={settings.allow_history_personalization}
            disabled={false}
            onChange={(next) => toggle("allow_history_personalization", next)}
          />
        </section>
      </>
    );
  })();

  return (
    <main className="flex min-h-full flex-col gap-6 px-6 pb-12" style={{ color: "var(--deck-soft)" }}>
      <ProfileHeader onBack={back} topInset={insets.top} />
      {body}
    </main>
  );
}

export default ProfileScreen;
