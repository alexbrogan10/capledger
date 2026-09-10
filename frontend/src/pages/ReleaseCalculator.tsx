import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ContractListItem, ReleaseImpact } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

export function ReleaseCalculator() {
  const { contractId: contractIdParam } = useParams();
  const { selectedTeamId, season, meta } = useAppState();

  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [contractId, setContractId] = useState<number | null>(contractIdParam ? Number(contractIdParam) : null);
  const [releaseSeason, setReleaseSeason] = useState(season);
  const [june1, setJune1] = useState(false);
  const [result, setResult] = useState<ReleaseImpact | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setReleaseSeason(season);
  }, [season]);

  useEffect(() => {
    if (!selectedTeamId) return;
    api
      .contracts({ team_id: selectedTeamId, contract_status: "active", season })
      .then((rows) => {
        setContracts(rows);
        if (!contractId && rows.length > 0) setContractId(rows[0].id);
      })
      .catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId, season]);

  const runSimulation = () => {
    if (!contractId) return;
    setLoading(true);
    setError(null);
    api
      .simulateRelease(contractId, releaseSeason, june1)
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (contractId) runSimulation();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contractId, releaseSeason, june1]);

  const selectedContract = contracts.find((c) => c.id === contractId);
  const seasonOptions = meta?.projection_seasons ?? [season];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Release Calculator</h1>
        <p className="text-sm text-ink-500">
          Model the cap consequence of releasing a player. This is a hypothetical scenario — it does not
          change any stored roster or contract data.
        </p>
      </div>

      <Card>
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Player</span>
            <select
              className="w-64 rounded border border-ink-200 px-3 py-1.5"
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
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">Release Season</span>
            <select
              className="rounded border border-ink-200 px-3 py-1.5"
              value={releaseSeason}
              onChange={(e) => setReleaseSeason(Number(e.target.value))}
            >
              {seasonOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={june1} onChange={(e) => setJune1(e.target.checked)} />
            <span>Post-June 1 designation</span>
          </label>
        </div>
      </Card>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {result && !loading && (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Card title="Before Release">
              <StatTile label="Cap Hit" value={formatMoney(result.before_cap_hit)} />
            </Card>
            <Card title="After Release">
              <div className="grid grid-cols-2 gap-3">
                <StatTile label={`${result.release_season} Dead Cap`} value={formatMoney(result.after_dead_cap_current_year)} tone="caution" />
                {result.june1 && (
                  <StatTile
                    label={`${result.release_season + 1} Dead Cap`}
                    value={formatMoney(result.after_dead_cap_next_year)}
                    tone="caution"
                  />
                )}
                <StatTile
                  label={`${result.release_season} Cap Savings`}
                  value={formatMoney(result.current_year_cap_savings)}
                  tone={result.current_year_cap_savings >= 0 ? "positive" : "negative"}
                />
                <StatTile label="Total Dead Cap" value={formatMoney(result.total_dead_cap)} />
              </div>
            </Card>
          </div>

          <Card title="Resulting Team Cap Position" subtitle={`${result.release_season} available cap space`}>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
              <StatTile
                label="Before"
                value={result.team_cap_before !== null ? formatMoney(result.team_cap_before) : "—"}
              />
              <StatTile
                label="After"
                value={result.team_cap_after !== null ? formatMoney(result.team_cap_after) : "—"}
                tone={result.team_cap_after !== null && result.team_cap_after >= 0 ? "positive" : "negative"}
              />
              <StatTile
                label="Next Year's Cap Hit Removed"
                value={formatMoney(result.next_year_cap_hit_removed)}
                hint="Informational — the cap hit the team no longer owes next season"
              />
            </div>
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

      {selectedContract && !result && !loading && (
        <p className="text-sm text-ink-400">Select a player to model a release scenario.</p>
      )}
    </div>
  );
}
