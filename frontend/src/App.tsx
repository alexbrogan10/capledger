import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AppStateProvider } from "./lib/AppState";

function lazyPage<T extends Record<string, React.ComponentType>>(
  loader: () => Promise<T>,
  name: keyof T
) {
  return lazy(() => loader().then((m) => ({ default: m[name] })));
}

const Dashboard = lazyPage(() => import("./pages/Dashboard"), "Dashboard");
const CapOverview = lazyPage(() => import("./pages/CapOverview"), "CapOverview");
const RosterLedger = lazyPage(() => import("./pages/RosterLedger"), "RosterLedger");
const ContractExplorer = lazyPage(() => import("./pages/ContractExplorer"), "ContractExplorer");
const PlayerProfile = lazyPage(() => import("./pages/PlayerProfile"), "PlayerProfile");
const ReleaseCalculator = lazyPage(() => import("./pages/ReleaseCalculator"), "ReleaseCalculator");
const RestructureSimulator = lazyPage(() => import("./pages/RestructureSimulator"), "RestructureSimulator");
const ExtensionSimulator = lazyPage(() => import("./pages/ExtensionSimulator"), "ExtensionSimulator");
const TradeCalculator = lazyPage(() => import("./pages/TradeCalculator"), "TradeCalculator");
const ScenarioBuilder = lazyPage(() => import("./pages/ScenarioBuilder"), "ScenarioBuilder");
const CapProjectionPage = lazyPage(() => import("./pages/CapProjectionPage"), "CapProjectionPage");
const DeadCapDashboard = lazyPage(() => import("./pages/DeadCapDashboard"), "DeadCapDashboard");
const FinancialFlexibilityPage = lazyPage(() => import("./pages/FinancialFlexibilityPage"), "FinancialFlexibilityPage");
const PositionSpendingPage = lazyPage(() => import("./pages/PositionSpendingPage"), "PositionSpendingPage");
const FlexibilityForecastPage = lazyPage(() => import("./pages/FlexibilityForecastPage"), "FlexibilityForecastPage");
const FreeAgentPlanningPage = lazyPage(() => import("./pages/FreeAgentPlanningPage"), "FreeAgentPlanningPage");
const RookiePlanningPage = lazyPage(() => import("./pages/RookiePlanningPage"), "RookiePlanningPage");
const AnalyticsModelsPage = lazyPage(() => import("./pages/AnalyticsModelsPage"), "AnalyticsModelsPage");
const ContractReportPage = lazyPage(() => import("./pages/ContractReportPage"), "ContractReportPage");

function PageLoading() {
  return <div className="p-8 text-sm text-ink-400">Loading…</div>;
}

export default function App() {
  return (
    <AppStateProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoading />}>
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
              <Route path="/flexibility-forecast" element={<FlexibilityForecastPage />} />
              <Route path="/free-agent-planning" element={<FreeAgentPlanningPage />} />
              <Route path="/rookie-planning" element={<RookiePlanningPage />} />
              <Route path="/analytics-models" element={<AnalyticsModelsPage />} />
              <Route path="/contract-report/:playerId" element={<ContractReportPage />} />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AppStateProvider>
  );
}
