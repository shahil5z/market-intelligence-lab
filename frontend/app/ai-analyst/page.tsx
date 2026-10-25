"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, DataTable, Note, PageHeader, Skeleton } from "@/components/ui";
import { friendlyError, type Row, postJson } from "@/lib/api";
import { COLORS, compact } from "@/lib/format";

const EXAMPLES = ["Why did sales decline in Q3?", "Which region had the strongest growth?", "What are the highest-value customer segments?", "Which campaign had the best uplift?", "What does the demand forecast say?"];

export default function AiAnalystPage() {
  const [question, setQuestion] = useState(EXAMPLES[0]);
  const [useLlm, setUseLlm] = useState(true);
  const [res, setRes] = useState<Row | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function ask(q: string) {
    setBusy(true);
    setErr(null);
    try {
      setRes(await postJson<Row>("/api/ai/analyze", { question: q, use_llm: useLlm }));
    } catch (e) {
      setErr(friendlyError(e, "answer this question"));
    } finally {
      setBusy(false);
    }
  }

  const rows: Row[] = res?.result?.rows ?? [];
  const chart = res?.result?.chart;
  const columns = rows.length ? Object.keys(rows[0]).map((k) => ({ key: k, label: k.replaceAll("_", " "), format: (v: unknown) => (typeof v === "number" ? v.toLocaleString("en-GB", { maximumFractionDigits: 2 }) : String(v ?? "n/a")) })) : [];

  return (
    <>
      <PageHeader title="AI Analyst (optional module)"
        description="Ask a question in plain English. A rule-based router picks an analytical tool, Python computes the answer from the data, and only then a language model (if configured) explains that structured result. The model never sees the raw data and is told not to add numbers." />
      <Note>Pipeline: question → intent detection → analytical tool → computed JSON → explanation (OpenAI if OPENAI_API_KEY is set on the server, otherwise a rule-based template). The table below is the ground truth.</Note>
      <form className="mt-4 rounded-lg border border-slate-200 bg-white p-3" onSubmit={(e) => { e.preventDefault(); ask(question); }}>
        <label htmlFor="q" className="text-xs font-medium text-slate-600">Your question</label>
        <div className="mt-1 flex flex-col gap-2 sm:flex-row">
          <input id="q" value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500}
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm" />
          <button type="submit" disabled={busy || question.trim().length < 3} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50">
            {busy ? "Analysing…" : "Ask"}
          </button>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {EXAMPLES.map((q) => (
            <button key={q} type="button" onClick={() => { setQuestion(q); ask(q); }} className="rounded-full border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50">{q}</button>
          ))}
          <label className="ml-auto flex items-center gap-2 text-xs text-slate-600">
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} /> Use OpenAI explanation if available
          </label>
        </div>
      </form>
      {busy && <div className="mt-4"><Skeleton rows={4} label="Working" /></div>}
      {err && <div className="mt-4" role="alert"><Note tone="warn">{err}</Note></div>}
      {res && (
        <div className="mt-4 space-y-4">
          <Card title="Answer" subtitle={`Intent: ${res.intent} · tool: ${res.tool} · explanation: ${res.explanation_source}`}>
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-800">{res.answer}</p>
            <p className="mt-2 text-xs text-slate-500">{res.status}</p>
          </Card>
          {chart && rows.length > 0 && (
            <Card title="Supporting chart">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={rows}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey={chart.x} tick={{ fontSize: 10 }} interval={0} />
                  <YAxis tickFormatter={compact} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  {chart.y.map((k: string, i: number) => <Bar key={k} dataKey={k} fill={COLORS[i]} />)}
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}
          {rows.length > 0 && <Card title="Supporting data (computed by Python)"><DataTable caption="Supporting data" rows={rows} columns={columns} /></Card>}
        </div>
      )}
    </>
  );
}
