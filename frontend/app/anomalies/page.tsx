"use client";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataTable, Interpretation, Note, PageHeader, Select, Status } from "@/components/ui";
import { type Row, useApi } from "@/lib/api";
import { COLORS, compact, fmtNumber, fmtPct } from "@/lib/format";

const SEVERITY_STYLE: Record<string, string> = {
  high: "bg-rose-100 text-rose-900",
  medium: "bg-amber-100 text-amber-900",
  low: "bg-slate-100 text-slate-800",
};

export default function AnomaliesPage() {
  const [region, setRegion] = useState("");
  const [metric, setMetric] = useState("");
  const [severity, setSeverity] = useState("");
  const { data, loading, error } = useApi<Row>("/api/anomalies", { region, metric, severity, limit: "100" });

  return (
    <>
      <PageHeader title="Anomaly Detection"
        description="Weeks whose revenue (per region group) or units (top-10 products) deviate strongly from the recent past, using a robust rolling z-score. Each row explains why it was flagged." />
      <div className="flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <Select label="Region" value={region} onChange={setRegion} allLabel="All" options={data?.regions ?? []} />
        <Select label="Metric" value={metric} onChange={setMetric} allLabel="All" options={["revenue", "units"]} />
        <Select label="Severity" value={severity} onChange={setSeverity} allLabel="All" options={["high", "medium", "low"]} />
      </div>
      <div className="mt-4"><Status loading={loading} error={error} /></div>
      {data && (
        <>
          <div className="mt-4"><Note>{data.method} Expected range: {data.expected_range_rule}. Severity: {data.severity_rule}.</Note></div>
          <Card title={`Weekly revenue — ${data.series_name}`} subtitle="Dots mark flagged weeks (teal = spike, violet = drop)" className="mt-4">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={data.series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={30} />
                <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => `£${fmtNumber(Number(v))}`} />
                <Line dataKey="value" name="Revenue" stroke={COLORS[1]} dot={false} />
                {data.series_anomalies.map((a: Row) => (
                  <ReferenceDot key={a.date} x={a.date} y={a.observed} r={5} fill={a.direction === "spike" ? COLORS[0] : COLORS[2]} stroke="white" />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </Card>
          <Card title={`Flagged weeks (${data.n_matching} matching of ${data.total_flagged})`} className="mt-4">
            <DataTable caption="Anomalies" rows={data.anomalies} columns={[
              { key: "date", label: "Week of" },
              { key: "region", label: "Region" },
              { key: "product", label: "Product" },
              { key: "metric", label: "Metric" },
              { key: "observed", label: "Observed", align: "right", format: (v) => fmtNumber(v) },
              { key: "expected_low", label: "Expected range", align: "right", format: (v, r) => `${fmtNumber(v)} – ${fmtNumber(r.expected_high)}` },
              { key: "deviation_pct", label: "Deviation", align: "right", format: (v) => fmtPct(v, 0, true) },
              { key: "z_score", label: "Robust z", align: "right", format: (v) => v.toFixed(1) },
              { key: "severity", label: "Severity", format: (v) => <span className={`rounded px-1.5 py-0.5 text-xs ${SEVERITY_STYLE[v]}`}>{v}</span> },
              { key: "reason", label: "Why flagged" },
            ]} />
            {data.anomalies.length > 0 && (
              <Interpretation>
                {data.anomalies.filter((a: Row) => a.direction === "drop").length} of the {data.anomalies.length} rows shown are drops.
                {" "}{data.anomalies.filter((a: Row) => a.reason.includes("Christmas")).length} overlap the Christmas/New Year closure, where a drop is expected rather than a business problem.
                Product-level spikes in a low-volume series can come from a single large order. Flags are prompts for investigation, not confirmed incidents.
              </Interpretation>
            )}
          </Card>
        </>
      )}
    </>
  );
}
