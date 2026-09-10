import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { ContractListItem, ScenarioComparison } from "../api/types";
import { Badge, Card, ErrorState, LoadingState } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

const ASSESSMENT_TONE: Record<string, "positive" | "info" | "caution" | "negative" | "neutral"> = {
  Strong: "positive",
  Favorable: "positive",
  Moderate: "info",
  Conditional: "caution",
  Unfavorable: "negative",
};

export function ScenarioBuilder() {
  const { selectedTeamId, season } = useAppState();
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [contractId, setContractId] = useState<number | null>(null);
  const [result, setResult] = useState<ScenarioComparison | null>(null);
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
      .scenarioComparison(contractId, season)
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [contractId, season]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">What Should We Do With This Contract?</h1>
        <p className="text-sm text-ink-500">
          Automatically compares Keep / Restructure / Release / Trade for the selected player and season.
          Every assessment is a transparent, threshold-based label — not a black-box recommendation.
        </p>
      </div>

      <Card>
        <label className="flex flex-col text-sm">
          <span className="mb-1 text-ink-500">Player</span>
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
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            {result.options.map((opt) => (
              <Card key={opt.scenario_type} title={opt.label}>
                <div className="mb-2">
                  <Badge tone={ASSESSMENT_TONE[opt.assessment] ?? "neutral"}>{opt.assessment}</Badge>
                </div>
                <dl className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-ink-500">{result.season} Cap Impact</dt>
                    <dd
                      className={`tabular font-semibold ${
                        opt.current_year_cap_impact >= 0 ? "text-positive" : "text-negative"
                      }`}
                    >
                      {formatMoney(opt.current_year_cap_impact)}
                    </dd>
                  </div>
                  {opt.dead_cap > 0 && (
                    <div className="flex justify-between">
                      <dt className="text-ink-500">Dead Cap</dt>
                      <dd className="tabular font-medium text-caution">{formatMoney(opt.dead_cap)}</dd>
                    </div>
                  )}
                </dl>
                <p className="mt-2 text-xs text-ink-500">{opt.future_year_impact}</p>
                <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-ink-600">
                  {opt.reasoning.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </Card>
            ))}
          </div>

          <p className="text-xs text-ink-400">{result.disclaimer}</p>
        </>
      )}
    </div>
  );
}
