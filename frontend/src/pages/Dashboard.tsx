import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { Dashboard as DashboardData } from "../api/types";
import { Badge, Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney, formatPct } from "../lib/format";

const BLUE = "#2a78d6";
const RED = "#e34948";

export function Dashboard() {
  const { selectedTeamId, season } = useAppState();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTeamId) return;
    setData(null);
    setError(null);
    api
      .dashboard(selectedTeamId, season)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [selectedTeamId, season]);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  const cap = data.current_cap;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">
          {data.team.name} — Front Office Dashboard
        </h1>
        <p className="text-sm text-ink-500">
          {data.season} season · Executive overview of cap position, future flexibility, and financial alerts.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
        <StatTile label="League Cap Limit" value={formatMoney(cap.salary_cap, { compact: true })} />
        <StatTile
          label="Top-51 Commitments"
          value={formatMoney(cap.top51_commitments, { compact: true })}
        />
        <StatTile label="Dead Money" value={formatMoney(cap.dead_cap, { compact: true })} tone={cap.dead_cap > 0 ? "caution" : "neutral"} />
        <StatTile
          label="Available Cap Space"
          value={formatMoney(cap.cap_space, { compact: true })}
          tone={cap.cap_space >= 0 ? "positive" : "negative"}
        />
        <StatTile
          label="Effective Cap Space"
          value={formatMoney(cap.effective_cap_space, { compact: true })}
          tone={cap.effective_cap_space >= 0 ? "positive" : "negative"}
          hint="Space once the full roster counts"
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Future Cap Space" subtitle="Projected available space, current commitments only — labeled assumption, not guaranteed">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={[cap, ...data.future_cap]} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
              <CartesianGrid stroke="#e1e0d9" vertical={false} />
              <XAxis dataKey="season" tick={{ fontSize: 12, fill: "#898781" }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
              <YAxis
                tickFormatter={(v) => formatMoney(v, { compact: true })}
                tick={{ fontSize: 11, fill: "#898781" }}
                axisLine={false}
                tickLine={false}
                width={56}
              />
              <Tooltip
                formatter={(value: number) => formatMoney(value)}
                labelFormatter={(label) => `${label} season`}
                contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e1e0d9" }}
              />
              <Bar dataKey="cap_space" radius={[4, 4, 0, 0]}>
                {[cap, ...data.future_cap].map((row, idx) => (
                  <Cell key={idx} fill={row.cap_space >= 0 ? BLUE : RED} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Position Spending" subtitle="Cap allocation by position group, current season">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={[...data.position_spending].sort((a, b) => b.cap_spending - a.cap_spending)}
              layout="vertical"
              margin={{ top: 8, right: 24, left: 8, bottom: 8 }}
            >
              <CartesianGrid stroke="#e1e0d9" horizontal={false} />
              <XAxis type="number" tickFormatter={(v) => formatMoney(v, { compact: true })} tick={{ fontSize: 11, fill: "#898781" }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
              <YAxis dataKey="position_group" type="category" tick={{ fontSize: 12, fill: "#0b0b0b" }} axisLine={false} tickLine={false} width={64} />
              <Tooltip
                formatter={(value: number, _name, item) => [
                  `${formatMoney(value)} (${formatPct(item.payload.cap_percentage)})`,
                  "Cap spending",
                ]}
                contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e1e0d9" }}
              />
              <Bar dataKey="cap_spending" fill={BLUE} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="Financial Alerts">
          {data.alerts.length === 0 ? (
            <p className="text-sm text-ink-500">No significant alerts for {data.season}.</p>
          ) : (
            <ul className="space-y-2">
              {data.alerts.map((alert, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <Badge tone={alert.severity === "high" ? "negative" : alert.severity === "watch" ? "caution" : "info"}>
                    {alert.severity}
                  </Badge>
                  <span className="text-ink-700">{alert.message}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Top Cap Commitments" subtitle={`${data.season} cap hit, active roster`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-ink-400">
                <th className="pb-2">Player</th>
                <th className="pb-2">Pos</th>
                <th className="pb-2 text-right">Cap Hit</th>
              </tr>
            </thead>
            <tbody>
              {data.top_commitments.map((row, idx) => (
                <tr key={idx} className="border-t border-ink-100">
                  <td className="py-1.5 text-ink-800">{row.player_name}</td>
                  <td className="py-1.5 text-ink-500">{row.position}</td>
                  <td className="tabular py-1.5 text-right font-medium text-ink-800">
                    {formatMoney(row.cap_hit)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <p className="text-xs text-ink-400">
        Colors: <span style={{ color: BLUE }}>■</span> positive cap space, <span style={{ color: RED }}>■</span> negative cap space.
      </p>
    </div>
  );
}
