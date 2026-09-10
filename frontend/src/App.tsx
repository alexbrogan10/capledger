import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AppStateProvider } from "./lib/AppState";
import { Dashboard } from "./pages/Dashboard";
import { CapOverview } from "./pages/CapOverview";
import { RosterLedger } from "./pages/RosterLedger";
import { ContractExplorer } from "./pages/ContractExplorer";
import { PlayerProfile } from "./pages/PlayerProfile";
import { ReleaseCalculator } from "./pages/ReleaseCalculator";

export default function App() {
  return (
    <AppStateProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/cap-overview" element={<CapOverview />} />
            <Route path="/roster" element={<RosterLedger />} />
            <Route path="/contracts" element={<ContractExplorer />} />
            <Route path="/players/:playerId" element={<PlayerProfile />} />
            <Route path="/release-calculator" element={<ReleaseCalculator />} />
            <Route path="/release-calculator/:contractId" element={<ReleaseCalculator />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppStateProvider>
  );
}
