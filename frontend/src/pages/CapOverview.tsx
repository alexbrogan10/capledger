import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { TeamCap } from "../api/types";
import { Card, Definition, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

export function CapOverview() {
  const { selectedTeamId, season, teams } = useAppState();
  const [cap, setCap] = useState<TeamCap | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTeamId) return;
    setCap(null);
    setError(null);
    api
      .teamCap(selectedTeamId, season)
      .then(setCap)
      .catch((e) => setError(String(e)));
  }, [selectedTeamId, season]);

  const team = teams.find((t) => t.id === selectedTeamId);

  if (error) return <ErrorState message={error} />;
  if (!cap) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Cap Overview</h1>
        <p className="text-sm text-ink-500">
          {team?.name} · {season} salary-cap sheet. Every figure below is defined explicitly — hover the
          term or expand it for the exact calculation.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <StatTile label="Current Salary Cap" value={formatMoney(cap.salary_cap)} />
        <StatTile label="Top-51 Cap Commitments" value={formatMoney(cap.top51_commitments)} />
        <StatTile label="Full Roster Commitments" value={formatMoney(cap.cap_commitments)} />
        <StatTile label="Dead Cap" value={formatMoney(cap.dead_cap)} tone={cap.dead_cap > 0 ? "caution" : "neutral"} />
        <StatTile
          label="Available Cap Space"
          value={formatMoney(cap.cap_space)}
          tone={cap.cap_space >= 0 ? "positive" : "negative"}
        />
        <StatTile
          label="Effective Cap Space"
          value={formatMoney(cap.effective_cap_space)}
          tone={cap.effective_cap_space >= 0 ? "positive" : "negative"}
        />
      </div>

      <Card title="What do these numbers mean?">
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {Object.entries(cap.definitions).map(([key, value]) => (
            <div key={key}>
              <dt className="text-sm font-semibold capitalize text-ink-800">{key.replace(/_/g, " ")}</dt>
              <dd className="mt-0.5 text-sm text-ink-600">{value}</dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card title="Cap Space vs. Financial Flexibility">
        <div className="text-sm text-ink-600">
          <Definition term="Cap space">
            The dollar amount currently available under the league salary cap, computed on a top-51 or
            full-roster basis as shown above.
          </Definition>{" "}
          answers "how much room is there right now?" It does not by itself describe an organization's
          broader financial flexibility — future guaranteed money, dead-cap exposure, expiring contracts,
          and restructuring potential all affect how much real freedom a team has to maneuver. Cap Ledger's
          dedicated Financial Flexibility scoring (Phase 3 of the roadmap) will combine these factors; this
          page reports cap space only, and should not be read as a full flexibility assessment on its own.
        </div>
      </Card>
    </div>
  );
}
