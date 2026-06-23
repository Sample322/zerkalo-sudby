// AuthGate — the boot flow. On mount it reads initData, authenticates against the backend,
// and stores the JWT in the session store. It renders three states:
//   - authenticating: the ritual portal (a turning sigil ring)
//   - authenticated:  the app (children) — no persistent chrome (each screen owns its top)
//   - error:          an in-character message (NO stacktrace, NO "AI" — threat T-05-02)
//
// Identity is never trusted client-side: AuthGate only forwards initData and reflects the
// backend's verdict. This screen runs ABOVE LazyMotion, so its motion is CSS, not the m.* runtime.

import { useEffect, useRef, type ReactNode } from "react";
import { authenticate } from "../api/auth";
import { telegramReady } from "../lib/telegram";
import { useSession } from "../stores/session";

interface AuthGateProps {
  children: ReactNode;
}

export function AuthGate({ children }: AuthGateProps) {
  const status = useSession((s) => s.status);
  const setAuthenticating = useSession((s) => s.setAuthenticating);
  const setAuthenticated = useSession((s) => s.setAuthenticated);
  const setError = useSession((s) => s.setError);

  // Guard against React StrictMode's dev double-mount firing two auth requests.
  const startedRef = useRef(false);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    let active = true;
    telegramReady();
    setAuthenticating();

    authenticate()
      .then((response) => {
        if (active) setAuthenticated(response);
      })
      .catch(() => {
        // Failure cause stays internal; the user only ever sees the in-character state.
        if (active) setError();
      });

    return () => {
      active = false;
    };
  }, [setAuthenticating, setAuthenticated, setError]);

  if (status === "authenticated") {
    return <>{children}</>;
  }

  const isError = status === "error";
  return (
    <main
      className="relative flex flex-col items-center justify-center gap-8 px-9 text-center"
      style={{ minHeight: "var(--tg-viewport-stable-height, 100dvh)" }}
    >
      <p className="eyebrow">Зеркало Судьбы</p>

      <Sigil dimmed={isError} />

      {isError ? (
        <div className="flex flex-col gap-4">
          <h1 className="font-display metal-text text-[28px] leading-tight">Зеркало затуманилось</h1>
          <p className="text-lg leading-relaxed" style={{ color: "var(--color-mist)" }}>
            Колода не узнала тебя. Открой ритуал из&nbsp;Telegram, чтобы зеркало отразило твой путь.
          </p>
        </div>
      ) : (
        <p className="text-xl italic" style={{ color: "var(--deck-soft)" }}>
          Зеркало вглядывается в&nbsp;тебя…
        </p>
      )}
    </main>
  );
}

/** The turning sigil ring — a slow gold arc orbiting a luminous ✦ (dims + stills on error). */
function Sigil({ dimmed }: { dimmed: boolean }) {
  return (
    <div className="relative grid place-items-center" style={{ width: 132, height: 132 }}>
      <div
        aria-hidden="true"
        className="absolute inset-0 rounded-full"
        style={{
          background:
            "radial-gradient(circle, color-mix(in srgb, var(--deck-glow) 42%, transparent), transparent 68%)",
          opacity: dimmed ? 0.22 : 0.7,
          transition: "opacity 600ms ease",
        }}
      />
      {!dimmed && (
        <div
          aria-hidden="true"
          className="zs-spin absolute rounded-full"
          style={{
            inset: 12,
            background:
              "conic-gradient(from 0deg, transparent 0deg, color-mix(in srgb, var(--deck-accent) 78%, transparent) 70deg, transparent 150deg)",
            WebkitMaskImage:
              "radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px))",
            maskImage:
              "radial-gradient(farthest-side, transparent calc(100% - 2px), #000 calc(100% - 2px))",
            animationDuration: "3.6s",
          }}
        />
      )}
      <div
        aria-hidden="true"
        className="absolute rounded-full"
        style={{
          inset: 30,
          border: "1px solid color-mix(in srgb, var(--deck-accent) 26%, transparent)",
        }}
      />
      <span
        className="font-display metal-text"
        style={{ fontSize: 46, opacity: dimmed ? 0.55 : 1, transition: "opacity 600ms ease" }}
      >
        ✦
      </span>
    </div>
  );
}
