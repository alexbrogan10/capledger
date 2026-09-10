import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import type { PlayerContractProfile, ScenarioComparison } from "../api/types";
import { ErrorState, LoadingState } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

export function ContractReportPage() {
  const { playerId } = useParams();
  const { season } = useAppState();
  const [profile, setProfile] = useState<PlayerContractProfile | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioComparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playerId) return;
    setProfile(null);
    setScenarios(null);
    setError(null);
    api
      .playerProfile(Number(playerId))
      .then((p) => {
        setProfile(p);
        return api.scenarioComparison(p.contract_id, season);
      })
      .then(setScenarios)
      .catch((e) => setError(String(e)));
  }, [playerId, season]);

  if (error) return <ErrorState message={error} />;
  if (!profile || !scenarios) return <LoadingState />;

  const byType = Object.fromEntries(scenarios.options.map((o) => [o.scenario_type, o]));
  const currentYear = profile.financial_timeline.find((y) => y.season === season);

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-4 flex justify-end print:hidden">
        <button
          onClick={() => window.print()}
          className="rounded bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-light"
        >
          Print / Save as PDF
        </button>
      </div>

      <div className="rounded-lg border border-ink-200 bg-white p-8 font-mono text-sm text-ink-800 shadow-sm print:border-0 print:shadow-none">
        <div className="border-b-2 border-ink-800 pb-2 text-center text-base font-bold tracking-wide">
          CONTRACT ANALYSIS
        </div>
        <div className="border-b border-dashed border-ink-300 py-3">
          <Row label="PLAYER" value={profile.player.name} />
          <Row label="POSITION" value={profile.player.position} />
          <Row label="AGE" value={String(profile.player.age)} />
          <Row label="TEAM" value={profile.team_abbreviation ?? "—"} />
          <Row label="CURRENT AAV" value={formatMoney(profile.annual_value)} />
          <Row label="CURRENT CAP HIT" value={formatMoney(currentYear?.cap_hit ?? 0)} />
          <Row label="YEARS REMAINING" value={String(Math.max(0, profile.contract_end - season + 1))} />
        </div>

        <div className="border-b border-dashed border-ink-300 py-3">
          <div className="mb-1 font-bold">CURRENT CONTRACT</div>
          {profile.financial_timeline.map((y) => (
            <div key={y.season} className="flex justify-between">
              <span>{y.season}:</span>
              <span>{formatMoney(y.cap_hit)}</span>
            </div>
          ))}
        </div>

        <div className="border-b border-dashed border-ink-300 py-3">
          <div className="mb-2 font-bold">OPTIONS</div>

          {byType.keep && (
            <div className="mb-2">
              <div className="font-semibold">KEEP</div>
              <Row label="Cap Impact" value={formatMoney(byType.keep.current_year_cap_impact)} />
              <Row label="Assessment" value={byType.keep.assessment} />
            </div>
          )}
          {byType.restructure && (
            <div className="mb-2">
              <div className="font-semibold">RESTRUCTURE</div>
              <Row label="Immediate Savings" value={formatMoney(byType.restructure.current_year_cap_impact)} />
              <Row label="Future Commitment" value={byType.restructure.future_year_impact} />
              <Row label="Assessment" value={byType.restructure.assessment} />
            </div>
          )}
          {byType.release && (
            <div className="mb-2">
              <div className="font-semibold">RELEASE</div>
              <Row label="Immediate Savings" value={formatMoney(byType.release.current_year_cap_impact)} />
              <Row label="Dead Cap" value={formatMoney(byType.release.dead_cap)} />
              <Row label="Assessment" value={byType.release.assessment} />
            </div>
          )}
          {byType.trade && (
            <div>
              <div className="font-semibold">TRADE</div>
              <Row label="Cap Savings" value={formatMoney(byType.trade.current_year_cap_impact)} />
              <Row label="Dead Cap" value={formatMoney(byType.trade.dead_cap)} />
              <Row label="Assessment" value={byType.trade.assessment} />
            </div>
          )}
        </div>

        <div className="border-b border-dashed border-ink-300 py-3">
          <div className="mb-1 font-bold">DECISION POINTS</div>
          {profile.decision_points.map((dp, idx) => (
            <div key={idx} className="mb-1">
              <span className="font-semibold">{dp.season}:</span> {dp.label} — {dp.detail}
            </div>
          ))}
        </div>

        <div className="py-3">
          <div className="mb-1 font-bold">WHAT COULD CHANGE THIS?</div>
          <p>{scenarios.disclaimer}</p>
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-ink-500">{label}:</span>
      <span className="font-semibold">{value}</span>
    </div>
  );
}
