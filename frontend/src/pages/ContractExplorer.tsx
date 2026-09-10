import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ContractListItem } from "../api/types";
import { Card, ErrorState, LoadingState } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { downloadCsv } from "../lib/csv";
import { formatMoney } from "../lib/format";

export function ContractExplorer() {
  const { teams, season } = useAppState();
  const [contracts, setContracts] = useState<ContractListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [teamId, setTeamId] = useState<string>("");
  const [position, setPosition] = useState("");
  const [minAav, setMinAav] = useState("");
  const [maxAav, setMaxAav] = useState("");
  const [selected, setSelected] = useState<number[]>([]);

  useEffect(() => {
    setContracts(null);
    setError(null);
    api
      .contracts({
        season,
        search: search || undefined,
        team_id: teamId ? Number(teamId) : undefined,
        position: position || undefined,
        min_aav: minAav ? Number(minAav) : undefined,
        max_aav: maxAav ? Number(maxAav) : undefined,
        contract_status: "active",
      })
      .then(setContracts)
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [season, search, teamId, position, minAav, maxAav]);

  const positions = useMemo(
    () => Array.from(new Set((contracts ?? []).map((c) => c.position))).sort(),
    [contracts]
  );

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id);
      if (prev.length >= 2) return [prev[1], id];
      return [...prev, id];
    });
  };

  const comparisonContracts = (contracts ?? []).filter((c) => selected.includes(c.id));

  if (error) return <ErrorState message={error} />;

  const exportCsv = () => {
    if (!contracts) return;
    downloadCsv(
      `contracts_${season}.csv`,
      contracts.map((c) => ({
        player: c.player_name, team: c.team_abbreviation, position: c.position, age: c.age,
        years_remaining: c.years_remaining, aav: c.annual_value, cap_hit: c.current_cap_hit,
        guaranteed_money: c.guaranteed_money, status: c.contract_status,
      }))
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">Contract Explorer</h1>
          <p className="text-sm text-ink-500">
            Search active contracts league-wide. Select up to two to compare side by side.
          </p>
        </div>
        <button onClick={exportCsv} className="rounded border border-ink-200 px-3 py-1.5 text-sm text-ink-700 hover:bg-ink-50">
          Export CSV
        </button>
      </div>

      <div className="flex flex-wrap gap-3">
        <input
          className="w-56 rounded border border-ink-200 px-3 py-1.5 text-sm"
          placeholder="Search player…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select className="rounded border border-ink-200 px-3 py-1.5 text-sm" value={teamId} onChange={(e) => setTeamId(e.target.value)}>
          <option value="">All teams</option>
          {teams.map((t) => (
            <option key={t.id} value={t.id}>
              {t.abbreviation}
            </option>
          ))}
        </select>
        <select className="rounded border border-ink-200 px-3 py-1.5 text-sm" value={position} onChange={(e) => setPosition(e.target.value)}>
          <option value="">All positions</option>
          {positions.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
        <input
          className="w-32 rounded border border-ink-200 px-3 py-1.5 text-sm"
          placeholder="Min AAV"
          type="number"
          value={minAav}
          onChange={(e) => setMinAav(e.target.value)}
        />
        <input
          className="w-32 rounded border border-ink-200 px-3 py-1.5 text-sm"
          placeholder="Max AAV"
          type="number"
          value={maxAav}
          onChange={(e) => setMaxAav(e.target.value)}
        />
      </div>

      {comparisonContracts.length > 0 && (
        <Card title="Contract Comparison">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {comparisonContracts.map((c) => (
              <div key={c.id} className="rounded border border-ink-200 p-3">
                <div className="font-semibold text-ink-900">
                  {c.player_name} <span className="text-ink-400">({c.team_abbreviation})</span>
                </div>
                <dl className="mt-2 space-y-1 text-sm">
                  <Row label="AAV" value={formatMoney(c.annual_value)} />
                  <Row label="Current Cap Hit" value={formatMoney(c.current_cap_hit)} />
                  <Row label="Years Remaining" value={String(c.years_remaining)} />
                  <Row label="Guaranteed" value={formatMoney(c.guaranteed_money)} />
                  <Row label="Age" value={String(c.age)} />
                </dl>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-ink-400">
            Comparison shows the underlying figures only. Cap Ledger does not label one contract as
            objectively "better" without specifying the criteria that matter for your roster and timeline.
          </p>
        </Card>
      )}

      {!contracts ? (
        <LoadingState />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-ink-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-ink-50">
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-ink-500">
                <th className="px-3 py-2"></th>
                <th className="px-3 py-2">Player</th>
                <th className="px-3 py-2">Team</th>
                <th className="px-3 py-2">Pos</th>
                <th className="px-3 py-2 text-right">Age</th>
                <th className="px-3 py-2 text-right">Yrs Left</th>
                <th className="px-3 py-2 text-right">AAV</th>
                <th className="px-3 py-2 text-right">Cap Hit</th>
                <th className="px-3 py-2 text-right">Guaranteed</th>
              </tr>
            </thead>
            <tbody>
              {contracts.map((c) => (
                <tr key={c.id} className="border-t border-ink-100 hover:bg-ink-50">
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selected.includes(c.id)}
                      onChange={() => toggleSelect(c.id)}
                    />
                  </td>
                  <td className="px-3 py-2">
                    <Link to={`/players/${c.player_id}`} className="font-medium text-accent hover:underline">
                      {c.player_name}
                    </Link>
                  </td>
                  <td className="px-3 py-2 text-ink-600">{c.team_abbreviation}</td>
                  <td className="px-3 py-2 text-ink-600">{c.position}</td>
                  <td className="tabular px-3 py-2 text-right text-ink-600">{c.age}</td>
                  <td className="tabular px-3 py-2 text-right text-ink-600">{c.years_remaining}</td>
                  <td className="tabular px-3 py-2 text-right text-ink-800">{formatMoney(c.annual_value)}</td>
                  <td className="tabular px-3 py-2 text-right font-semibold text-ink-900">
                    {formatMoney(c.current_cap_hit)}
                  </td>
                  <td className="tabular px-3 py-2 text-right text-ink-600">{formatMoney(c.guaranteed_money)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <dt className="text-ink-500">{label}</dt>
      <dd className="tabular font-medium text-ink-800">{value}</dd>
    </div>
  );
}
