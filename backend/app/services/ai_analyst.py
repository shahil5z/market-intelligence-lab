"""AI Analyst (optional module).

Flow: question -> rule-based intent detection -> analytical tool (pandas/SQL) -> structured JSON
result -> (optional) OpenAI explains ONLY that JSON -> answer + supporting table/chart.
Without OPENAI_API_KEY, or if the call fails, a deterministic template explanation is returned.
"""

import json
import logging
import os
import re
from datetime import date

from app import db
from app.config import OPENAI_MODEL
from app.db import Filters
from app.services import artifacts_views, overview

log = logging.getLogger(__name__)

INTENTS = {
    "quarter_change": ["quarter", "q1", "q2", "q3", "q4", "decline", "drop", "fell", "decrease"],
    "region_growth": ["region", "country", "growth", "grew", "growing", "market"],
    "segments": ["segment", "customer", "rfm", "loyal", "value", "churn"],
    "forecast": ["forecast", "predict", "next week", "future", "demand", "model"],
    "campaigns": ["campaign", "uplift", "roi", "promotion", "marketing"],
    "anomalies": ["anomal", "unusual", "spike", "outlier", "strange"],
    "top_products": ["product", "category", "best seller", "best-selling", "top selling", "item"],
}


def detect_intent(question: str) -> str:
    q = question.lower()
    scores = {k: sum(w in q for w in words) for k, words in INTENTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "overview"


def _quarter_change(question: str) -> dict:
    m = re.search(r"q([1-4])", question.lower())
    quarter = int(m.group(1)) if m else 3
    year = 2011 if quarter <= 3 else 2010  # latest complete instance of that quarter in the data
    prev_q, prev_y = (quarter - 1, year) if quarter > 1 else (4, year - 1)
    df = db.quarterly_revenue_by_region()
    cur = df[(df.year == year) & (df.quarter == quarter)].set_index("region_group").revenue
    prev = df[(df.year == prev_y) & (df.quarter == prev_q)].set_index("region_group").revenue
    rows = [
        {
            "region_group": r,
            f"Q{prev_q} {prev_y}": round(float(prev.get(r, 0)), 2),
            f"Q{quarter} {year}": round(float(cur.get(r, 0)), 2),
            "change_pct": round(100 * (cur.get(r, 0) - prev.get(r, 0)) / prev.get(r, 1), 1),
        }
        for r in cur.index
    ]
    total_prev, total_cur = float(prev.sum()), float(cur.sum())
    return {
        "tool": "quarter_over_quarter_revenue",
        "quarter": f"Q{quarter} {year}",
        "previous": f"Q{prev_q} {prev_y}",
        "total_previous": round(total_prev, 2),
        "total_current": round(total_cur, 2),
        "total_change_pct": round(100 * (total_cur - total_prev) / total_prev, 1),
        "rows": rows,
        "chart": {"type": "bar", "x": "region_group", "y": ["change_pct"]},
    }


def _region_growth(_: str) -> dict:
    # Like-for-like: 1 Jan - 9 Dec of 2011 vs the same dates in 2010.
    cur = db.by_region(Filters(date(2011, 1, 1), date(2011, 12, 9))).set_index("region_group").revenue
    prev = db.by_region(Filters(date(2010, 1, 1), date(2010, 12, 9))).set_index("region_group").revenue
    rows = sorted(
        [
            {
                "region_group": r,
                "revenue_2010": round(float(prev.get(r, 0)), 2),
                "revenue_2011": round(float(cur[r]), 2),
                "growth_pct": round(100 * (cur[r] - prev[r]) / prev[r], 1) if prev.get(r, 0) > 0 else None,
            }
            for r in cur.index
        ],
        key=lambda r: -(r["growth_pct"] if r["growth_pct"] is not None else -1e9),
    )
    return {
        "tool": "region_growth_like_for_like",
        "period": "1 Jan-9 Dec 2011 vs 1 Jan-9 Dec 2010",
        "rows": rows,
        "strongest_growth": rows[0]["region_group"],
        "chart": {"type": "bar", "x": "region_group", "y": ["growth_pct"]},
    }


def _segments(_: str) -> dict:
    seg = artifacts_views.segments()
    keys = ["name", "customers", "revenue_share_pct", "avg_spend", "avg_frequency", "avg_recency_days"]
    return {
        "tool": "rfm_segments",
        "k": seg["chosen_k"],
        "rows": [{k: s[k] for k in keys} for s in seg["segments"]],
        "chart": {"type": "bar", "x": "name", "y": ["revenue_share_pct"]},
    }


def _forecast(_: str) -> dict:
    fc = artifacts_views.forecast("All regions")
    rows = [
        {
            "model": m,
            "test_mae": round(v["mae"], 1),
            "test_rmse": round(v["rmse"], 1),
            "test_mape": round(v["mape"], 1) if v["mape"] else None,
        }
        for m, v in fc["test_metrics"].items()
    ]
    return {
        "tool": "forecast_summary",
        "selected_model": fc["selected_model"],
        "test_period": fc["periods"]["test"],
        "future": fc["future"],
        "rows": rows,
        "chart": {"type": "bar", "x": "model", "y": ["test_mae"]},
    }


def _campaigns(_: str) -> dict:
    keys = ["campaign_name", "target_region_group", "target_category", "observed_uplift_pct", "welch_p_value", "naive_roi_pct"]
    rows = [{k: c.get(k) for k in keys} for c in artifacts_views.campaigns()["campaigns"] if c.get("sufficient_data")]
    return {
        "tool": "campaign_summary",
        "label": "observational, synthetic campaigns",
        "rows": rows,
        "chart": {"type": "bar", "x": "campaign_name", "y": ["observed_uplift_pct"]},
    }


def _anomalies(_: str) -> dict:
    an = artifacts_views.anomalies(None, None, None, 8)
    keys = ["date", "region", "product", "observed", "expected", "z_score", "direction", "severity"]
    return {
        "tool": "anomaly_summary",
        "total_flagged": an["total_flagged"],
        "rows": [{k: a[k] for k in keys} for a in an["anomalies"]],
        "chart": None,
    }


def _top_products(_: str) -> dict:
    data = overview.sales_by_product(Filters(), 10)
    rows = [{k: p[k] for k in ["product_name", "category", "revenue", "units"]} for p in data["top_products"]]
    return {"tool": "top_products", "rows": rows, "chart": {"type": "bar", "x": "product_name", "y": ["revenue"]}}


def _overview(_: str) -> dict:
    ov = overview.overview(Filters())
    keys = ["revenue", "units", "orders", "aov", "customers", "products", "top_region", "top_category"]
    return {"tool": "overview_kpis", "rows": [{"metric": k, "value": ov[k]} for k in keys], "chart": None}


TOOLS = {
    "quarter_change": _quarter_change,
    "region_growth": _region_growth,
    "segments": _segments,
    "forecast": _forecast,
    "campaigns": _campaigns,
    "anomalies": _anomalies,
    "top_products": _top_products,
    "overview": _overview,
}


def template_explanation(intent: str, r: dict) -> str:
    if intent == "quarter_change":
        worst = min(r["rows"], key=lambda x: x["change_pct"])
        return (
            f"Total revenue went from {r['total_previous']:,.0f} in {r['previous']} to {r['total_current']:,.0f} in {r['quarter']} "
            f"({r['total_change_pct']:+.1f}%). The weakest region group was {worst['region_group']} ({worst['change_pct']:+.1f}%). "
            "These figures describe what changed, not why; the data has no causal drivers."
        )
    if intent == "region_growth":
        top = r["rows"][0]
        return f"Like-for-like ({r['period']}), {top['region_group']} grew the most: {top['growth_pct']:+.1f}%."
    if intent == "segments":
        s = r["rows"][0]
        return (
            f"'{s['name']}' is the highest-value segment with {s['revenue_share_pct']:.1f}% of revenue from {s['customers']:,} customers."
        )
    if intent == "forecast":
        return f"{r['selected_model']} was selected on validation MAE; next-week forecast: {r['future'][0]['forecast']:,.0f} units."
    if intent == "campaigns":
        best = max(r["rows"], key=lambda x: x["observed_uplift_pct"]) if r["rows"] else None
        return (
            (
                f"{best['campaign_name']} has the highest observed uplift ({best['observed_uplift_pct']:+.1f}%, p = {best['welch_p_value']:.3f}). "
                "Campaigns are synthetic and the analysis is observational."
            )
            if best
            else "No campaign has enough data."
        )
    if intent == "anomalies":
        return f"{r['total_flagged']} weekly anomalies were flagged; the table shows the strongest by robust z-score."
    if intent == "top_products":
        p = r["rows"][0]
        return f"The top product by revenue is {p['product_name']} ({p['category']}) with {p['revenue']:,.0f} revenue."
    return "Here are the headline KPIs computed from the cleaned dataset."


def llm_explanation(question: str, intent: str, result: dict) -> tuple[str | None, str]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None, "OPENAI_API_KEY not set - showing the rule-based explanation."
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key, timeout=30)
        payload = {k: v for k, v in result.items() if k != "chart"}
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": "You explain data-analysis results for a student portfolio project. Use ONLY numbers present "
                    "in the JSON. Never invent figures or causes. If the question asks 'why', say the data shows what changed but not why. "
                    "Answer in 3-5 sentences, plain English. Currency is GBP. Campaign data is synthetic and observational.",
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\nTool used: {intent}\nResult JSON:\n{json.dumps(payload, default=str)[:6000]}",
                },
            ],
        )
        return resp.choices[0].message.content.strip(), f"Explained by OpenAI model {OPENAI_MODEL} from the JSON result above."
    except Exception as exc:  # network/auth/model errors -> fallback, never crash the endpoint
        log.warning("OpenAI call failed: %s", type(exc).__name__)
        return None, f"OpenAI call failed ({type(exc).__name__}) - showing the rule-based explanation."


def analyze(question: str, use_llm: bool = True) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("Question must not be empty")
    intent = detect_intent(question)
    result = TOOLS[intent](question)
    fallback = template_explanation(intent, result)
    answer, status = llm_explanation(question, intent, result) if use_llm else (None, "LLM disabled for this request.")
    return {
        "question": question,
        "intent": intent,
        "tool": result["tool"],
        "result": result,
        "answer": answer or fallback,
        "explanation_source": "openai" if answer else "rule_based",
        "status": status,
    }
