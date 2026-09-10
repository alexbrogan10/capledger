import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ComparableContracts, ContractValueProjection } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { formatMoney } from "../lib/format";

const POSITIONS = [
  "QB", "RB", "FB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
  "EDGE", "DT", "LB", "CB", "S", "K", "P", "LS",
];

export function AnalyticsModelsPage() {
  const [position, setPosition] = useState("WR");
  const [age, setAge] = useState(27);
  const [length, setLength] = useState(3);
  const [aav, setAav] = useState(18_000_000);

  const [projection, setProjection] = useState<ContractValueProjection | null>(null);
  const [comparables, setComparables] = useState<ComparableContracts | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    Promise.all([
      api.contractValueProjection(position, age, length),
      api.comparableContracts(position, age, aav, 8),
    ])
      .then(([p, c]) => {
        setProjection(p);
        setComparables(c);
      })
      .catch((e) => setError(String(e)));
  }, [position, age, length, aav]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Analytics &amp; Models</h1>
        <p className="text-sm text-ink-500">
          Model-estimated contract value and comparable-contract search, trained and computed against
          Cap Ledger's own synthetic dataset. Optional and secondary to the deterministic cap engine —
          never used for cap-mechanics math.
        </p>
      </div>

      <Card title="Query">
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
            <span className="mb-1 text-ink-500">Age</span>
            <input type="number" min={18} max={50} className="rounded border border-ink-200 px-2 py-1.5" value={age} onChange={(e) => setAge(Number(e.target.value))} />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Contract Length</span>
            <input type="number" min={1} max={7} className="rounded border border-ink-200 px-2 py-1.5" value={length} onChange={(e) => setLength(Number(e.target.value))} />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">AAV (for comparables)</span>
            <input type="number" step={500000} className="rounded border border-ink-200 px-2 py-1.5" value={aav} onChange={(e) => setAav(Number(e.target.value))} />
          </label>
        </div>
      </Card>

      {error && <ErrorState message={error} />}
      {(!projection || !comparables) && !error && <LoadingState />}

      {projection && (
        <Card title="Model-Estimated Contract Value" subtitle="Linear regression trained on Cap Ledger's synthetic dataset">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatTile label="Predicted AAV" value={formatMoney(projection.predicted_aav, { compact: true })} />
            <StatTile label="Model R²" value={projection.model.r2_score.toFixed(3)} hint="Higher = more of the variance explained" />
            <StatTile label="Mean Abs. Error" value={formatMoney(projection.model.mean_absolute_error, { compact: true })} />
          </div>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-ink-600">
            {projection.drivers.map((d, idx) => (
              <li key={idx}>{d}</li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-400">{projection.disclaimer}</p>
          <details className="mt-3 text-xs text-ink-500">
            <summary className="cursor-pointer">Model version &amp; training details</summary>
            <dl className="mt-2 grid grid-cols-2 gap-1 sm:grid-cols-3">
              <div><dt className="inline text-ink-400">Model: </dt><dd className="inline">{projection.model.name} v{projection.model.version}</dd></div>
              <div><dt className="inline text-ink-400">Trained: </dt><dd className="inline">{new Date(projection.model.trained_at).toLocaleString()}</dd></div>
              <div><dt className="inline text-ink-400">Dataset size: </dt><dd className="inline">{projection.model.dataset_size}</dd></div>
              <div><dt className="inline text-ink-400">Train/test split: </dt><dd className="inline">{projection.model.train_size}/{projection.model.test_size}</dd></div>
              <div><dt className="inline text-ink-400">Features: </dt><dd className="inline">{projection.model.features.join(", ")}</dd></div>
              <div><dt className="inline text-ink-400">Target: </dt><dd className="inline">{projection.model.target}</dd></div>
            </dl>
          </details>
        </Card>
      )}

      {comparables && (
        <Card title="Comparable Contracts" subtitle={comparables.methodology}>
          {comparables.results.length === 0 ? (
            <p className="text-sm text-ink-500">No comparable contracts found within the age/position window.</p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-ink-400">
                  <th className="pb-2">Player</th>
                  <th className="pb-2 text-right">Age</th>
                  <th className="pb-2 text-right">AAV</th>
                  <th className="pb-2 text-right">Yrs Left</th>
                  <th className="pb-2 text-right">Similarity</th>
                </tr>
              </thead>
              <tbody>
                {comparables.results.map((r) => (
                  <tr key={r.contract_id} className="border-t border-ink-100">
                    <td className="py-1.5 font-medium text-ink-800">{r.player_name}</td>
                    <td className="tabular py-1.5 text-right text-ink-600">
                      {r.age} {r.age_difference !== 0 && <span className="text-ink-400">({r.age_difference > 0 ? "+" : ""}{r.age_difference})</span>}
                    </td>
                    <td className="tabular py-1.5 text-right">{formatMoney(r.aav)}</td>
                    <td className="tabular py-1.5 text-right text-ink-600">{r.years_remaining}</td>
                    <td className="tabular py-1.5 text-right font-semibold text-accent">{r.similarity_score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}
