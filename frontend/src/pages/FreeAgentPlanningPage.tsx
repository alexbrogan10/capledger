import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { FreeAgentPlanning } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

const POSITIONS = [
  "QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
  "EDGE", "DT", "LB", "CB", "S", "K", "P", "LS",
];

export function FreeAgentPlanningPage() {
  const { selectedTeamId, season, teams } = useAppState();
  const [position, setPosition] = useState("WR");
  const [targetAav, setTargetAav] = useState(15_000_000);
  const [contractLength, setContractLength] = useState(3);
  const [guaranteedMoney, setGuaranteedMoney] = useState(25_000_000);
  const [result, setResult] = useState<FreeAgentPlanning | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = () => {
    if (!selectedTeamId) return;
    setLoading(true);
    setError(null);
    api
      .freeAgentPlanning(selectedTeamId, {
        position, target_aav: targetAav, contract_length: contractLength,
        guaranteed_money: guaranteedMoney, start_season: season,
      })
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId, season, position, targetAav, contractLength, guaranteedMoney]);

  const team = teams.find((t) => t.id === selectedTeamId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Free-Agent Planning</h1>
        <p className="text-sm text-ink-500">
          {team?.name} · Model signing a hypothetical free agent and see the resulting cap impact.
          Contract figures are hypothetical unless drawn from an actual reported contract.
        </p>
      </div>

      <Card title="Target Contract (hypothetical)">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Position</span>
            <select className="rounded border border-ink-200 px-2 py-1.5" value={position} onChange={(e) => setPosition(e.target.value)}>
              {POSITIONS.map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Max AAV</span>
            <input type="number" step={500000} className="rounded border border-ink-200 px-2 py-1.5" value={targetAav} onChange={(e) => setTargetAav(Number(e.target.value))} />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Contract Length</span>
            <input type="number" min={1} max={7} className="rounded border border-ink-200 px-2 py-1.5" value={contractLength} onChange={(e) => setContractLength(Number(e.target.value))} />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Max Guaranteed</span>
            <input type="number" step={500000} className="rounded border border-ink-200 px-2 py-1.5" value={guaranteedMoney} onChange={(e) => setGuaranteedMoney(Number(e.target.value))} />
          </label>
        </div>
      </Card>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {result && !loading && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Before Signing">
              <div className="grid grid-cols-2 gap-3">
                <StatTile label="Cap Space" value={formatMoney(result.cap_space_before)} tone={result.cap_space_before >= 0 ? "positive" : "negative"} />
                <StatTile label="Financial Flexibility" value={`${result.flexibility_score_before}/100`} />
              </div>
            </Card>
            <Card title="After Signing">
              <div className="grid grid-cols-2 gap-3">
                <StatTile label="Cap Space" value={formatMoney(result.cap_space_after)} tone={result.cap_space_after >= 0 ? "positive" : "negative"} />
                <StatTile label="Financial Flexibility" value={`${result.flexibility_score_after}/100`} />
              </div>
            </Card>
          </div>

          <Card title="Projected Contract" subtitle={`${formatMoney(result.projected_total_value, { compact: true })} total value`}>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-ink-400">
                  <th className="pb-1">Season</th>
                  <th className="pb-1 text-right">Cap Hit</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(result.year_by_year_cap_hit).map(([yr, amt]) => (
                  <tr key={yr} className="border-t border-ink-100">
                    <td className="py-1.5">{yr}</td>
                    <td className="tabular py-1.5 text-right font-medium">{formatMoney(amt)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
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
