"use client";

import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataTable, Interpretation, Kpi, PageHeader, Status } from "@/components/ui";
import { type Row, useApi } from "@/lib/api";
import { COLORS, fmtGBP, fmtNumber, fmtPct } from "@/lib/format";

function describe(s: Row, med: Row) {
  const parts = [
    s.avg_recency_days <= med.recency_days ? "bought recently" : "has not bought for a while",
    s.avg_frequency >= med.frequency ? "orders often" : "orders rarely",
    s.median_spend >= med.monetary ? "spends above the median" : "spends below the median",
  ];
  return `A typical customer ${parts.join(", ")}.`;
}

export default function SegmentsPage() {
  const { data, loading, error, reload } = useApi<Row>("/api/customers/segments");
  const names: string[] = data ? data.segments.map((s: Row) => s.name) : [];

  return (
    <>
      <PageHeader title="Customer Segments"
        description="RFM (recency, frequency, monetary) features per identified customer, log-transformed and standardised, clustered with K-Means. Segment names come from rules applied to each cluster's median behaviour, not from hand-picking." />
      <Status loading={loading} error={error} what="customer segments" onRetry={reload} rows={6} />
      {data && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Customers clustered" value={fmtNumber(data.n_customers)} note="guest orders without ID excluded" />
            <Kpi label="Chosen k" value={String(data.chosen_k)} note={`best silhouette overall: k = ${data.best_k_silhouette}`} />
            <Kpi label="Silhouette at chosen k" value={data.silhouette_by_k.find((s: Row) => s.k === data.chosen_k).silhouette.toFixed(3)} />
            <Kpi label="Agreement with Ward (ARI)" value={data.ward_adjusted_rand_index.toFixed(3)} note="1 = identical clusterings" />
          </div>
          <Interpretation>
            k = {data.best_k_silhouette} has the highest silhouette but splits customers only into broad active/inactive halves; k = {data.chosen_k} is the best-scoring k ≥ 3 and gives segments that can be acted on.
            Hierarchical (Ward) clustering on a 3,000-customer sample agrees moderately (ARI {data.ward_adjusted_rand_index.toFixed(2)}), so the segment boundaries are reasonably (not perfectly) stable.
          </Interpretation>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card title="Silhouette score by k">
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={data.silhouette_by_k}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="k" tick={{ fontSize: 11 }} />
                  <YAxis domain={["auto", "auto"]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => Number(v).toFixed(3)} />
                  <Line dataKey="silhouette" stroke={COLORS[0]} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
            <Card title="PCA projection (1,500-customer sample)" subtitle={`PC1 ${data.pca_explained_variance_pct[0]}% + PC2 ${data.pca_explained_variance_pct[1]}% of variance`}>
              <ResponsiveContainer width="100%" height={260}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" dataKey="pc1" name="PC1" tick={{ fontSize: 11 }} />
                  <YAxis type="number" dataKey="pc2" name="PC2" tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  {names.map((n, i) => (
                    <Scatter key={n} name={n} data={data.pca_points.filter((p: Row) => p.segment === n)} fill={COLORS[i % COLORS.length]} fillOpacity={0.6} r={2} />
                  ))}
                </ScatterChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <Card title="Segment profiles" className="mt-4">
            <DataTable caption="Segments" rows={data.segments} columns={[
              { key: "name", label: "Segment" },
              { key: "customers", label: "Customers", align: "right", format: (v, r) => `${fmtNumber(v)} (${fmtPct(r.customer_share_pct)})` },
              { key: "revenue_share_pct", label: "Revenue share", align: "right", format: (v) => fmtPct(v) },
              { key: "avg_spend", label: "Avg spend", align: "right", format: (v) => fmtGBP(v) },
              { key: "avg_frequency", label: "Avg orders", align: "right", format: (v) => fmtNumber(v, 1) },
              { key: "avg_recency_days", label: "Avg recency (days)", align: "right", format: (v) => fmtNumber(v) },
            ]} />
            <p className="mt-2 text-xs text-slate-500">Naming rules: {data.naming_rules} Medians: recency {data.medians.recency_days} days, frequency {data.medians.frequency} orders, spend {fmtGBP(data.medians.monetary)}.</p>
          </Card>

          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <Card title="Revenue share vs customer share">
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data.segments}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} interval={0} />
                  <YAxis unit="%" tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => fmtPct(Number(v))} />
                  <Legend />
                  <Bar dataKey="customer_share_pct" name="Customers %" fill={COLORS[1]} />
                  <Bar dataKey="revenue_share_pct" name="Revenue %" fill={COLORS[0]} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
            <Card title="Business interpretation">
              <ul className="space-y-2 text-sm text-slate-700">
                {data.segments.map((s: Row) => (
                  <li key={s.name}><strong>{s.name}</strong>: {fmtPct(s.customer_share_pct)} of customers, {fmtPct(s.revenue_share_pct)} of revenue. {describe(s, data.medians)}</li>
                ))}
              </ul>
            </Card>
          </div>
        </>
      )}
    </>
  );
}
