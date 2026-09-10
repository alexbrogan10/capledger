import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { PlayerContractProfile } from "../api/types";
import { Badge, Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { formatMoney } from "../lib/format";

const BLUE = "#2a78d6";

const DECISION_TONE: Record<string, "info" | "caution" | "negative" | "neutral"> = {
  expiration: "neutral",
  large_cap_hit: "caution",
  potential_release: "negative",
  potential_extension_window: "info",
};

export function PlayerProfile() {
  const { playerId } = useParams();
  const [profile, setProfile] = useState<PlayerContractProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playerId) return;
    setProfile(null);
    setError(null);
    api
      .playerProfile(Number(playerId))
      .then(setProfile)
      .catch((e) => setError(String(e)));
  }, [playerId]);

  if (error) return <ErrorState message={error} />;
  if (!profile) return <LoadingState />;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-ink-900">{profile.player.name}</h1>
          <p className="text-sm text-ink-500">
            {profile.player.position} · {profile.team_abbreviation} · Age {profile.player.age} ·{" "}
            {profile.player.experience} yrs experience
          </p>
        </div>
        <Link
          to={`/release-calculator/${profile.contract_id}`}
          className="rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-light"
        >
          Model a Release →
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="Contract" value={`${profile.contract_start}–${profile.contract_end}`} />
        <StatTile label="Total Value" value={formatMoney(profile.total_value, { compact: true })} />
        <StatTile label="AAV" value={formatMoney(profile.annual_value, { compact: true })} />
        <StatTile label="Guaranteed" value={formatMoney(profile.guaranteed_money, { compact: true })} />
      </div>

      <Card title="Financial Timeline" subtitle="Year-by-year cap hit across the contract">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={profile.financial_timeline} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
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
              formatter={(value: number, name: string) => [formatMoney(value), name]}
              contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e1e0d9" }}
            />
            <Bar dataKey="cap_hit" name="Cap Hit" fill={BLUE} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-ink-400">
                <th className="pb-1">Season</th>
                <th className="pb-1 text-right">Base Salary</th>
                <th className="pb-1 text-right">Bonus Proration</th>
                <th className="pb-1 text-right">Cap Hit</th>
                <th className="pb-1 text-right">Guaranteed Base</th>
              </tr>
            </thead>
            <tbody>
              {profile.financial_timeline.map((y) => (
                <tr key={y.season} className="border-t border-ink-100">
                  <td className="py-1.5">{y.season}</td>
                  <td className="tabular py-1.5 text-right">{formatMoney(y.base_salary)}</td>
                  <td className="tabular py-1.5 text-right">{formatMoney(y.signing_bonus_proration)}</td>
                  <td className="tabular py-1.5 text-right font-semibold">{formatMoney(y.cap_hit)}</td>
                  <td className="tabular py-1.5 text-right">{formatMoney(y.guaranteed_base_salary)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card
        title="Decision Points"
        subtitle="Analytical flags on this contract's timeline — not predictions of team intent"
      >
        <ul className="space-y-3">
          {profile.decision_points.map((dp, idx) => (
            <li key={idx} className="flex items-start gap-3 text-sm">
              <Badge tone={DECISION_TONE[dp.kind] ?? "neutral"}>{dp.season}</Badge>
              <div>
                <div className="font-medium text-ink-800">{dp.label}</div>
                <div className="text-ink-500">{dp.detail}</div>
              </div>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
