import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ContractListItem, TradeImpact } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

export function TradeCalculator() {
  const { selectedTeamId, season, teams } = useAppState();
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [contractId, setContractId] = useState<number | null>(null);
  const [result, setResult] = useState<TradeImpact | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedTeamId) return;
    api
      .contracts({ team_id: selectedTeamId, contract_status: "active", season })
      .then((rows) => {
        setContracts(rows);
        if (rows.length > 0) setContractId(rows[0].id);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId, season]);

  useEffect(() => {
    if (!contractId) return;
    setLoading(true);
    setError(null);
    api
      .simulateTrade(contractId, season)
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [contractId, season]);

  const team = teams.find((t) => t.id === selectedTeamId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Trade Contract Calculator</h1>
        <p className="text-sm text-ink-500">
          Models the contract consequences of trading a player — dead cap and cap savings for the trading
          team, and the cap hit the acquiring team would absorb. Trade compensation (picks, other players)
          is not modeled.
        </p>
      </div>

      <Card>
        <label className="flex flex-col text-sm">
          <span className="mb-1 text-ink-500">Player ({team?.abbreviation})</span>
          <select
            className="w-72 rounded border border-ink-200 px-3 py-1.5"
            value={contractId ?? ""}
            onChange={(e) => setContractId(Number(e.target.value))}
          >
            {contracts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.player_name} ({c.position}) — {formatMoney(c.current_cap_hit, { compact: true })} cap hit
              </option>
            ))}
          </select>
        </label>
      </Card>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {result && !loading && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Trading Team" subtitle={team?.name}>
              <div className="grid grid-cols-2 gap-3">
                <StatTile label="Pre-Trade Cap Hit" value={formatMoney(result.trading_team_pre_trade_cap_hit)} />
                <StatTile label="Dead Cap" value={formatMoney(result.trading_team_dead_cap)} tone="caution" />
                <StatTile
                  label="Cap Savings"
                  value={formatMoney(result.trading_team_cap_savings)}
                  tone={result.trading_team_cap_savings >= 0 ? "positive" : "negative"}
                />
              </div>
            </Card>
            <Card title="Acquiring Team" subtitle="Hypothetical — any team taking on the contract">
              <div className="grid grid-cols-2 gap-3">
                <StatTile
                  label="Total Remaining Commitment"
                  value={formatMoney(result.acquiring_team_total_remaining_commitment)}
                />
              </div>
              <table className="mt-4 w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase text-ink-400">
                    <th className="pb-1">Season</th>
                    <th className="pb-1 text-right">New Cap Hit</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(result.acquiring_team_cap_hits).map(([yr, amt]) => (
                    <tr key={yr} className="border-t border-ink-100">
                      <td className="py-1.5">{yr}</td>
                      <td className="tabular py-1.5 text-right font-medium">{formatMoney(amt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>

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
