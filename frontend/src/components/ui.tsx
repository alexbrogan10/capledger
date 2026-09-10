import type { ReactNode } from "react";

export function Card({ title, subtitle, children, className = "" }: {
  title?: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border border-ink-200 bg-white shadow-sm ${className}`}>
      {(title || subtitle) && (
        <div className="border-b border-ink-100 px-5 py-3">
          {title && <h3 className="text-sm font-semibold text-ink-800">{title}</h3>}
          {subtitle && <p className="mt-0.5 text-xs text-ink-500">{subtitle}</p>}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function StatTile({
  label,
  value,
  tone = "neutral",
  hint,
}: {
  label: string;
  value: string;
  tone?: "neutral" | "positive" | "negative" | "caution";
  hint?: string;
}) {
  const toneClass = {
    neutral: "text-ink-900",
    positive: "text-positive",
    negative: "text-negative",
    caution: "text-caution",
  }[tone];

  return (
    <div className="rounded-lg border border-ink-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-ink-500">{label}</div>
      <div className={`tabular mt-1 text-2xl font-semibold ${toneClass}`}>{value}</div>
      {hint && <div className="mt-1 text-xs text-ink-400">{hint}</div>}
    </div>
  );
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "positive" | "negative" | "caution" | "info" }) {
  const toneClass = {
    neutral: "bg-ink-100 text-ink-700",
    positive: "bg-emerald-50 text-positive",
    negative: "bg-red-50 text-negative",
    caution: "bg-amber-50 text-caution",
    info: "bg-blue-50 text-accent",
  }[tone];
  return <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${toneClass}`}>{children}</span>;
}

export function DemoBanner() {
  return (
    <div className="border-b border-amber-200 bg-amber-50 px-4 py-1.5 text-center text-xs font-medium text-amber-800">
      DEMO DATA — NOT OFFICIAL NFL DATA. All players, teams' rosters, and contract figures are synthetically
      generated for demonstration purposes only.
    </div>
  );
}

export function LoadingState() {
  return <div className="p-8 text-sm text-ink-400">Loading…</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="m-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-negative">
      {message}
    </div>
  );
}

export function Definition({ term, children }: { term: string; children: ReactNode }) {
  return (
    <details className="group inline-block">
      <summary className="inline-flex cursor-help list-none items-center gap-1 border-b border-dotted border-ink-400 text-inherit">
        {term}
      </summary>
      <div className="mt-1 max-w-xs rounded border border-ink-200 bg-white p-2 text-xs font-normal text-ink-600 shadow-md">
        {children}
      </div>
    </details>
  );
}
