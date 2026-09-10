import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AppStateProvider } from "./lib/AppState";
import { Dashboard } from "./pages/Dashboard";
import { CapOverview } from "./pages/CapOverview";
import { RosterLedger } from "./pages/RosterLedger";
import { ContractExplorer } from "./pages/ContractExplorer";
import { PlayerProfile } from "./pages/PlayerProfile";
import { ReleaseCalculator } from "./pages/ReleaseCalculator";
import { RestructureSimulator } from "./pages/RestructureSimulator";
import { ExtensionSimulator } from "./pages/ExtensionSimulator";
import { TradeCalculator } from "./pages/TradeCalculator";
import { ScenarioBuilder } from "./pages/ScenarioBuilder";
import { CapProjectionPage } from "./pages/CapProjectionPage";
import { DeadCapDashboard } from "./pages/DeadCapDashboard";
import { FinancialFlexibilityPage } from "./pages/FinancialFlexibilityPage";
import { PositionSpendingPage } from "./pages/PositionSpendingPage";

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
            <Route path="/restructure-simulator" element={<RestructureSimulator />} />
            <Route path="/extension-simulator" element={<ExtensionSimulator />} />
            <Route path="/trade-calculator" element={<TradeCalculator />} />
            <Route path="/scenario-builder" element={<ScenarioBuilder />} />
            <Route path="/cap-projection" element={<CapProjectionPage />} />
            <Route path="/dead-cap" element={<DeadCapDashboard />} />
            <Route path="/financial-flexibility" element={<FinancialFlexibilityPage />} />
            <Route path="/position-spending" element={<PositionSpendingPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AppStateProvider>
  );
}
