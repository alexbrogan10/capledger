import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Concentration, FinancialFlexibility } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney, formatPct } from "../lib/format";

const DEFAULT_WEIGHTS: Record<string, number> = {
  cap_space: 0.3,
  dead_cap: 0.15,
  future_guaranteed: 0.2,
  expiring_contracts: 0.15,
  concentration: 0.2,
};

const DIRECTION_COLOR: Record<string, string> = { "+": "text-positive", "-": "text-negative", "~": "text-ink-500" };

export function FinancialFlexibilityPage() {
  const { selectedTeamId, season, teams } = useAppState();
  const [weights, setWeights] = useState(DEFAULT_WEIGHTS);
  const [flex, setFlex] = useState<FinancialFlexibility | null>(null);
  const [concentration, setConcentration] = useState<Concentration | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTeamId) return;
    setError(null);
    Promise.all([
      api.financialFlexibility(selectedTeamId, season, weights),
      api.concentration(selectedTeamId, season),
    ])
      .then(([f, c]) => {
        setFlex(f);
        setConcentration(c);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId, season, weights]);

  const team = teams.find((t) => t.id === selectedTeamId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Financial Flexibility</h1>
        <p className="text-sm text-ink-500">
          {team?.name} · A weighted score combining cap space, dead-cap exposure, future guaranteed
          commitments, expiring contracts, and cap concentration — deliberately distinct from cap space
          alone. Adjust the weights to reflect your own priorities.
        </p>
      </div>

      {error && <ErrorState message={error} />}
      {!flex && !error && <LoadingState />}

      {flex && (
        <>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card title="Financial Flexibility Score" className="lg:col-span-1">
              <div className="text-center">
                <div className="tabular text-5xl font-bold text-accent">{flex.score}</div>
                <div className="text-sm text-ink-500">out of 100</div>
              </div>
            </Card>
            <Card title="Why" className="lg:col-span-2">
              <ul className="space-y-2 text-sm">
                {flex.factors.map((f) => (
                  <li key={f.key} className="flex items-start gap-2">
                    <span className={`w-4 font-bold ${DIRECTION_COLOR[f.direction]}`}>{f.direction}</span>
                    <span className="flex-1">
                      <span className="font-medium text-ink-800">{f.label}:</span>{" "}
                      <span className="text-ink-600">{f.detail}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          </div>

          <Card title="Adjust Weights" subtitle="Weights are relative — they're normalized automatically">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {flex.factors.map((f) => (
                <label key={f.key} className="flex flex-col text-sm">
                  <span className="mb-1 text-ink-500">{f.label}</span>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={weights[f.key] ?? 0}
                    onChange={(e) => setWeights((w) => ({ ...w, [f.key]: Number(e.target.value) }))}
                  />
                  <span className="tabular text-ink-700">{weights[f.key]?.toFixed(2)}</span>
                </label>
              ))}
            </div>
          </Card>

          <p className="text-xs text-ink-400">{flex.disclaimer}</p>
        </>
      )}

      {concentration && (
        <Card title="Financial Concentration" subtitle="Share of total commitments held by the largest contracts">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatTile label="Top 1" value={formatPct(concentration.top1_pct)} hint={formatMoney(concentration.top1_dollars, { compact: true })} />
            <StatTile label="Top 3" value={formatPct(concentration.top3_pct)} hint={formatMoney(concentration.top3_dollars, { compact: true })} />
            <StatTile label="Top 5" value={formatPct(concentration.top5_pct)} hint={formatMoney(concentration.top5_dollars, { compact: true })} />
            <StatTile label="Top 10" value={formatPct(concentration.top10_pct)} hint={formatMoney(concentration.top10_dollars, { compact: true })} />
          </div>
          <p className="mt-3 text-sm text-ink-600">{concentration.interpretation}</p>
        </Card>
      )}
    </div>
  );
}
