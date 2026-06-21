// AuthGate — the boot flow. On mount it reads initData, authenticates against the backend,
// and stores the JWT in the session store. It renders three states:
//   - authenticating: a neutral ritual-styled loader
//   - authenticated:  a welcome greeting + the children (the real app)
//   - error:          an in-character message (NO stacktrace, NO "AI" — threat T-05-02)
//
// Identity is never trusted client-side: AuthGate only forwards initData and reflects the
// backend's verdict.

import { useEffect, useRef, type ReactNode } from "react";
import { authenticate } from "../api/auth";
import { getInitData, telegramReady } from "../lib/telegram";
import { useSession } from "../stores/session";

interface AuthGateProps {
  children: ReactNode;
}

export function AuthGate({ children }: AuthGateProps) {
  const status = useSession((s) => s.status);
  const user = useSession((s) => s.user);
  const availableReadings = useSession((s) => s.availableReadings);
  const setAuthenticating = useSession((s) => s.setAuthenticating);
  const setAuthenticated = useSession((s) => s.setAuthenticated);
  const setError = useSession((s) => s.setError);

  // Guard against React StrictMode's dev double-mount firing two auth requests.
  const startedRef = useRef(false);
  // TEMP deploy diagnostic: capture what the client actually had (initData length + a safe
  // prefix) and the backend verdict, so the "колода не узнала" screen tells us empty-initData
  // (len 0 → SDK/Telegram not providing) vs a real backend reject (len>0, status 401).
  const debugRef = useRef<{ len: number; head: string; status: number | string }>({
    len: -1,
    head: "",
    status: "?",
  });

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
      .catch((err: unknown) => {
        const id = getInitData();
        debugRef.current = {
          len: id.length,
          head: id.slice(0, 16),
          status: (err as { status?: number })?.status ?? "net",
        };
        // Failure cause stays internal; the user sees only the in-character state.
        if (active) setError();
      });

    return () => {
      active = false;
    };
  }, [setAuthenticating, setAuthenticated, setError]);

  if (status === "error") {
    return (
      <main className="flex min-h-full flex-col items-center justify-center gap-6 px-6 text-center">
        <h1
          className="text-3xl font-semibold tracking-wide"
          style={{ color: "var(--color-glow)" }}
        >
          Зеркало Судьбы
        </h1>
        <p className="max-w-xs text-lg opacity-80">
          Колода не узнала тебя. Открой ритуал из Telegram, чтобы зеркало
          отразило твой путь.
        </p>
        {/* TEMP diagnostic line — remove after deploy debugging. */}
        <p className="max-w-xs text-xs opacity-50" style={{ wordBreak: "break-all" }}>
          debug: initData len={debugRef.current.len} · status=
          {String(debugRef.current.status)} · head=&quot;{debugRef.current.head}&quot;
        </p>
      </main>
    );
  }

  if (status === "authenticated") {
    const name = user?.first_name?.trim();
    const greeting = name
      ? `Колода знает тебя, ${name}.`
      : "Колода чувствует твоё присутствие.";

    return (
      <div className="flex min-h-full flex-col">
        <header className="flex flex-col items-center gap-3 px-6 pt-12 pb-6 text-center">
          <h1
            className="text-3xl font-semibold tracking-wide"
            style={{ color: "var(--color-glow)" }}
          >
            Зеркало Судьбы
          </h1>
          <p className="text-lg">{greeting}</p>
          <p className="text-sm opacity-70">
            Раскладов наготове:{" "}
            <span style={{ color: "var(--color-glow)" }}>
              {availableReadings}
            </span>
          </p>
        </header>
        {children}
      </div>
    );
  }

  // idle | authenticating — neutral ritual loader.
  return (
    <main className="flex min-h-full flex-col items-center justify-center gap-6 px-6 text-center">
      <h1
        className="text-3xl font-semibold tracking-wide"
        style={{ color: "var(--color-glow)" }}
      >
        Зеркало Судьбы
      </h1>
      <p className="text-lg opacity-70">Зеркало вглядывается в тебя…</p>
    </main>
  );
}
