// ProfileScreen — the Profile/Settings surface (PROF-01 / PROF-02 / D-07). Shows the Telegram
// identity (name + photo from `GET /api/me`) and the two user-facing toggles — reversals and
// history-personalization — each persisted via `PATCH /api/me/settings` with an OPTIMISTIC cache
// update (usePatchSettings). The personalization toggle defaults OFF (the server default, D-05)
// and carries a plain-language privacy explainer that describes «история раскладов» / «колода
// помнит», NEVER the mechanism (SAFE-06 / Pitfall 6 — all strings come from copy.ts).
//
// FREE-COUNT BLOCK (D-09, Phase 6): un-hides the Phase-5 deliberately-omitted limits surface now
// that the weekly free limit is real. A small glass block between identity and settings shows the
// FREE count ONLY (PROFILE_LIMIT_LABEL + «Осталось N из M» via formatRemaining) — the subscription
// / paid-balance surface stays out until Phase 7 (no tariffs, no «buy» here). The Phase-5 test
// that asserted the count was ABSENT is inverted to assert it is PRESENT.
//
// Renders inside FlowRoot's <LazyMotion features={domAnimation}> so all motion uses `m.*` from
// "motion/react-m" (D-10 / Pitfall 5). The GLASS visual language + back affordance mirror
// ResultScreen for a cohesive surface. The identity values render as React text nodes only — no
// dangerouslySetInnerHTML (T-05-XSS).

import type { CSSProperties } from "react";
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

const GLASS: CSSProperties = {
  background: "color-mix(in srgb, var(--deck-deep) 70%, transparent)",
  border: "1px solid color-mix(in srgb, var(--deck-accent) 22%, transparent)",
  borderRadius: 16,
};

/** Compose the display name from the Telegram profile, falling back gracefully when absent. */
function displayName(user: SessionUser): string {
  const parts = [user.first_name, user.last_name].filter(
    (p): p is string => Boolean(p && p.trim().length > 0),
  );
  if (parts.length > 0) return parts.join(" ");
  if (user.username) return `@${user.username}`;
  return "Странник"; // brand-safe neutral fallback when Telegram gives no name (SAFE-06).
}

/** Initial for the avatar fallback when no photo_url is present. */
function avatarInitial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "·";
}

interface SettingRowProps {
  label: string;
  /** Optional explainer paragraph shown under the label (the personalization privacy note). */
  description?: string;
  checked: boolean;
  /** Disabled while the profile is still resolving (no value to toggle from yet). */
  disabled: boolean;
  onChange: (next: boolean) => void;
}

/** One settings toggle row — a label (+ optional explainer) and an accessible switch button. */
function SettingRow({ label, description, checked, disabled, onChange }: SettingRowProps) {
  return (
    <div className="flex flex-col gap-2 p-4" style={GLASS}>
      <div className="flex items-start justify-between gap-4">
        <span className="text-base font-medium" style={{ color: "var(--deck-soft)" }}>
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
              ? "var(--deck-accent)"
              : "color-mix(in srgb, var(--deck-soft) 28%, transparent)",
            cursor: disabled ? "default" : "pointer",
          }}
        >
          <span
            aria-hidden="true"
            className="absolute top-0.5 h-6 w-6 rounded-full transition-[left]"
            style={{
              left: checked ? 22 : 2,
              background: "var(--deck-bg)",
            }}
          />
        </m.button>
      </div>
      {description && (
        <p className="text-sm leading-relaxed opacity-70" style={{ color: "var(--deck-soft)" }}>
          {description}
        </p>
      )}
    </div>
  );
}

