// App-level error boundary (UI-05 / ТЗ §9.8). Catches an UNEXPECTED render error anywhere in the
// tree and shows an in-voice fallback instead of a blank screen or a stack trace — the last line of
// the "every error state in product voice" guarantee that the per-query states don't cover. React
// requires a class component for error boundaries. The error details go to the console for
// diagnostics only; the user sees brand-safe copy (no «AI/нейросеть/модель», no technical text).

import { Component, type ErrorInfo, type ReactNode } from "react";

import { APP_ERROR_HINT, APP_ERROR_RETRY, APP_ERROR_TITLE } from "../reading/copy";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Diagnostics only — never surfaced to the user.
    console.error("app_render_error", error, info.componentStack);
  }

  render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    return (
      <main className="flex min-h-full flex-col items-center justify-center gap-4 px-8 text-center">
        <h1 className="font-display metal-text text-[26px] leading-tight">{APP_ERROR_TITLE}</h1>
        <p className="text-[16px] italic leading-relaxed" style={{ color: "var(--color-mist-dim)" }}>
          {APP_ERROR_HINT}
        </p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="pill-primary px-6 py-3 text-[15px]"
          style={{ cursor: "pointer" }}
        >
          {APP_ERROR_RETRY}
        </button>
      </main>
    );
  }
}

export default ErrorBoundary;
