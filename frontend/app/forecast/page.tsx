"use client";

import { useMemo, useState } from "react";
import { Area, Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataTable, Interpretation, Kpi, Note, PageHeader, Select, Status } from "@/components/ui";
import { type Row, useApi } from "@/lib/api";
import { COLORS, compact, fmtNumber, fmtPct } from "@/lib/format";

export default function ForecastPage() {
  const [series, setSeries] = useState("All regions");
  const [model, setModel] = useState("");
  const { data, loading, error, reload } = useApi<Row>("/api/demand/forecast", { series });
  const shown = model || data?.selected_model;

  const chartRows = useMemo(() => {
    if (!data) return [];
    const hist = data.history.map((h: Row) => ({ week: h.week_start, actual: h.actual, predicted: h[shown] ?? null, split: h.split }));
    const fut = data.future.map((f: Row) => ({ week: f.week_start, forecast: f.forecast, band: [f.lower, f.upper] }));
    return [...hist, ...fut];
  }, [data, shown]);

  const metricRows = data
    ? Object.keys(data.test_metrics).map((m) => ({
        model: m,
        val_mae: data.validation_metrics[m].mae,
        test_mae: data.test_metrics[m].mae,
        test_rmse: data.test_metrics[m].rmse,
        test_mape: data.test_metrics[m].mape,
        rec_mae: data.test_metrics_recursive?.[m]?.mae,
      }))
    : [];
  const naive = data?.test_metrics?.Naive?.mae;
  const sel = data ? data.test_metrics[data.selected_model] : null;

  return (
    <>
      <PageHeader title="Demand Forecast"
        description="Weekly units sold, forecast with six models under a strict time-ordered train / validation / test split. The model is selected on validation MAE; test metrics are reported for every model so the choice can be checked." />
      <div className="flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <Select label="Series" value={series} onChange={(v) => { setSeries(v); setModel(""); }} options={data?.available_series ?? ["All regions"]} />
        {data && <Select label="Model shown in chart" value={shown} onChange={setModel} options={Object.keys(data.test_metrics)} />}
      </div>
      <div className="mt-4"><Status loading={loading} error={error} what="forecast data" onRetry={reload} rows={6} /></div>
      {data && sel && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi label="Selected model (validation MAE)" value={data.selected_model} />
            <Kpi label="Test MAE (selected)" value={`${fmtNumber(sel.mae)} units`} note={`Naive baseline: ${fmtNumber(naive)}`} />
            <Kpi label="Test MAPE (selected)" value={fmtPct(sel.mape)} note={sel.mape_excluded_zero_weeks ? `${sel.mape_excluded_zero_weeks} zero weeks excluded` : "no zero-demand weeks in test"} />
            <Kpi label="Lowest test MAE" value={data.lowest_test_mae_model} note="for reference; not used for selection" />
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            <Kpi label="Training" value={`${data.periods.train.weeks} weeks`} note={`${data.periods.train.start} → ${data.periods.train.end}`} />
            <Kpi label="Validation" value={`${data.periods.validation.weeks} weeks`} note={`${data.periods.validation.start} → ${data.periods.validation.end}`} />
            <Kpi label="Test" value={`${data.periods.test.weeks} weeks`} note={`${data.periods.test.start} → ${data.periods.test.end}`} />
            <Kpi label="Forecast horizon" value={`${data.horizon_weeks} weeks`} note="recursive, beyond the data" />
          </div>

          <Card title={`Actual vs predicted weekly units — ${series}`} subtitle="Shaded: validation (light) and test (darker). Predictions are one-step-ahead. Dashed line: future forecast with approximate band." className="mt-4">
            <ResponsiveContainer width="100%" height={340}>
              <ComposedChart data={chartRows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="week" tick={{ fontSize: 11 }} minTickGap={30} />
                <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => (Array.isArray(v) ? `${fmtNumber(Number(v[0]))} – ${fmtNumber(Number(v[1]))}` : fmtNumber(Number(v)))} />
                <Legend />
                <ReferenceArea x1={data.periods.validation.start} x2={data.periods.validation.end} fill="#f1f5f9" />
                <ReferenceArea x1={data.periods.test.start} x2={data.periods.test.end} fill="#e2e8f0" />
                <Area dataKey="band" name="Approx. 95% band" fill="#99f6e4" stroke="none" />
                <Line dataKey="actual" name="Actual" stroke={COLORS[1]} dot={false} strokeWidth={2} />
                <Line dataKey="predicted" name={`Predicted (${shown})`} stroke={COLORS[0]} dot={false} strokeWidth={2} connectNulls={false} />
                <Line dataKey="forecast" name="Future forecast" stroke={COLORS[0]} strokeDasharray="5 4" dot />
              </ComposedChart>
            </ResponsiveContainer>
            <Interpretation>
              On the test weeks, {data.selected_model} has MAE {fmtNumber(sel.mae)} units versus {fmtNumber(naive)} for the naive (last week) baseline
              — {naive > sel.mae ? `${fmtPct((100 * (naive - sel.mae)) / naive)} lower error` : `${fmtPct((100 * (sel.mae - naive)) / naive)} higher error`}.
              {data.selected_model !== data.lowest_test_mae_model && ` ${data.lowest_test_mae_model} happened to score best on test, which shows that model rankings on 12 weeks are noisy.`}
            </Interpretation>
          </Card>

          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <Card title="Model comparison" subtitle="Errors in units per week. Lower is better." className="lg:col-span-2">
              <DataTable caption="Model metrics" rows={metricRows} columns={[
                { key: "model", label: "Model", format: (v) => (v === data.selected_model ? <strong>{v} (selected)</strong> : v) },
                { key: "val_mae", label: "Val MAE", align: "right", format: (v) => fmtNumber(v) },
                { key: "test_mae", label: "Test MAE", align: "right", format: (v) => fmtNumber(v) },
                { key: "test_rmse", label: "Test RMSE", align: "right", format: (v) => fmtNumber(v) },
                { key: "test_mape", label: "Test MAPE", align: "right", format: (v) => fmtPct(v) },
                { key: "rec_mae", label: "Test MAE (12-wk recursive)", align: "right", format: (v) => (v == null ? "—" : fmtNumber(v)) },
              ]} />
              <p className="mt-2 text-xs text-slate-500">{data.evaluation_note}</p>
            </Card>
            <Card title="Random Forest feature importance">
              {data.rf_feature_importance && (
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={Object.entries(data.rf_feature_importance).map(([k, v]) => ({ feature: k, importance: v }))} layout="vertical">
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis type="category" dataKey="feature" width={110} tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="importance" fill={COLORS[2]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </div>

          <Card title="Future forecast" subtitle={data.interval_note} className="mt-4">
            <DataTable caption="Future forecast" rows={data.future} columns={[
              { key: "week_start", label: "Week starting" },
              { key: "forecast", label: "Forecast units", align: "right", format: (v) => fmtNumber(v) },
              { key: "lower", label: "Lower", align: "right", format: (v) => fmtNumber(v) },
              { key: "upper", label: "Upper", align: "right", format: (v) => fmtNumber(v) },
            ]} />
          </Card>

          <div className="mt-4">
            <Note tone="warn">
              <strong>Limitations.</strong> Only ~2 years of weekly history (one seasonal repeat), so yearly seasonality is captured only through week-of-year features and lag-52 (seasonal naive).
              Validation and test windows are 12 weeks each, so metric differences between models are small relative to their noise. MAPE is undefined for zero-demand weeks (those are excluded and counted)
              and inflates on low-volume weeks. The test window ends right before the Christmas peak; the future forecast runs into the holiday period where the data shows sharp closures. No external drivers (weather, macro, prices of competitors) are used.
            </Note>
          </div>
        </>
      )}
    </>
  );
}
