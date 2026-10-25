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
    <section className={`rounded-lg border border-slate-200 bg-white p-4 ${className}`}>
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

export function Status({ loading, error }: { loading: boolean; error: string | null }) {
  if (error)
    return (
      <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-900">
        Could not load data: {error}. Is the backend running on port 8000?
      </div>
    );
  if (loading) return <p className="text-sm text-slate-500" role="status">Loading…</p>;
  return null;
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
