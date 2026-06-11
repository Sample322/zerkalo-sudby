import { AuthGate } from "./components/AuthGate";
import { FlowRoot } from "./flow/FlowRoot";

// Authenticated surface = the full Phase-3 reading flow (onboarding → selection → ritual →
// reveal → result), driven by FlowRoot's step state-machine. AuthGate owns the initData ->
// JWT boot + the three auth states; FlowRoot is its child.
function App() {
  return (
    <AuthGate>
      <FlowRoot />
    </AuthGate>
  );
}

export default App;
