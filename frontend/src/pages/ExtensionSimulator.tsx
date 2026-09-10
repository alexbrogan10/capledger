import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { ContractListItem, ExtensionImpact } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

const BLUE = "#2a78d6";
const ORANGE = "#eb6834";

export function ExtensionSimulator() {
  const { selectedTeamId, season } = useAppState();
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [contractId, setContractId] = useState<number | null>(null);
  const [startSeason, setStartSeason] = useState(season + 1);
  const [years, setYears] = useState(3);
  const [totalValue, setTotalValue] = useState(60_000_000);
  const [signingBonus, setSigningBonus] = useState(15_000_000);
  const [guaranteed, setGuaranteed] = useState(30_000_000);
  const [result, setResult] = useState<ExtensionImpact | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedTeamId) return;
    api
      .contracts({ team_id: selectedTeamId, contract_status: "active", season })
      .then((rows) => {
        setContracts(rows);
        if (rows.length > 0) {
          setContractId(rows[0].id);
          setStartSeason(rows[0].contract_end + 1);
        }
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId, season]);

  const runSimulation = () => {
    if (!contractId) return;
    setLoading(true);
    setError(null);
    api
      .simulateExtension(contractId, {
        extension_start_season: startSeason,
        new_length_years: years,
        new_total_value: totalValue,
        new_signing_bonus: signingBonus,
        new_guaranteed_money: guaranteed,
      })
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    runSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contractId, startSeason, years, totalValue, signingBonus, guaranteed]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Contract Extension Simulator</h1>
        <p className="text-sm text-ink-500">
          Model a hypothetical extension. All new-contract terms below are inputs you choose — Cap Ledger
          does not predict or infer what a real negotiation would produce.
        </p>
      </div>

      <Card title="Extension Terms (hypothetical)">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Player</span>
            <select
              className="rounded border border-ink-200 px-2 py-1.5"
              value={contractId ?? ""}
              onChange={(e) => {
                const id = Number(e.target.value);
                setContractId(id);
                const c = contracts.find((x) => x.id === id);
                if (c) setStartSeason(c.contract_end + 1);
              }}
            >
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.player_name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Start Season</span>
            <input
              type="number"
              className="rounded border border-ink-200 px-2 py-1.5"
              value={startSeason}
              onChange={(e) => setStartSeason(Number(e.target.value))}
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">New Years</span>
            <input
              type="number"
              min={1}
              className="rounded border border-ink-200 px-2 py-1.5"
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Total Value</span>
            <input
              type="number"
              step={1_000_000}
              className="rounded border border-ink-200 px-2 py-1.5"
              value={totalValue}
              onChange={(e) => setTotalValue(Number(e.target.value))}
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Signing Bonus</span>
            <input
              type="number"
              step={1_000_000}
              className="rounded border border-ink-200 px-2 py-1.5"
              value={signingBonus}
              onChange={(e) => setSigningBonus(Number(e.target.value))}
            />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Guaranteed</span>
            <input
              type="number"
              step={1_000_000}
              className="rounded border border-ink-200 px-2 py-1.5"
              value={guaranteed}
              onChange={(e) => setGuaranteed(Number(e.target.value))}
            />
          </label>
        </div>
      </Card>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {result && !loading && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Total New Commitment" value={formatMoney(result.total_new_commitment, { compact: true })} />
            <StatTile label="Total New Guaranteed" value={formatMoney(result.total_new_guaranteed, { compact: true })} />
            <StatTile
              label="First-Year Cap Hit Change"
              value={formatMoney(result.first_year_cap_hit_change, { compact: true })}
              tone={result.first_year_cap_hit_change <= 0 ? "positive" : "caution"}
            />
          </div>

          <Card title="Current Contract vs. Extension Scenario" subtitle="Cap hit by season — blue = current contract, orange = extension years">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={result.combined_years} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                <CartesianGrid stroke="#e1e0d9" vertical={false} />
                <XAxis dataKey="season" tick={{ fontSize: 12, fill: "#898781" }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
                <YAxis
                  tickFormatter={(v) => formatMoney(v, { compact: true })}
                  tick={{ fontSize: 11, fill: "#898781" }}
                  axisLine={false}
                  tickLine={false}
                  width={56}
                />
                <Tooltip formatter={(value: number) => formatMoney(value)} contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e1e0d9" }} />
                <Bar dataKey="cap_hit" radius={[4, 4, 0, 0]}>
                  {result.combined_years.map((y, idx) => (
                    <Cell key={idx} fill={y.season >= result.extension_start_season ? ORANGE : BLUE} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Assumptions">
            <ul className="list-disc space-y-1 pl-5 text-sm text-ink-600">
              {result.assumptions.map((a, idx) => (
                <li key={idx}>{a}</li>
              ))}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
