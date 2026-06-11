import { AuthGate } from "./components/AuthGate";
import { CatalogScreen } from "./components/CatalogScreen";

// Authenticated surface = the deck & spread catalog (Phase 2). The reading ritual itself
// arrives in Phase 3. AuthGate owns the initData -> JWT boot + the three auth states.
function App() {
  return (
    <AuthGate>
      <CatalogScreen />
    </AuthGate>
  );
}

export default App;
