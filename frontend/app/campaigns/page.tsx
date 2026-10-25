"use client";

import { useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataTable, Interpretation, Kpi, Note, PageHeader, Status } from "@/components/ui";
import { type Row, useApi } from "@/lib/api";
import { COLORS, compact, fmtGBP, fmtNumber, fmtP, fmtPct } from "@/lib/format";

export default function CampaignsPage() {
  const list = useApi<Row>("/api/campaigns");
  const [id, setId] = useState<number | null>(null);
  const firstOk = list.data?.campaigns.find((c: Row) => c.sufficient_data)?.campaign_id;
  const selected = id ?? firstOk;
  const detail = useApi<Row>(selected ? `/api/campaigns/${selected}` : "/api/campaigns", {});
  const c = detail.data?.campaign_id ? detail.data : null;

  return (
    <>
      <PageHeader title="Campaign Analysis"
        description="Observed performance of each campaign window against its own pre-period and against a control group (difference-in-differences). This is an observational analysis of synthetic campaigns — it demonstrates the method, not real marketing effects." />
      <Status loading={list.loading} error={list.error} />
      {list.data && (
        <>
          <Note tone="warn"><strong>Observational · synthetic campaigns.</strong> {list.data.label}</Note>
          <Card title="All campaigns" subtitle="Select a row to see its detail. Revenue = real sales attributed to the campaign's target segment during its window." className="mt-4">
            <DataTable caption="Campaigns" rows={list.data.campaigns} columns={[
              { key: "campaign_name", label: "Campaign", format: (v, r) => (
                <button type="button" onClick={() => setId(r.campaign_id)} className={`underline-offset-2 hover:underline ${r.campaign_id === selected ? "font-semibold text-teal-800" : "text-slate-900"}`}>{v}</button>
              ) },
              { key: "channel", label: "Channel" },
              { key: "target_region_group", label: "Target region" },
              { key: "target_category", label: "Target category" },
              { key: "start_date", label: "Start" },
              { key: "budget", label: "Budget", align: "right", format: (v) => fmtGBP(v) },
              { key: "revenue", label: "Revenue", align: "right", format: (v) => fmtGBP(v) },
              { key: "observed_uplift_pct", label: "Observed uplift", align: "right", format: (v, r) => (r.sufficient_data ? fmtPct(v, 1, true) : "insufficient data") },
              { key: "welch_p_value", label: "p (Welch)", align: "right", format: (v) => (v === undefined || v === null ? "—" : fmtP(v)) },
              { key: "naive_roi_pct", label: "Naive ROI", align: "right", format: (v) => (v === undefined || v === null ? "—" : fmtPct(v, 0, true)) },
            ]} />
          </Card>
        </>
      )}
      {c && (
        <>
          <h2 className="mt-6 text-lg font-semibold text-slate-900">{c.campaign_name}: {c.target_category} in {c.target_region_group}</h2>
          <p className="text-sm text-slate-600">{c.channel} · {c.campaign_type} · {c.start_date} to {c.end_date} ({c.duration_days} days) · baseline {c.pre_period.start} to {c.pre_period.end}</p>
          <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Revenue in window" value={fmtGBP(c.revenue)} note={`${fmtNumber(c.orders)} orders · ${fmtNumber(c.units)} units`} />
            <Kpi label="AOV (campaign lines)" value={fmtGBP(c.aov, 2)} />
            <Kpi label="Budget (synthetic)" value={fmtGBP(c.budget)} />
            <Kpi label="Naive ROI" value={c.sufficient_data ? fmtPct(c.naive_roi_pct, 0, true) : "n/a"} note="(observed incremental revenue − budget) / budget" />
          </div>
          {c.sufficient_data ? (
            <>
              <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
                <Kpi label="Observed uplift vs pre-period" value={fmtPct(c.observed_uplift_pct, 1, true)}
                  note={`daily mean ${fmtGBP(c.pre_mean_daily_revenue)} → ${fmtGBP(c.during_mean_daily_revenue)}`} />
                <Kpi label="Difference, 95% CI (Welch)" value={`${fmtGBP(c.difference_mean_daily)} / day`}
                  note={`[${fmtGBP(c.difference_ci95[0])}, ${fmtGBP(c.difference_ci95[1])}] · p = ${fmtP(c.welch_p_value)}`} />
                <Kpi label="Difference-in-differences" value={`${fmtGBP(c.did_estimate_daily)} / day`}
                  note={`95% CI [${fmtGBP(c.did_ci95[0])}, ${fmtGBP(c.did_ci95[1])}] · p = ${fmtP(c.did_p_value)}`} />
              </div>
              <Interpretation>
                Daily revenue in the target segment was {fmtPct(Math.abs(c.observed_uplift_pct))} {c.observed_uplift_pct >= 0 ? "higher" : "lower"} during the window than in the pre-period.
                {c.welch_p_value < 0.05 ? " This difference is statistically significant at the 5% level" : " This difference is not statistically significant at the 5% level"}
                {c.did_p_value < 0.05 ? ", and relative to the control group the DiD estimate is also significant." : "; relative to the control group the DiD estimate is not significant."}
                {" "}Because the campaign is synthetic, any difference reflects ordinary variation in real sales, not a campaign effect.
              </Interpretation>
            </>
          ) : (
            <div className="mt-3"><Note>{c.note}</Note></div>
          )}
          <Card title="Daily revenue: target segment vs control" subtitle={c.control_definition ?? "Control: same category in other region groups"} className="mt-4">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={c.daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={30} />
                <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => fmtGBP(Number(v))} />
                <Legend />
                <ReferenceLine x={c.start_date} stroke="#0f172a" strokeDasharray="4 4" label={{ value: "start", fontSize: 11 }} />
                <Line dataKey="treated" name="Target segment" stroke={COLORS[0]} dot={false} />
                <Line dataKey="control" name="Control" stroke={COLORS[1]} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
          <Card title="Assumptions and limitations" className="mt-4">
            <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
              {c.assumptions.map((a: string) => <li key={a}>{a}</li>)}
            </ul>
          </Card>
        </>
      )}
    </>
  );
}
