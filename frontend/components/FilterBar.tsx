"use client";

import { DateInput, Select } from "@/components/ui";
import { useApi } from "@/lib/api";

export type FilterState = { start: string; end: string; region_group: string; category: string };
type Dims = { region_groups: string[]; categories: string[]; date_min: string; date_max: string };

export default function FilterBar({ value, onChange, show = ["dates", "region", "category"] }: {
  value: FilterState; onChange: (v: FilterState) => void; show?: ("dates" | "region" | "category")[];
}) {
  const { data } = useApi<Dims>("/api/meta/dimensions");
  return (
    <form className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-3" onSubmit={(e) => e.preventDefault()} aria-label="Filters">
      {show.includes("dates") && (
        <>
          <DateInput label="From" value={value.start} min={data?.date_min} max={data?.date_max} onChange={(start) => onChange({ ...value, start })} />
          <DateInput label="To" value={value.end} min={data?.date_min} max={data?.date_max} onChange={(end) => onChange({ ...value, end })} />
        </>
      )}
      {show.includes("region") && (
        <Select label="Region group" value={value.region_group} allLabel="All regions" options={data?.region_groups ?? []}
          onChange={(region_group) => onChange({ ...value, region_group })} />
      )}
      {show.includes("category") && (
        <Select label="Category" value={value.category} allLabel="All categories" options={data?.categories ?? []}
          onChange={(category) => onChange({ ...value, category })} />
      )}
      <button type="button" onClick={() => onChange({ start: "", end: "", region_group: "", category: "" })}
        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50">
        Reset
      </button>
      {data && <p className="text-xs text-slate-500">Data covers {data.date_min} to {data.date_max}.</p>}
    </form>
  );
}
