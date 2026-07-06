import { AuthGate } from "./components/AuthGate";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { FlowRoot } from "./flow/FlowRoot";
import { RitualBackground } from "./components/ritual/RitualBackground";

// Authenticated surface = the full reading flow (onboarding → selection → ritual → reveal →
// result), driven by FlowRoot's step state-machine. RitualBackground is the fixed atmosphere
// behind everything (z-0); the content sits in a relative z-10 column above it. AuthGate owns
// the initData → JWT boot + the three auth states; FlowRoot is its child. The ErrorBoundary wraps
// the whole authenticated surface so an unexpected render error shows an in-voice fallback (UI-05),
// never a blank screen or a stack trace.
function App() {
  return (
    <>
      <RitualBackground />
      <div className="relative z-10 flex min-h-full flex-col">
        <ErrorBoundary>
          <AuthGate>
            <FlowRoot />
          </AuthGate>
        </ErrorBoundary>
      </div>
    </>
  );
}

export default App;
