import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { DeadCapDashboard as DeadCapDashboardData } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

const RED = "#e34948";

export function DeadCapDashboard() {
  const { selectedTeamId, season, teams } = useAppState();
  const [data, setData] = useState<DeadCapDashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTeamId) return;
    setData(null);
    setError(null);
    api
      .deadCapDashboard(selectedTeamId, season)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [selectedTeamId, season]);

  const team = teams.find((t) => t.id === selectedTeamId);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Dead-Cap Dashboard</h1>
        <p className="text-sm text-ink-500">{team?.name} · Cap charges from players no longer on the roster.</p>
      </div>

      <StatTile
        label={`${data.current_season} Total Dead Cap`}
        value={formatMoney(data.total_dead_cap_current_season)}
        tone={data.total_dead_cap_current_season > 0 ? "caution" : "neutral"}
      />

      <Card title="Dead Cap by Season" subtitle="Already-realized dead money on the books, by season">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data.by_season} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#e1e0d9" vertical={false} />
            <XAxis dataKey="season" tick={{ fontSize: 12, fill: "#898781" }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
            <YAxis
              tickFormatter={(v) => formatMoney(v, { compact: true })}
              tick={{ fontSize: 11, fill: "#898781" }}
              axisLine={false}
              tickLine={false}
              width={56}
            />
            <Tooltip formatter={(value: number) => formatMoney(value)} contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e1e0d9" }} />
            <Bar dataKey="dead_cap" fill={RED} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <Card title="Dead Cap by Player" subtitle={`${data.current_season} season`}>
        {data.by_player.length === 0 ? (
          <p className="text-sm text-ink-500">No dead cap on the books for {data.current_season}.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-ink-400">
                <th className="pb-2">Player</th>
                <th className="pb-2">Pos</th>
                <th className="pb-2">Status</th>
                <th className="pb-2 text-right">Dead Cap</th>
              </tr>
            </thead>
            <tbody>
              {data.by_player.map((row) => (
                <tr key={row.player_id} className="border-t border-ink-100">
                  <td className="py-1.5 text-ink-800">{row.player_name}</td>
                  <td className="py-1.5 text-ink-500">{row.position}</td>
                  <td className="py-1.5 text-ink-500">{row.contract_status}</td>
                  <td className="tabular py-1.5 text-right font-semibold text-negative">
                    {formatMoney(row.dead_cap_value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
