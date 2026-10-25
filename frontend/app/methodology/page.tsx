"use client";

import type { ReactNode } from "react";
import { Card, DataTable, PageHeader, Status } from "@/components/ui";
import { type Row, useApi } from "@/lib/api";
import { fmtNumber, fmtPct } from "@/lib/format";

function Section({ n, title, children }: { n: number; title: string; children: ReactNode }) {
  return (
    <Card title={`${n}. ${title}`}>
      <div className="space-y-2 text-sm leading-relaxed text-slate-700">{children}</div>
    </Card>
  );
}

export default function MethodologyPage() {
  const dq = useApi<Row>("/api/data-quality");
  const fc = useApi<Row>("/api/demand/forecast");
  const raw = dq.data?.raw;
  const clean = dq.data?.clean;

  return (
    <>
      <PageHeader title="Methodology"
        description="How the data was sourced, cleaned and analysed, which methods were used and why, how results were evaluated, and what the analysis cannot tell you. Numbers on this page are read from the pipeline outputs." />
      <Status loading={dq.loading} error={dq.error} what="the data quality report" onRetry={dq.reload} rows={4} />
      <div className="space-y-4">
        <Section n={1} title="Data sources">
          <p><strong>Public:</strong> UCI Machine Learning Repository, <em>Online Retail II</em> (Chen, 2012; dataset id 502), licensed <a className="underline" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Source: <a className="underline" href="https://archive.ics.uci.edu/dataset/502/online+retail+ii">archive.ics.uci.edu/dataset/502/online+retail+ii</a>. The data was cleaned and aggregated for this project. All transactions of a UK-based, registered non-store online retailer of all-occasion gift-ware, 01/12/2009 – 09/12/2011. Many customers are wholesalers. Columns: Invoice, StockCode, Description, Quantity, InvoiceDate, Price (GBP), Customer ID, Country.</p>
          <p><strong>Derived from public data:</strong> product category (keyword rules on the description), region group (geographic grouping of country), product base price (median observed price), discount_pct (price below the product median), customer first purchase and home country.</p>
          <p><strong>Synthetic (seeded, seed = 42):</strong> 12 campaigns (dates, channel, type, budget, target region group and category), product pack size, region market type. These are invented for demonstration and labelled synthetic in the UI and the data dictionary. <strong>Public calendar:</strong> UK bank holidays transcribed from gov.uk.</p>
          <p>Why this dataset: it has real invoices, dates, customers, products, quantities, prices and countries over two full seasonal cycles, which is what demand forecasting, RFM segmentation and anomaly detection need. It does not contain campaigns or discounts, so those were added synthetically or derived, and documented.</p>
        </Section>
        <Section n={2} title="Data cleaning and validation">
          {raw && clean && (
            <>
              <p>The raw file has {fmtNumber(raw.rows)} rows. Quality checks on raw data: missing cells {fmtPct(raw.missing_cells_pct, 2)} (Customer ID missing on {fmtPct(raw.missing_by_column_pct["Customer ID"], 1)} of rows), exact duplicates {fmtPct(raw.duplicate_rows_pct, 2)}, cancellations {fmtPct(raw.cancellation_rows_pct, 2)}, negative quantities {fmtPct(raw.negative_quantity_pct, 2)}, non-positive prices {fmtPct(raw.impossible_price_pct, 2)}, invalid dates {fmtPct(raw.invalid_dates_pct, 2)}, stock codes with inconsistent descriptions {fmtPct(raw.inconsistent_category_pct, 1)}, quantity outliers {fmtPct(raw.quantity_outlier_pct, 2)} ({raw.quantity_outlier_rule}).</p>
              <DataTable caption="Cleaning steps" rows={dq.data!.cleaning_steps} columns={[
                { key: "rule", label: "Cleaning rule (in order)" },
                { key: "rows_removed", label: "Rows removed", align: "right", format: (v) => fmtNumber(v) },
              ]} />
              <p>Result: {fmtNumber(clean.rows)} sales lines ({fmtPct(clean.rows_removed_pct, 2)} removed), {fmtNumber(clean.customers)} customers, {fmtNumber(clean.products)} products, {clean.countries} countries. Foreign-key checks after loading: {Object.entries(clean.invalid_foreign_keys).map(([k, v]) => `${k} = ${v}`).join(", ")}. Rows without a Customer ID are kept for sales and forecasting but excluded from segmentation.</p>
            </>
          )}
        </Section>
        <Section n={3} title="Feature engineering">
          <p>Calendar features (year, quarter, ISO week, weekday, weekend, UK bank holiday, pre-Christmas flag); line revenue = quantity × unit price; discount_pct; order-level aggregates (order value, units, lines, order-size band); product-week aggregates (units, average price, distinct customers); RFM per customer; weekly lags (1-4, 52), 4-week rolling mean and cyclical week-of-year encoding (sin/cos) for forecasting. Lags only use past values, so no future information leaks into features.</p>
        </Section>
        <Section n={4} title="Exploratory analysis">
          <p>Monthly seasonality comparing 2010 and 2011 (partial months excluded), revenue per trading day by weekday, Spearman correlations at product-week level, price-decile vs weekly units, discount bands vs quantity, regional AOV and the share of revenue inside synthetic campaign windows. Spearman is used because sales variables are heavily skewed.</p>
        </Section>
        <Section n={5} title="Statistical methods">
          <p>Welch’s t-test (default, unequal variances) and Student’s t-test on order-level metrics with 95% CIs for each mean and for the difference; Cohen’s d effect size. Chi-square test of independence on order counts with Cramér’s V. Pearson/Spearman correlation with Fisher-z confidence interval. All at α = 0.05; wording about significance is generated from the p-value. With tens of thousands of orders, small effects become significant, so effect sizes are always shown.</p>
          <p>Campaigns: pre/post comparison (Welch) and difference-in-differences (OLS with treated × post interaction, HC1 robust standard errors) against a control of the same category in other region groups. Because several campaigns are tested at once, p-values are also adjusted with Holm (family-wise error) and Benjamini-Hochberg (false discovery rate).</p>
        </Section>
        <Section n={6} title="Forecasting">
          {fc.data ? (
            <p>Target: weekly units ({fc.data.series}; region groups also available). {fc.data.n_weeks} complete weeks. Train {fc.data.periods.train.start} → {fc.data.periods.train.end} ({fc.data.periods.train.weeks} weeks), validation {fc.data.periods.validation.start} → {fc.data.periods.validation.end} ({fc.data.periods.validation.weeks}), test {fc.data.periods.test.start} → {fc.data.periods.test.end} ({fc.data.periods.test.weeks}). Models: naive (last week), seasonal naive (same week last year), linear regression, random forest, XGBoost, damped-trend exponential smoothing (statsmodels). Models are fitted on train and compared on validation; the model with the lowest validation MAE is selected; all models are then refitted on train + validation and scored on test. Test scores are reported two ways: one-step-ahead (each week predicted from actual earlier weeks) and a recursive 12-week backtest from the end of validation (predictions fed back as lags), which is closer to real forecasting. The future forecast ({fc.data.horizon_weeks} weeks) is recursive with an approximate band from test residuals.</p>
          ) : <Status loading={fc.loading} error={fc.error} what="the forecast setup" onRetry={fc.reload} rows={3} />}
          <p>SARIMA with yearly seasonality and Holt-Winters seasonal models were not used: with about two years of weekly data there is only one seasonal repeat, which is not enough to estimate a 52-week seasonal component reliably.</p>
        </Section>
        <Section n={7} title="Customer segmentation">
          <p>RFM per identified customer (recency in days to the day after the last transaction, number of distinct invoices, total revenue). log1p transform to reduce skew, then standardisation. K-Means for k = 2…8 with silhouette scores; the best k ≥ 3 is used so segments are actionable (the k = 2 result is reported). Ward hierarchical clustering on a sample is compared via adjusted Rand index. PCA is used only for the 2-D plot. Names come from fixed rules on cluster medians relative to overall medians.</p>
        </Section>
        <Section n={8} title="Anomaly detection">
          <p>Weekly revenue per region group and weekly units for the top-10 products. Robust rolling z-score: log1p values, expected = median of the previous 12 weeks, spread = 1.4826 × MAD; flagged when |z| ≥ 3.5 (Iglewicz–Hoaglin) and the series was active. The expected range shown is the IQR fence of the previous 12 weeks. A rolling window only looks backwards, so each decision uses information available at that time.</p>
        </Section>
        <Section n={9} title="Evaluation methodology">
          <p>Forecasts: MAE (main metric, in units), RMSE (penalises large misses), MAPE (only on non-zero weeks; unstable near zero). Segmentation: silhouette, ARI vs Ward. Tests: p-values together with effect sizes and CIs. Backend tests (pytest) recompute key numbers independently (e.g. revenue via SQL, Welch p-value via SciPy, naive MAE from stored predictions) and check that time splits are ordered and disjoint.</p>
        </Section>
        <Section n={10} title="Limitations">
          <ul className="list-disc space-y-1 pl-5">
            <li>Campaigns, pack sizes and market types are synthetic; campaign &quot;uplift&quot; is ordinary variation in real sales, not a marketing effect.</li>
            <li>All analysis is observational: correlation is not causation, and DiD relies on a parallel-trends assumption that is not tested here.</li>
            <li>One retailer, mostly UK, 2009-2011, mostly wholesale customers: results do not generalise to other markets or to today.</li>
            <li>No external variables (weather, prices of competitors, macro data); short history limits seasonal modelling; forecasts would drift and need retraining.</li>
            <li>Product categories come from keyword rules; a sizeable share of revenue stays in &quot;Other&quot; (see Sales EDA by category).</li>
            <li>{clean ? `${fmtPct(clean.missing_customer_id_pct, 1)} of clean lines` : "Some lines"} have no Customer ID, so segmentation covers registered customers only.</li>
            <li>MAPE is undefined for zero-demand weeks and inflated for low-volume series.</li>
          </ul>
        </Section>
        <Section n={11} title="Reproducibility">
          <p>One command rebuilds everything from the public download: <code className="rounded bg-slate-100 px-1">python scripts/run_pipeline.py</code> (ingest → validate/clean/transform → DuckDB → forecasting → segmentation → anomalies → campaigns). All random processes use fixed seeds. Python dependencies are pinned in backend/requirements.txt. The data-quality report in docs/ is regenerated on every run.</p>
        </Section>
      </div>
    </>
  );
}
