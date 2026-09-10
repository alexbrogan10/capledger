import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import type { CapProjection } from "../api/types";
import { Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney, formatPct } from "../lib/format";

const BLUE = "#2a78d6";
const RED = "#e34948";

export function CapProjectionPage() {
  const { selectedTeamId, teams } = useAppState();
  const [growthRate, setGrowthRate] = useState(0.06);
  const [result, setResult] = useState<CapProjection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!selectedTeamId) return;
    setLoading(true);
    setError(null);
    api
      .recomputeProjections(selectedTeamId, growthRate)
      .then(setResult)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [selectedTeamId, growthRate]);

  const team = teams.find((t) => t.id === selectedTeamId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink-900">Cap Projection</h1>
        <p className="text-sm text-ink-500">
          {team?.name} · Multi-year projection built from currently-signed contracts. Adjust the assumed
          league cap growth rate to see how sensitive the outlook is.
        </p>
      </div>

      <Card>
        <label className="flex flex-col text-sm">
          <span className="mb-1 text-ink-500">
            Assumed league cap growth rate: <strong>{formatPct(growthRate * 100)}</strong> / year
          </span>
          <input
            type="range"
            min={0}
            max={0.12}
            step={0.005}
            value={growthRate}
            onChange={(e) => setGrowthRate(Number(e.target.value))}
            className="w-80"
          />
        </label>
      </Card>

      {error && <ErrorState message={error} />}
      {loading && <LoadingState />}

      {result && !loading && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
            <StatTile label={`${result.base_season} Base Cap`} value={formatMoney(result.base_cap, { compact: true })} />
            <StatTile
              label={`${result.seasons[result.seasons.length - 1]?.season} Projected Cap`}
              value={formatMoney(result.seasons[result.seasons.length - 1]?.projected_cap, { compact: true })}
            />
            <StatTile
              label={`${result.seasons[result.seasons.length - 1]?.season} Projected Space`}
              value={formatMoney(result.seasons[result.seasons.length - 1]?.projected_space, { compact: true })}
              tone={(result.seasons[result.seasons.length - 1]?.projected_space ?? 0) >= 0 ? "positive" : "negative"}
            />
          </div>

          <Card title="Projected Cap Space by Season">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={result.seasons} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
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
                <Bar dataKey="projected_space" radius={[4, 4, 0, 0]}>
                  {result.seasons.map((s, idx) => (
                    <Cell key={idx} fill={s.projected_space >= 0 ? BLUE : RED} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
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
