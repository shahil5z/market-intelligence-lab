"use client";

import Link from "next/link";
import { Card, Note, PageHeader, Status } from "@/components/ui";
import { useApi } from "@/lib/api";

type Finding = { area: string; text: string; source: string };
const PAGE: Record<string, string> = { Regions: "/", Seasonality: "/sales", Pricing: "/sales", Customers: "/segments", Forecasting: "/forecast", Campaigns: "/campaigns", Anomalies: "/anomalies" };

export default function InsightsPage() {
  const { data, loading, error, reload } = useApi<{ findings: Finding[] }>("/api/insights");
  return (
    <>
      <PageHeader title="Business Insights"
        description="Key findings generated automatically from the computed results. Each sentence is a template filled with numbers returned by the analysis endpoints — nothing is written by hand or by a language model." />
      <Status loading={loading} error={error} what="insights" onRetry={reload} rows={6} />
      {data && (
        <Card title="Key findings">
          <ol className="list-decimal space-y-3 pl-5 text-sm text-slate-800">
            {data.findings.map((f) => (
              <li key={f.area}>
                <span className="font-semibold">{f.area}.</span> {f.text}{" "}
                <Link href={PAGE[f.area] ?? "/"} className="text-teal-800 underline underline-offset-2">see analysis</Link>
                <span className="ml-1 text-xs text-slate-500">(source: {f.source})</span>
              </li>
            ))}
          </ol>
        </Card>
      )}
      <div className="mt-4"><Note>These are descriptive and observational findings. Campaign results are based on synthetic campaigns and must not be read as real marketing effects.</Note></div>
    </>
  );
}
