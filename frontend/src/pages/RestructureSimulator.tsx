import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ContractListItem, RestructureImpact } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

export function RestructureSimulator() {
  const { selectedTeamId, season } = useAppState();
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [contractId, setContractId] = useState<number | null>(null);
  const [amount, setAmount] = useState<number>(1_000_000);
  const [result, setResult] = useState<RestructureImpact | null>(null);
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
          setAmount(Math.round(rows[0].current_cap_hit * 0.3));
        }
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId, season]);

  const runSimulation = () => {
    if (!contractId || amount <= 0) return;
    setLoading(true);
    setError(null);
    api
      .simulateRestructure(contractId, season, amount)
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (contractId && amount > 0) runSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contractId, amount, season]);

  const selectedContract = contracts.find((c) => c.id === contractId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Restructure Simulator</h1>
        <p className="text-sm text-ink-500">
          Converting base salary into bonus proration trades current-year cap space for future-year
          obligations. This is a hypothetical scenario — it does not change any stored data.
        </p>
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Player</span>
            <select
              className="w-64 rounded border border-ink-200 px-3 py-1.5"
              value={contractId ?? ""}
              onChange={(e) => {
                const id = Number(e.target.value);
                setContractId(id);
                const c = contracts.find((x) => x.id === id);
                if (c) setAmount(Math.round(c.current_cap_hit * 0.3));
              }}
            >
              {contracts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.player_name} ({c.position}) — {formatMoney(c.current_cap_hit, { compact: true })} cap hit
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Amount to convert</span>
            <input
              type="range"
              min={100000}
              max={selectedContract ? Math.max(selectedContract.current_cap_hit - 1_000_000, 100000) : 5_000_000}
              step={50000}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-64"
            />
            <span className="tabular mt-1 text-ink-700">{formatMoney(amount)}</span>
          </label>
        </div>
      </Card>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {result && !loading && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Before">
              <StatTile label={`${result.season} Cap Hit`} value={formatMoney(result.original_cap_hit)} />
            </Card>
            <Card title="After">
              <div className="grid grid-cols-2 gap-3">
                <StatTile label={`${result.season} Cap Hit`} value={formatMoney(result.new_cap_hit)} />
                <StatTile
                  label="Immediate Cap Savings"
                  value={formatMoney(result.current_year_savings)}
                  tone={result.current_year_savings >= 0 ? "positive" : "negative"}
                />
              </div>
            </Card>
          </div>

          <Card title="Future Consequence" subtitle="Cap obligations added to future seasons">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {Object.entries(result.future_cap_hit_increases).map(([yr, amt]) => (
                <StatTile key={yr} label={yr} value={`+${formatMoney(amt)}`} tone="caution" />
              ))}
            </div>
            <p className="mt-3 text-xs text-ink-400">
              Total future increase ({formatMoney(Object.values(result.future_cap_hit_increases).reduce((a, b) => a + b, 0))})
              exactly equals this season's savings — restructuring moves cost, it does not create it.
            </p>
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
