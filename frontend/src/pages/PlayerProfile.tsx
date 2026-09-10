import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type { ContractRisk, ContractValue, PlayerContractProfile } from "../api/types";
import { Badge, Card, ErrorState, LoadingState, StatTile } from "../components/ui";
import { useAppState } from "../lib/AppState";
import { formatMoney } from "../lib/format";

const BLUE = "#2a78d6";

const DECISION_TONE: Record<string, "info" | "caution" | "negative" | "neutral"> = {
  expiration: "neutral",
  large_cap_hit: "caution",
  potential_release: "negative",
  potential_extension_window: "info",
};

const RISK_TONE: Record<string, "positive" | "info" | "caution" | "negative"> = {
  Low: "positive",
  Moderate: "info",
  High: "caution",
  "Very High": "negative",
};

export function PlayerProfile() {
  const { playerId } = useParams();
  const { season } = useAppState();
  const [profile, setProfile] = useState<PlayerContractProfile | null>(null);
  const [risk, setRisk] = useState<ContractRisk | null>(null);
  const [value, setValue] = useState<ContractValue | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!playerId) return;
    setProfile(null);
    setRisk(null);
    setValue(null);
    setError(null);
    api
      .playerProfile(Number(playerId))
      .then((p) => {
        setProfile(p);
        api.contractRisk(p.contract_id, season).then(setRisk).catch(() => {});
        api.contractValue(p.contract_id).then(setValue).catch(() => {});
      })
      .catch((e) => setError(String(e)));
  }, [playerId, season]);

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
        <div className="flex gap-2">
          <Link
            to={`/contract-report/${profile.player.id}`}
            className="rounded border border-ink-200 px-3 py-1.5 text-sm font-medium text-ink-700 hover:bg-ink-50"
          >
            Decision Report
          </Link>
          <Link
            to={`/release-calculator/${profile.contract_id}`}
            className="rounded bg-accent px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-light"
          >
            Model a Release →
          </Link>
        </div>
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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {risk && (
          <Card title="Contract Risk" subtitle="Model-identified financial risk from contract structure">
            <div className="mb-3 flex items-center gap-3">
              <Badge tone={RISK_TONE[risk.category] ?? "neutral"}>{risk.category}</Badge>
              <span className="tabular text-sm text-ink-500">Risk score: {risk.risk_score}/100</span>
            </div>
            <ul className="space-y-2 text-sm">
              {risk.factors.map((f, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className={`w-4 font-bold ${f.contributes_risk ? "text-negative" : "text-ink-400"}`}>
                    {f.contributes_risk ? "!" : "·"}
                  </span>
                  <span className="text-ink-600">{f.detail}</span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-ink-400">{risk.disclaimer}</p>
          </Card>
        )}

        {value && (
          <Card title="Contract Value Analysis" subtitle="AAV vs. same-position contracts in this dataset">
            <div className="grid grid-cols-2 gap-3">
              <StatTile label="AAV" value={formatMoney(value.aav, { compact: true })} />
              <StatTile label="Position Median" value={formatMoney(value.position_median_aav, { compact: true })} />
              <StatTile label="Percentile" value={`${value.percentile}th`} />
              <StatTile label="Age-Adjusted Percentile" value={`${value.age_band_percentile}th`} />
            </div>
            <p className="mt-3 text-sm font-medium text-ink-800">{value.discrepancy_label}</p>
            <p className="mt-1 text-xs text-ink-400">{value.disclaimer}</p>
          </Card>
        )}
      </div>
    </div>
  );
}
