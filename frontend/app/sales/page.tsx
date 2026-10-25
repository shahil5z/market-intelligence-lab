"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import FilterBar, { type FilterState } from "@/components/FilterBar";
import { Card, DataTable, Interpretation, Note, PageHeader, Status } from "@/components/ui";
import { type Row, useApi } from "@/lib/api";
import { COLORS, compact, fmtGBP, fmtNumber, fmtP, fmtPct } from "@/lib/format";

const EMPTY: FilterState = { start: "", end: "", region_group: "", category: "" };

function corrColor(v: number) {
  const a = Math.min(Math.abs(v), 1);
  return v >= 0 ? `rgba(15,118,110,${a})` : `rgba(124,58,237,${a})`;
}

export default function SalesPage() {
  const [f, setF] = useState<FilterState>(EMPTY);
  const { data, loading, error, reload } = useApi<Row>("/api/sales/eda", { region_group: f.region_group, category: f.category });
  const regions = useApi<{ rows: Row[] }>("/api/sales/by-region", { category: f.category });
  const vars = ["units", "avg_price", "discount_pct", "customers", "is_pre_christmas"];

  return (
    <>
      <PageHeader title="Sales Analysis (EDA)"
        description="Exploratory analysis of the cleaned transactions: seasonality, weekday pattern, price and discount versus demand, regional behaviour and campaign periods. Each chart has a short reading of what the numbers show." />
      <FilterBar value={f} onChange={setF} show={["region", "category"]} />
      <div className="mt-4"><Status loading={loading} error={error} what="sales data" onRetry={reload} rows={6} /></div>
      {data && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Card title="Seasonality: monthly revenue, 2010 vs 2011" subtitle={data.seasonality.note} className="lg:col-span-2">
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.seasonality.rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => fmtGBP(Number(v))} />
                <Legend />
                <Line dataKey="2010" stroke={COLORS[1]} strokeWidth={2} />
                <Line dataKey="2011" stroke={COLORS[0]} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
            <Interpretation>
              In 2010, revenue peaked in {data.seasonality.peak_month_2010} and October-December produced {fmtPct(data.seasonality.q4_share_2010_pct)} of the
              year’s revenue. A clear autumn build-up is consistent with a gift/homeware wholesaler stocking up before Christmas.
            </Interpretation>
          </Card>

          <Card title="Weekday pattern" subtitle="Average revenue per trading day">
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={data.weekday.rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="weekday" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => fmtGBP(Number(v))} />
                <Bar dataKey="revenue_per_trading_day" name="Revenue per trading day" fill={COLORS[0]} />
              </BarChart>
            </ResponsiveContainer>
            <Interpretation>
              {data.weekday.best_weekday} has the highest revenue per trading day.
              {data.weekday.days_without_sales.length > 0 && ` No sales are recorded on ${data.weekday.days_without_sales.join(", ")}, so "weekend" in this data means Sunday only.`}
            </Interpretation>
          </Card>

          <Card title="Regional behaviour" subtitle="Average order value by region group">
            <Status loading={regions.loading} error={regions.error} what="regional sales" onRetry={regions.reload} empty={regions.data?.rows.length === 0} rows={5} />
            {regions.data && (
              <DataTable caption="Regions" rows={regions.data.rows} columns={[
                { key: "region_group", label: "Region group" },
                { key: "revenue_share_pct", label: "Revenue share", align: "right", format: (v) => fmtPct(v) },
                { key: "aov", label: "AOV", align: "right", format: (v) => fmtGBP(v, 0) },
                { key: "customers", label: "Customers", align: "right", format: (v) => fmtNumber(v) },
              ]} />
            )}
            {regions.data && regions.data.rows.length > 0 && (() => {
              const r = [...regions.data.rows].sort((a, b) => b.aov - a.aov)[0];
              return <Interpretation>{r.region_group} has the highest average order value ({fmtGBP(r.aov)}), compared with an overall range of {fmtGBP(Math.min(...regions.data.rows.map((x) => x.aov)))} to {fmtGBP(r.aov)}.</Interpretation>;
            })()}
          </Card>

          <Card title="Price vs demand" subtitle={`Product-weeks grouped into price deciles (n = ${fmtNumber(data.correlations.n)})`}>
            <ResponsiveContainer width="100%" height={230}>
              <ComposedChart data={data.correlations.price_deciles}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="median_price" tickFormatter={(v) => `£${v}`} tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="median_units" name="Median weekly units" fill={COLORS[3]} />
                <Line dataKey="mean_units" name="Mean weekly units" stroke={COLORS[5]} />
              </ComposedChart>
            </ResponsiveContainer>
            <Interpretation>
              Spearman ρ between average price and weekly units = {data.correlations.price_vs_units_spearman} (p {fmtP(data.correlations.price_vs_units_p_value)}).
              {data.correlations.price_vs_units_spearman < 0 ? " Cheaper items sell in larger quantities." : " Higher-priced items do not sell in smaller quantities here."} This compares different products, so it is not a price elasticity.
            </Interpretation>
          </Card>

          <Card title="Discount vs quantity" subtitle={data.discount.definition}>
            <DataTable caption="Discount bands" rows={data.discount.rows} columns={[
              { key: "band", label: "Price reduction band" },
              { key: "lines", label: "Lines", align: "right", format: (v) => fmtNumber(v) },
              { key: "avg_quantity", label: "Mean qty / line", align: "right", format: (v) => fmtNumber(v, 1) },
              { key: "median_quantity", label: "Median qty", align: "right", format: (v) => fmtNumber(v, 0) },
            ]} />
            <Interpretation>
              Compare mean quantity across bands. The dataset has no promotion flag, so a lower price on a line most likely reflects tiered wholesale (volume) pricing; this is an inference (NOT VERIFIED), not a measured promotion effect.
            </Interpretation>
          </Card>

          <Card title="Correlation matrix (Spearman, product-week level)">
            <div className="overflow-x-auto">
              <table className="text-xs">
                <caption className="sr-only">Correlation matrix</caption>
                <thead><tr><th />{vars.map((v) => <th key={v} scope="col" className="px-1 py-1 font-medium text-slate-600">{v}</th>)}</tr></thead>
                <tbody>
                  {data.correlations.matrix.map((r: Row) => (
                    <tr key={r.variable}>
                      <th scope="row" className="pr-2 text-left font-medium text-slate-600">{r.variable}</th>
                      {vars.map((v) => (
                        <td key={v} className="h-9 w-16 text-center tabular-nums" style={{ background: corrColor(r[v]), color: Math.abs(r[v]) > 0.5 ? "white" : "#0f172a" }}>
                          {r[v].toFixed(2)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {(() => {
              const pairs = data.correlations.matrix.flatMap((r: Row) => vars.filter((v) => v > r.variable).map((v) => ({ a: r.variable, b: v, r: r[v] as number })));
              const top = pairs.sort((x: Row, y: Row) => Math.abs(y.r) - Math.abs(x.r))[0];
              return <Interpretation>Teal = positive, violet = negative. The strongest pair is {top.a} and {top.b} (ρ = {top.r.toFixed(2)}).</Interpretation>;
            })()}
          </Card>

          <Card title="Campaign periods">
            <Note tone="warn">{data.campaign_periods.note}</Note>
            <p className="mt-3 text-sm text-slate-700">
              Revenue inside synthetic campaign windows/targets: <strong>{fmtGBP(data.campaign_periods.campaign_revenue)}</strong> ({fmtPct(data.campaign_periods.campaign_share_pct, 2)} of the selection).
              See Campaign Analysis for the statistics.
            </p>
          </Card>
        </div>
      )}
    </>
  );
}
