import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { RookiePlanning } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

interface DraftPick {
  round: number;
  position: string;
}

export function RookiePlanningPage() {
  const { selectedTeamId, season, teams } = useAppState();
  const [picks, setPicks] = useState<DraftPick[]>([
    { round: 1, position: "EDGE" },
    { round: 2, position: "CB" },
    { round: 4, position: "OL" },
  ]);
  const [result, setResult] = useState<RookiePlanning | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const run = () => {
    if (!selectedTeamId || picks.length === 0) return;
    setLoading(true);
    setError(null);
    api
      .rookiePlanning(
        selectedTeamId, season,
        picks.map((p) => ({ draft_round: p.round, position: p.position || undefined }))
      )
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTeamId, season, picks]);

  const team = teams.find((t) => t.id === selectedTeamId);

  const updatePick = (idx: number, field: keyof DraftPick, value: string | number) => {
    setPicks((prev) => prev.map((p, i) => (i === idx ? { ...p, [field]: value } : p)));
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Rookie Contract Planning</h1>
        <p className="text-sm text-ink-500">
          {team?.name} · What happens to our cap if we draft players in these rounds? Uses a simplified,
          per-round rookie-contract estimate — not the real NFL rookie wage scale.
        </p>
      </div>

      <Card title="Draft Picks">
        <div className="space-y-2">
          {picks.map((pick, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm">
                <span className="text-ink-500">Round</span>
                <select
                  className="rounded border border-ink-200 px-2 py-1"
                  value={pick.round}
                  onChange={(e) => updatePick(idx, "round", Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5, 6, 7].map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm">
                <span className="text-ink-500">Position</span>
                <input
                  className="w-20 rounded border border-ink-200 px-2 py-1"
                  value={pick.position}
                  onChange={(e) => updatePick(idx, "position", e.target.value)}
                />
              </label>
              <button
                className="text-xs text-negative hover:underline"
                onClick={() => setPicks((prev) => prev.filter((_, i) => i !== idx))}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            className="rounded border border-ink-200 px-3 py-1.5 text-sm text-accent hover:bg-ink-50"
            onClick={() => setPicks((prev) => [...prev, { round: 3, position: "" }])}
          >
            + Add pick
          </button>
        </div>
      </Card>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {result && !loading && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatTile label="Total First-Year Impact" value={formatMoney(result.total_first_year_cap_impact, { compact: true })} tone="caution" />
            <StatTile label="Cap Space Before" value={formatMoney(result.cap_space_before, { compact: true })} tone={result.cap_space_before >= 0 ? "positive" : "negative"} />
            <StatTile label="Cap Space After" value={formatMoney(result.cap_space_after, { compact: true })} tone={result.cap_space_after >= 0 ? "positive" : "negative"} />
          </div>

          <Card title="Pick-by-Pick Impact">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-ink-400">
                  <th className="pb-2">Round</th>
                  <th className="pb-2">Position</th>
                  <th className="pb-2 text-right">Total Value</th>
                  <th className="pb-2 text-right">Signing Bonus</th>
                  <th className="pb-2 text-right">First-Year Cap Hit</th>
                </tr>
              </thead>
              <tbody>
                {result.picks.map((p, idx) => (
                  <tr key={idx} className="border-t border-ink-100">
                    <td className="py-1.5">{p.draft_round}</td>
                    <td className="py-1.5 text-ink-500">{p.position ?? "—"}</td>
                    <td className="tabular py-1.5 text-right">{formatMoney(p.total_value)}</td>
                    <td className="tabular py-1.5 text-right">{formatMoney(p.signing_bonus)}</td>
                    <td className="tabular py-1.5 text-right font-semibold">{formatMoney(p.first_year_cap_hit)}</td>
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
