import { NavLink, Outlet } from "react-router-dom";
import { useAppState } from "../lib/AppState";
import { DemoBanner } from "./ui";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/cap-overview", label: "Cap Overview" },
  { to: "/roster", label: "Roster Ledger" },
  { to: "/contracts", label: "Contract Explorer" },
  { to: "/release-calculator", label: "Release Calculator" },
];

export function Layout() {
  const { teams, selectedTeamId, setSelectedTeamId, season, setSeason, meta, loading } = useAppState();

  return (
    <div className="flex min-h-screen flex-col">
      <DemoBanner />
      <header className="border-b border-ink-200 bg-ink-900 text-white">
        <div className="mx-auto flex max-w-7xl items-center gap-6 px-4 py-3">
          <div>
            <div className="text-lg font-semibold tracking-tight">Cap Ledger</div>
            <div className="text-[11px] text-ink-400">NFL Salary Cap &amp; Contract Strategy</div>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm">
              <span className="text-ink-400">Team</span>
              <select
                className="rounded border border-ink-600 bg-ink-800 px-2 py-1 text-white"
                value={selectedTeamId ?? ""}
                onChange={(e) => setSelectedTeamId(Number(e.target.value))}
              >
                {teams.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name} ({t.abbreviation})
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <span className="text-ink-400">Season</span>
              <select
                className="rounded border border-ink-600 bg-ink-800 px-2 py-1 text-white"
                value={season}
                onChange={(e) => setSeason(Number(e.target.value))}
              >
                {(meta?.projection_seasons ?? [season]).map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
        <nav className="mx-auto flex max-w-7xl gap-1 px-4">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "border-accent-light text-white"
                    : "border-transparent text-ink-300 hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        {loading ? <div className="p-8 text-sm text-ink-400">Loading Cap Ledger…</div> : <Outlet />}
      </main>
      <footer className="border-t border-ink-200 px-4 py-4 text-center text-xs text-ink-400">
        Cap Ledger is an independent analytical project. It is not affiliated with the NFL or any NFL
        team, and does not represent proprietary team information or professional financial/legal advice.
      </footer>
    </div>
  );
}
