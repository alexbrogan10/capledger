import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { PositionSpendingComparison } from "../api/types";
import { Card, ErrorState, LoadingState } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney, formatPct } from "../lib/format";

const BLUE = "#2a78d6";
const ORANGE = "#eb6834";

export function PositionSpendingPage() {
  const { selectedTeamId, season, teams } = useAppState();
  const [data, setData] = useState<PositionSpendingComparison | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTeamId) return;
    setData(null);
    setError(null);
    api
      .positionSpendingComparison(selectedTeamId, season)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [selectedTeamId, season]);

  const team = teams.find((t) => t.id === selectedTeamId);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Position Spending</h1>
        <p className="text-sm text-ink-500">
          {team?.name} · {season} · Cap allocation by position group compared to the league average.
        </p>
      </div>

      <Card title="Team vs. League Average" subtitle="Percentage of team cap by position group">
        <ResponsiveContainer width="100%" height={320}>
          <BarChart data={data.rows} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#e1e0d9" vertical={false} />
            <XAxis dataKey="position_group" tick={{ fontSize: 12, fill: "#898781" }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
            <YAxis
              tickFormatter={(v) => `${v}%`}
              tick={{ fontSize: 11, fill: "#898781" }}
              axisLine={false}
              tickLine={false}
              width={40}
            />
            <Tooltip formatter={(value: number) => `${value.toFixed(1)}%`} contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e1e0d9" }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="team_cap_percentage" name={team?.abbreviation ?? "Team"} fill={BLUE} radius={[4, 4, 0, 0]} />
            <Bar dataKey="league_avg_cap_percentage" name="League Average" fill={ORANGE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Detail">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-ink-400">
              <th className="pb-2">Position</th>
              <th className="pb-2 text-right">Cap Spending</th>
              <th className="pb-2 text-right">Team %</th>
              <th className="pb-2 text-right">League Avg %</th>
              <th className="pb-2 text-right">Difference</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.position_group} className="border-t border-ink-100">
                <td className="py-1.5 font-medium text-ink-800">{row.position_group}</td>
                <td className="tabular py-1.5 text-right">{formatMoney(row.team_cap_spending)}</td>
                <td className="tabular py-1.5 text-right">{formatPct(row.team_cap_percentage)}</td>
                <td className="tabular py-1.5 text-right text-ink-500">{formatPct(row.league_avg_cap_percentage)}</td>
                <td className={`tabular py-1.5 text-right font-medium ${row.difference >= 0 ? "text-accent" : "text-caution"}`}>
                  {row.difference >= 0 ? "+" : ""}
                  {formatPct(row.difference)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
