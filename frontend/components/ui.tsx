// Small presentational building blocks shared by all pages.
import type { ReactNode } from "react";
import type { Row } from "@/lib/api";

export function PageHeader({ title, description, children }: { title: string; description: string; children?: ReactNode }) {
  return (
    <header className="mb-6">
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      <p className="mt-1 max-w-3xl text-sm text-slate-600">{description}</p>
      {children}
    </header>
  );
}

export function Card({ title, subtitle, children, className = "" }: { title?: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`min-w-0 rounded-lg border border-slate-200 bg-white p-4 ${className}`}>
      {title && <h2 className="text-sm font-semibold text-slate-900">{title}</h2>}
      {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      <div className={title ? "mt-3" : ""}>{children}</div>
    </section>
  );
}

export function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900">{value}</p>
      {note && <p className="mt-1 text-xs text-slate-500">{note}</p>}
    </div>
  );
}

export function Note({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "warn" }) {
  const styles = tone === "warn" ? "border-amber-300 bg-amber-50 text-amber-900" : "border-slate-200 bg-slate-50 text-slate-700";
  return <div className={`rounded-md border px-3 py-2 text-sm ${styles}`}>{children}</div>;
}

export function Interpretation({ children }: { children: ReactNode }) {
  return (
    <div className="mt-3 border-l-2 border-teal-700 pl-3 text-sm text-slate-700">
      <span className="font-medium text-slate-900">Interpretation: </span>
      {children}
    </div>
  );
}

/**
 * Loading / error / empty state for one async section.
 * `what` names the data in plain words, e.g. "sales data" -> "Unable to load sales data. Please try again."
 */
export function Status({ loading, error, what = "this data", onRetry, empty = false, rows = 3 }: {
  loading: boolean; error: string | null; what?: string; onRetry?: () => void; empty?: boolean; rows?: number;
}) {
  if (error)
    return (
      <div role="alert" className="flex flex-wrap items-center gap-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-900">
        <span>Unable to load {what}. Please try again.</span>
        {onRetry && (
          <button type="button" onClick={onRetry} className="rounded border border-rose-400 bg-white px-2 py-0.5 text-xs font-medium hover:bg-rose-100">
            Retry
          </button>
        )}
      </div>
    );
  if (loading) return <Skeleton rows={rows} label={`Loading ${what}`} />;
  if (empty)
    return <p className="rounded-md border border-dashed border-slate-300 px-3 py-4 text-center text-sm text-slate-500">No {what} for the selected filters.</p>;
  return null;
}

export function Skeleton({ rows = 3, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div role="status" aria-label={label} className="animate-pulse space-y-2">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="h-4 rounded bg-slate-200" style={{ width: `${95 - i * 12}%` }} />
      ))}
      <span className="sr-only">{label}…</span>
    </div>
  );
}

type Column = { key: string; label: string; format?: (v: Row[string], row: Row) => ReactNode; align?: "right" };

export function DataTable({ rows, columns, caption }: { rows: Row[]; columns: Column[]; caption?: string }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
            {columns.map((c) => (
              <th key={c.key} scope="col" className={`whitespace-nowrap px-2 py-2 font-medium ${c.align === "right" ? "text-right" : ""}`}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-b border-slate-100 last:border-0">
              {columns.map((c) => (
                <td key={c.key} className={`px-2 py-1.5 text-slate-800 ${c.align === "right" ? "text-right tabular-nums" : ""}`}>
                  {c.format ? c.format(r[c.key], r) : String(r[c.key] ?? "n/a")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Select({ label, value, onChange, options, allLabel }: {
  label: string; value: string; onChange: (v: string) => void; options: string[]; allLabel?: string;
}) {
  const id = `sel-${label.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-slate-600">{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900">
        {allLabel !== undefined && <option value="">{allLabel}</option>}
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </div>
  );
}

export function DateInput({ label, value, onChange, min, max }: { label: string; value: string; onChange: (v: string) => void; min?: string; max?: string }) {
  const id = `date-${label.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-slate-600">{label}</label>
      <input id={id} type="date" value={value} min={min} max={max} onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-900" />
    </div>
  );
}
