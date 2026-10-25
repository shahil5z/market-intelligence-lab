"use client";

import { useState } from "react";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataTable, Interpretation, Kpi, Note, PageHeader, Select, Status } from "@/components/ui";
import { type Row, postJson, useApi } from "@/lib/api";
import { COLORS, fmtNumber, fmtP } from "@/lib/format";

const TESTS = { welch: "Welch t-test", student: "Student t-test", chi_square: "Chi-square test", correlation: "Correlation" } as const;
type TestKey = keyof typeof TESTS;

export default function StatisticsPage() {
  const opts = useApi<Row>("/api/statistics/options");
  const [test, setTest] = useState<TestKey>("welch");
  const [metric, setMetric] = useState("order_value");
  const [dimension, setDimension] = useState("region_group");
  const [groupA, setGroupA] = useState("United Kingdom");
  const [groupB, setGroupB] = useState("Western Europe");
  const [rowDim, setRowDim] = useState("region_group");
  const [colDim, setColDim] = useState("order_size_band");
  const [x, setX] = useState("avg_price");
  const [y, setY] = useState("units");
  const [method, setMethod] = useState("spearman");
  const [result, setResult] = useState<Row | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const levels: string[] = opts.data?.dimensions?.[dimension] ?? [];
  const dims = Object.keys(opts.data?.dimensions ?? {});

  async function run(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    const body: Row = { test };
    if (test === "welch" || test === "student") Object.assign(body, { metric, dimension, group_a: groupA, group_b: groupB });
    if (test === "chi_square") Object.assign(body, { row_dimension: rowDim, col_dimension: colDim });
    if (test === "correlation") Object.assign(body, { x, y, method });
    try {
      setResult(await postJson<Row>("/api/statistics/test", body));
    } catch (ex) {
      setResult(null);
      setErr((ex as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Statistics Lab"
        description="Run a hypothesis test on the real order data. Choose a test, a metric and the groups to compare; the backend computes the statistics with SciPy and returns sample sizes, means, the difference with its 95% confidence interval, the p-value and an effect size." />
      <Status loading={opts.loading} error={opts.error} />
      {opts.data && (
        <form onSubmit={run} className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-3" aria-label="Test settings">
          <Select label="Test" value={test} onChange={(v) => { setTest(v as TestKey); setResult(null); }} options={Object.keys(TESTS)} />
          {(test === "welch" || test === "student") && (
            <>
              <Select label="Metric (per order)" value={metric} onChange={setMetric} options={opts.data.metrics} />
              <Select label="Compare groups of" value={dimension} onChange={(d) => { setDimension(d); const l = opts.data!.dimensions[d]; setGroupA(l[0]); setGroupB(l[1] ?? l[0]); }} options={dims} />
              <Select label="Group A" value={groupA} onChange={setGroupA} options={levels} />
              <Select label="Group B" value={groupB} onChange={setGroupB} options={levels} />
            </>
          )}
          {test === "chi_square" && (
            <>
              <Select label="Rows" value={rowDim} onChange={setRowDim} options={dims} />
              <Select label="Columns" value={colDim} onChange={setColDim} options={dims} />
            </>
          )}
          {test === "correlation" && (
            <>
              <Select label="X (product-week)" value={x} onChange={setX} options={opts.data.correlation_variables} />
              <Select label="Y (product-week)" value={y} onChange={setY} options={opts.data.correlation_variables} />
              <Select label="Method" value={method} onChange={setMethod} options={["spearman", "pearson"]} />
            </>
          )}
          <button type="submit" disabled={busy} className="rounded-md bg-slate-900 px-4 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">
            {busy ? "Running…" : "Run test"}
          </button>
        </form>
      )}
      {err && <div className="mt-4" role="alert"><Note tone="warn">{err}</Note></div>}
      {result && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Test" value={result.test} note={`unit: ${result.unit}`} />
            <Kpi label="p-value" value={fmtP(result.p_value)} note={result.significant_at_5pct ? "below 0.05" : "0.05 or above"} />
            <Kpi label={result.effect_size.name} value={result.effect_size.value.toFixed(3)} note={result.effect_size.magnitude} />
            {result.difference !== undefined && (
              <Kpi label="Difference (A − B)" value={fmtNumber(result.difference, 2)} note={`95% CI [${fmtNumber(result.difference_ci95[0], 2)}, ${fmtNumber(result.difference_ci95[1], 2)}]`} />
            )}
            {result.r !== undefined && <Kpi label="r" value={result.r.toFixed(3)} note={`95% CI [${result.r_ci95[0].toFixed(3)}, ${result.r_ci95[1].toFixed(3)}] · n = ${fmtNumber(result.n)}`} />}
            {result.statistic !== undefined && result.df !== undefined && <Kpi label="Test statistic" value={result.statistic.toFixed(2)} note={`df = ${fmtNumber(result.df, 0)}`} />}
          </div>
          {result.groups && (
            <Card title="Groups">
              <DataTable caption="Groups" rows={result.groups} columns={[
                { key: "name", label: "Group" },
                { key: "n", label: "n", align: "right", format: (v) => fmtNumber(v) },
                { key: "mean", label: "Mean", align: "right", format: (v) => fmtNumber(v, 2) },
                { key: "mean_ci95", label: "95% CI of mean", align: "right", format: (v) => `${fmtNumber(v[0], 2)} – ${fmtNumber(v[1], 2)}` },
                { key: "median", label: "Median", align: "right", format: (v) => fmtNumber(v, 2) },
                { key: "std", label: "Std dev", align: "right", format: (v) => fmtNumber(v, 2) },
              ]} />
            </Card>
          )}
          {result.table && (
            <Card title={`Contingency table (n = ${fmtNumber(result.n)})`}>
              <DataTable caption="Contingency table" rows={result.table} columns={[{ key: "level", label: "" }, ...result.columns.map((c: string) => ({ key: c, label: c, align: "right" as const, format: (v: number) => fmtNumber(v) }))]} />
            </Card>
          )}
          {result.sample_points && (
            <Card title={`${result.x} vs ${result.y} (600-point random sample)`}>
              <ResponsiveContainer width="100%" height={260}>
                <ScatterChart>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis type="number" dataKey="x" name={result.x} scale="log" domain={["auto", "auto"]} allowDataOverflow tick={{ fontSize: 11 }} />
                  <YAxis type="number" dataKey="y" name={result.y} scale="log" domain={["auto", "auto"]} allowDataOverflow tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Scatter data={result.sample_points.filter((p: Row) => p.x > 0 && p.y > 0)} fill={COLORS[0]} fillOpacity={0.5} />
                </ScatterChart>
              </ResponsiveContainer>
              <p className="text-xs text-slate-500">Log scales; points with zero values are hidden in the chart but included in the test.</p>
            </Card>
          )}
          <Card title="What this means">
            <Interpretation>{result.interpretation}</Interpretation>
            <p className="mt-3 text-sm text-slate-700"><strong>Statistical vs business significance.</strong> {result.business_note}</p>
            {result.caveat && <p className="mt-2 text-sm text-slate-600">Caveat: {result.caveat}</p>}
          </Card>
        </div>
      )}
    </>
  );
}
