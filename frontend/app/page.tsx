"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import FilterBar, { type FilterState } from "@/components/FilterBar";
import { Card, DataTable, Interpretation, Kpi, PageHeader, Select, Status } from "@/components/ui";
import { type Row, useApi } from "@/lib/api";
import { COLORS, compact, fmtGBP, fmtNumber, fmtPct } from "@/lib/format";

const EMPTY: FilterState = { start: "", end: "", region_group: "", category: "" };

export default function OverviewPage() {
  const [f, setF] = useState<FilterState>(EMPTY);
  const [grain, setGrain] = useState("month");
  const ov = useApi<Row>("/api/overview", f);
  const trend = useApi<{ rows: Row[] }>("/api/sales/trend", { ...f, grain });
  const regions = useApi<{ rows: Row[] }>("/api/sales/by-region", { start: f.start, end: f.end, category: f.category });
  const products = useApi<{ categories: Row[]; top_products: Row[] }>("/api/sales/by-product", { start: f.start, end: f.end, region_group: f.region_group, limit: "10" });
  const dist = useApi<Row>("/api/sales/distribution", f);
  const o = ov.data;

  return (
    <>
      <PageHeader title="Executive Overview"
        description="Headline sales KPIs computed live from the cleaned transaction table. Use the filters to focus on a period, region group or product category. Revenue is in GBP (the dataset's currency)." />
      <FilterBar value={f} onChange={setF} />
      <div className="mt-4"><Status loading={ov.loading} error={ov.error} what="the sales overview" onRetry={ov.reload} rows={2} /></div>
      {o && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Revenue" value={fmtGBP(o.revenue)} />
            <Kpi label="Units sold" value={fmtNumber(o.units)} />
            <Kpi label="Avg order value" value={fmtGBP(o.aov, 2)} note={`${fmtNumber(o.orders)} orders`} />
            <Kpi label="Growth rate" value={fmtPct(o.growth_rate_pct, 1, true)} note={`vs ${o.growth_comparison}`} />
            <Kpi label="Customers (with ID)" value={fmtNumber(o.customers)} />
            <Kpi label="Products sold" value={fmtNumber(o.products)} />
            <Kpi label="Top region group" value={o.top_region} note={`${fmtPct(o.top_region_share_pct)} of revenue`} />
            <Kpi label="Top category" value={o.top_category} note={`Top product: ${o.top_product}`} />
          </div>
          <Interpretation>
            Between {o.filters.start} and {o.filters.end} the selection generated {fmtGBP(o.revenue)} from {fmtNumber(o.orders)} orders.
            {o.growth_rate_pct !== null
              ? ` Revenue is ${fmtPct(Math.abs(o.growth_rate_pct))} ${o.growth_rate_pct >= 0 ? "higher" : "lower"} than in the equally long period before it.`
              : " No earlier period of equal length exists, so growth is not computed."}{" "}
            {o.top_region} is the largest region group ({fmtPct(o.top_region_share_pct)} of revenue).
          </Interpretation>
        </>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card title="Revenue and units over time" subtitle="Partial first/last periods are shown as-is" className="lg:col-span-2">
          <div className="mb-2 w-40"><Select label="Granularity" value={grain} onChange={setGrain} options={["day", "week", "month", "quarter"]} /></div>
          <Status loading={trend.loading} error={trend.error} what="sales data" onRetry={trend.reload} empty={trend.data?.rows.length === 0} rows={6} />
          {trend.data && (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trend.data.rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="period" tick={{ fontSize: 11 }} minTickGap={24} />
                <YAxis yAxisId="l" tickFormatter={compact} tick={{ fontSize: 11 }} />
                <YAxis yAxisId="r" orientation="right" tickFormatter={compact} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => fmtNumber(Number(v))} />
                <Legend />
                <Line yAxisId="l" type="monotone" dataKey="revenue" name="Revenue (£)" stroke={COLORS[0]} dot={false} strokeWidth={2} />
                <Line yAxisId="r" type="monotone" dataKey="units" name="Units" stroke={COLORS[1]} dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>
        <Card title="Revenue by region group">
          <Status loading={regions.loading} error={regions.error} what="regional sales" onRetry={regions.reload} empty={regions.data?.rows.length === 0} rows={5} />
          {regions.data && (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={regions.data.rows} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tickFormatter={compact} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="region_group" width={130} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => fmtGBP(Number(v))} />
                <Bar dataKey="revenue" name="Revenue" fill={COLORS[0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
        <Card title="Revenue by product category" subtitle="Categories are rule-based keyword groups of real product descriptions">
          <Status loading={products.loading} error={products.error} what="product sales" onRetry={products.reload} empty={products.data?.top_products.length === 0} rows={5} />
          {products.data && (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={products.data.categories} layout="vertical" margin={{ left: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" tickFormatter={compact} tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="category" width={130} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => fmtGBP(Number(v))} />
                <Bar dataKey="revenue" name="Revenue" fill={COLORS[2]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
        <Card title="Order value distribution" subtitle="Number of orders (invoices) per order-value band, £">
          <Status loading={dist.loading} error={dist.error} what="the order value distribution" onRetry={dist.reload} rows={5} />
          {dist.data && (
            <>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={dist.data.bins}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                  <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="orders" name="Orders" fill={COLORS[3]} />
                </BarChart>
              </ResponsiveContainer>
              <Interpretation>
                Mean order value {fmtGBP(dist.data.mean, 2)} vs median {fmtGBP(dist.data.median, 2)} (skewness {dist.data.skewness}):
                {dist.data.mean > dist.data.median ? " the distribution is right-skewed, so a few large wholesale orders pull the mean up." : " the distribution is roughly symmetric."}
              </Interpretation>
            </>
          )}
        </Card>
        <Card title="Top 10 products by revenue">
          {products.data && (
            <DataTable caption="Top products" rows={products.data.top_products} columns={[
              { key: "product_name", label: "Product" },
              { key: "category", label: "Category" },
              { key: "revenue", label: "Revenue", align: "right", format: (v) => fmtGBP(v) },
              { key: "units", label: "Units", align: "right", format: (v) => fmtNumber(v) },
            ]} />
          )}
        </Card>
      </div>
    </>
  );
}