/** Shared back-header — title + a single in-app back affordance → Home (D-11). */
function ProfileHeader({ onBack, topInset }: { onBack: () => void; topInset: number }) {
  return (
    <header className="flex items-center gap-3" style={{ paddingTop: 16 + topInset }}>
      <m.button
        type="button"
        whileTap={{ scale: 0.94 }}
        onClick={onBack}
        aria-label={NAV_BACK}
        className="grid h-10 w-10 shrink-0 place-items-center rounded-full outline-none focus-visible:ring-2"
        style={{
          background: "color-mix(in srgb, var(--deck-deep) 60%, transparent)",
          border: "1px solid color-mix(in srgb, var(--deck-accent) 22%, transparent)",
          color: "var(--deck-accent)",
          cursor: "pointer",
        }}
      >
        <span aria-hidden="true">←</span>
      </m.button>
      <h1 className="text-3xl font-semibold" style={{ color: "var(--deck-accent)" }}>
        {PROFILE_HEADER}
      </h1>
    </header>
  );
}

export function ProfileScreen() {
  const back = useSelection((s) => s.back);
  const insets = getContentSafeAreaInsets();

  const { data, isPending, isError } = useMe();
  const patchSettings = usePatchSettings();

  // Toggling a flag fires the optimistic PATCH with ONLY the changed key (the server applies the
  // partial update; the cache reflects it instantly via usePatchSettings.onMutate).
  function toggle(flag: keyof SessionSettings, next: boolean): void {
    patchSettings.mutate({ [flag]: next });
  }

  const body = (() => {
    if (isPending) {
      return <p className="px-1 opacity-70">{HISTORY_LOADING}</p>;
    }
    if (isError || !data) {
      return <p className="px-1 opacity-70">{HISTORY_ERROR}</p>;
    }

    const name = displayName(data.user);
    const settings = data.settings;

    return (
      <>
        {/* Telegram identity — photo (or an initial fallback) + name. The free-count block (D-09)
            follows below, between identity and settings. */}
        <section className="flex items-center gap-4 p-4" style={GLASS}>
          {data.user.photo_url ? (
            <img
              src={data.user.photo_url}
              alt=""
              width={56}
              height={56}
              referrerPolicy="no-referrer"
              className="h-14 w-14 shrink-0 rounded-full object-cover"
              style={{ border: "1px solid color-mix(in srgb, var(--deck-accent) 30%, transparent)" }}
            />
          ) : (
            <span
              aria-hidden="true"
              className="grid h-14 w-14 shrink-0 place-items-center rounded-full text-xl font-semibold"
              style={{
                background: "color-mix(in srgb, var(--deck-accent) 18%, transparent)",
                color: "var(--deck-accent)",
              }}
            >
              {avatarInitial(name)}
            </span>
          )}
          <span className="text-xl font-semibold" style={{ color: "var(--deck-soft)" }}>
            {name}
          </span>
        </section>

        {/* Free-readings count (D-09) — the un-hidden Phase-5 block. Eyebrow label + «Осталось N
            из M», free count ONLY (no subscription/paid/buy — that is Phase 7). Sourced from the
            same `GET /api/me` limits; the value is a React text node (T-06-17). */}
        {data.limits && (
          <section className="flex flex-col gap-1 p-4" style={GLASS}>
            <span className="text-sm uppercase tracking-wide opacity-70">
              {PROFILE_LIMIT_LABEL}
            </span>
            <span className="text-base" style={{ color: "var(--deck-soft)" }}>
              {formatRemaining(
                Math.max(0, data.limits.free_weekly_limit - data.limits.free_used_this_week),
                data.limits.free_weekly_limit,
              )}
            </span>
          </section>
        )}

        {/* The two user-facing toggles (D-07). Each reads its value from the persisted settings
            and writes via the optimistic PATCH. The personalization row carries the privacy
            explainer; it defaults OFF (server default, D-05). */}
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
    <main
      className="flex min-h-full flex-col gap-6 px-6 pb-12"
      style={{ color: "var(--deck-soft)" }}
    >
      <ProfileHeader onBack={back} topInset={insets.top} />
      {body}
    </main>
  );
}

export default ProfileScreen;
