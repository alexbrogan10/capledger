import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { RosterRow } from "../api/types";
import { Badge, ErrorState, LoadingState } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { downloadCsv } from "../lib/csv";
import { formatMoney, formatPct } from "../lib/format";

type SortKey = keyof RosterRow;

const COLUMNS: { key: SortKey; label: string; numeric?: boolean }[] = [
  { key: "player_name", label: "Player" },
  { key: "position", label: "Pos" },
  { key: "age", label: "Age", numeric: true },
  { key: "contract_years_remaining", label: "Yrs Left", numeric: true },
  { key: "annual_value", label: "AAV", numeric: true },
  { key: "current_salary", label: "Salary", numeric: true },
  { key: "current_cap_hit", label: "Cap Hit", numeric: true },
  { key: "guaranteed_money", label: "Guaranteed", numeric: true },
  { key: "dead_cap_if_released", label: "Dead Cap If Released", numeric: true },
  { key: "pct_of_team_cap", label: "% of Cap", numeric: true },
];

export function RosterLedger() {
  const { selectedTeamId, season, teams } = useAppState();
  const [rows, setRows] = useState<RosterRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [position, setPosition] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("current_cap_hit");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    if (!selectedTeamId) return;
    setRows(null);
    setError(null);
    api
      .teamRoster(selectedTeamId, season)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, [selectedTeamId, season]);

  const positions = useMemo(() => Array.from(new Set((rows ?? []).map((r) => r.position))).sort(), [rows]);

  const filtered = useMemo(() => {
    if (!rows) return [];
    let out = rows;
    if (search) out = out.filter((r) => r.player_name.toLowerCase().includes(search.toLowerCase()));
    if (position) out = out.filter((r) => r.position === position);
    out = [...out].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av === null) return 1;
      if (bv === null) return -1;
      if (typeof av === "number" && typeof bv === "number") return sortDir === "asc" ? av - bv : bv - av;
      return sortDir === "asc" ? String(av).localeCompare(String(bv)) : String(bv).localeCompare(String(av));
    });
    return out;
  }, [rows, search, position, sortKey, sortDir]);

  const team = teams.find((t) => t.id === selectedTeamId);

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  if (error) return <ErrorState message={error} />;
  if (!rows) return <LoadingState />;

  const exportCsv = () => {
    downloadCsv(
      `${team?.abbreviation ?? "team"}_roster_${season}.csv`,
      filtered.map((r) => ({
        player: r.player_name, position: r.position, age: r.age,
        years_remaining: r.contract_years_remaining, aav: r.annual_value,
        current_salary: r.current_salary, cap_hit: r.current_cap_hit,
        guaranteed_money: r.guaranteed_money, dead_cap_if_released: r.dead_cap_if_released ?? "",
        pct_of_cap: r.pct_of_team_cap ?? "", status: r.contract_status,
      }))
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">Roster Ledger</h1>
          <p className="text-sm text-ink-500">
            {team?.name} · {season} · {filtered.length} of {rows.length} roster entries
          </p>
        </div>
        <button onClick={exportCsv} className="rounded border border-ink-200 px-3 py-1.5 text-sm text-ink-700 hover:bg-ink-50">
          Export CSV
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          className="w-64 rounded border border-ink-200 px-3 py-1.5 text-sm"
          placeholder="Search player…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          className="rounded border border-ink-200 px-3 py-1.5 text-sm"
          value={position}
          onChange={(e) => setPosition(e.target.value)}
        >
          <option value="">All positions</option>
          {positions.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-lg border border-ink-200 bg-white shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-ink-50">
            <tr>
              {COLUMNS.map((col) => (
                <th
                  key={col.key}
                  className={`cursor-pointer select-none px-3 py-2 text-xs font-semibold uppercase tracking-wide text-ink-500 ${
                    col.numeric ? "text-right" : "text-left"
                  }`}
                  onClick={() => handleSort(col.key)}
                >
                  {col.label}
                  {sortKey === col.key && (sortDir === "asc" ? " ▲" : " ▼")}
                </th>
              ))}
              <th className="px-3 py-2 text-left text-xs font-semibold uppercase tracking-wide text-ink-500">
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.player_id} className="border-t border-ink-100 hover:bg-ink-50">
                <td className="px-3 py-2">
                  <Link to={`/players/${row.player_id}`} className="font-medium text-accent hover:underline">
                    {row.player_name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-ink-600">{row.position}</td>
                <td className="tabular px-3 py-2 text-right text-ink-600">{row.age}</td>
                <td className="tabular px-3 py-2 text-right text-ink-600">{row.contract_years_remaining}</td>
                <td className="tabular px-3 py-2 text-right text-ink-800">{formatMoney(row.annual_value)}</td>
                <td className="tabular px-3 py-2 text-right text-ink-800">{formatMoney(row.current_salary)}</td>
                <td
                  className={`tabular px-3 py-2 text-right font-semibold ${
                    row.pct_of_team_cap && row.pct_of_team_cap > 10 ? "text-negative" : "text-ink-900"
                  }`}
                >
                  {formatMoney(row.current_cap_hit)}
                </td>
                <td className="tabular px-3 py-2 text-right text-ink-600">{formatMoney(row.guaranteed_money)}</td>
                <td className="tabular px-3 py-2 text-right text-ink-600">
                  {row.dead_cap_if_released !== null ? formatMoney(row.dead_cap_if_released) : "—"}
                </td>
                <td className="tabular px-3 py-2 text-right text-ink-600">{formatPct(row.pct_of_team_cap)}</td>
                <td className="px-3 py-2">
                  <Badge tone={row.contract_status === "active" ? "positive" : "neutral"}>
                    {row.contract_status}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
