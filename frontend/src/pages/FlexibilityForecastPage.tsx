import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { FlexibilityForecast } from "../api/types";
import { Card, ErrorState, LoadingState } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatPct } from "../lib/format";

const BLUE = "#2a78d6";

export function FlexibilityForecastPage() {
  const { selectedTeamId, teams } = useAppState();
  const [growthRate, setGrowthRate] = useState(0.06);
  const [sensitivity, setSensitivity] = useState(0.03);
  const [data, setData] = useState<FlexibilityForecast | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedTeamId) return;
    setError(null);
    api
      .flexibilityForecast(selectedTeamId, growthRate, sensitivity)
      .then(setData)
      .catch((e) => setError(String(e)));
  }, [selectedTeamId, growthRate, sensitivity]);

  const team = teams.find((t) => t.id === selectedTeamId);

  if (error) return <ErrorState message={error} />;
  if (!data) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Financial Flexibility Forecast</h1>
        <p className="text-sm text-ink-500">
          {team?.name} · Financial Flexibility Score projected across the multi-year window, plus
          sensitivity to the assumed cap-growth rate.
        </p>
      </div>

      <Card>
        <div className="flex flex-wrap gap-8">
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">
              Assumed growth rate: <strong>{formatPct(growthRate * 100)}</strong>
            </span>
            <input type="range" min={0} max={0.12} step={0.005} value={growthRate} onChange={(e) => setGrowthRate(Number(e.target.value))} className="w-64" />
          </label>
          <label className="flex flex-col text-sm">
            <span className="mb-1 text-ink-500">
              Sensitivity range: <strong>±{formatPct(sensitivity * 100)}</strong>
            </span>
            <input type="range" min={0.01} max={0.06} step={0.005} value={sensitivity} onChange={(e) => setSensitivity(Number(e.target.value))} className="w-64" />
          </label>
        </div>
      </Card>

      <Card title="Projected Financial Flexibility" subtitle="Score (0-100) by season under the current assumption">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.seasons} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#e1e0d9" vertical={false} />
            <XAxis dataKey="season" tick={{ fontSize: 12, fill: "#898781" }} axisLine={{ stroke: "#c3c2b7" }} tickLine={false} />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#898781" }} axisLine={false} tickLine={false} width={32} />
            <Tooltip
              formatter={(value: number, _name, item) => [
                `${value} — ${item.payload.top_positive_factor ?? ""}${item.payload.top_negative_factor ? ` / ${item.payload.top_negative_factor}` : ""}`,
                "Score",
              ]}
              contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e1e0d9" }}
            />
            <Bar dataKey="score" fill={BLUE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card title="What's Driving the Change">
          <ul className="list-disc space-y-2 pl-5 text-sm text-ink-600">
            {data.narrative.map((n, idx) => (
              <li key={idx}>{n}</li>
            ))}
          </ul>
        </Card>
        <Card title="What Would Change Our Mind?">
          <ul className="list-disc space-y-2 pl-5 text-sm text-ink-600">
            {data.what_would_change_our_mind.map((n, idx) => (
              <li key={idx}>{n}</li>
            ))}
          </ul>
        </Card>
      </div>

      <p className="text-xs text-ink-400">{data.disclaimer}</p>
    </div>
  );
}
