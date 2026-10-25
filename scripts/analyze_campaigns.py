"""Step 10 - Observational campaign analysis.

IMPORTANT: campaigns are SYNTHETIC (seeded random windows laid over real sales). Any "uplift" is a
property of the real sales in that window, not an effect of a real campaign. The methods are what
this module demonstrates. Nothing here is causal.

For each campaign the target segment = (target region group, target category).
  pre window    = same number of days immediately before the start date
  during window = campaign start..end
Metrics use daily segment revenue on trading days (days on which the shop sold anything).
  observed uplift      = (mean daily revenue during - mean pre) / mean pre
  Welch t-test + 95% CI for the difference in daily means
  difference-in-differences vs a control = same category in all NON-target region groups,
  estimated with OLS revenue ~ treated + post + treated:post (HC1 robust SE)
  naive ROI            = (observed incremental revenue - budget) / budget   (revenue, not profit)
"""

import json

import duckdb
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from common import DB_PATH, MODELS_DIR
from scipy import stats

MIN_ACTIVE_DAYS = 5


def welch_ci(a: np.ndarray, b: np.ndarray, level: float = 0.95) -> tuple[float, float, float, float]:
    """Return (difference, ci_low, ci_high, p_value) for mean(a) - mean(b) using Welch's method."""
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    diff = a.mean() - b.mean()
    se = np.sqrt(va + vb)
    dof = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(b) - 1))
    t = stats.t.ppf(0.5 + level / 2, dof)
    p = stats.ttest_ind(a, b, equal_var=False).pvalue
    return float(diff), float(diff - t * se), float(diff + t * se), float(p)


def daily(con, start, end, groups: list[str], category: str) -> pd.DataFrame:
    placeholders = ",".join("?" * len(groups))
    return con.execute(
        f"""
        WITH days AS (SELECT DISTINCT date FROM sales WHERE date BETWEEN ? AND ?)
        SELECT d.date, COALESCE(SUM(s.revenue), 0) AS revenue
        FROM days d LEFT JOIN (
            SELECT s.date, s.revenue FROM sales s JOIN regions r USING(region_id) JOIN products p USING(product_id)
            WHERE r.region_group IN ({placeholders}) AND p.category = ?) s USING(date)
        GROUP BY d.date ORDER BY d.date""",
        [start, end, *groups, category],
    ).df()


def analyse(con, c: pd.Series, all_groups: list[str]) -> dict:
    start, end = pd.Timestamp(c.start_date), pd.Timestamp(c.end_date)
    length = (end - start).days + 1
    pre_start, pre_end = start - pd.Timedelta(days=length), start - pd.Timedelta(days=1)
    treated = daily(con, pre_start, end, [c.target_region_group], c.target_category)
    control = daily(con, pre_start, end, [g for g in all_groups if g != c.target_region_group], c.target_category)
    for df in (treated, control):
        df["post"] = (df.date >= start).astype(int)
    pre, during = treated[treated.post == 0].revenue.to_numpy(), treated[treated.post == 1].revenue.to_numpy()
    lines = (
        con.execute(
            """SELECT COUNT(*) AS lines, COUNT(DISTINCT invoice_id) AS orders, COALESCE(SUM(quantity),0) AS units,
                           COALESCE(SUM(revenue),0) AS revenue FROM sales WHERE campaign_id = ?""",
            [int(c.campaign_id)],
        )
        .df()
        .iloc[0]
    )
    base = {
        "campaign_id": int(c.campaign_id),
        "campaign_name": c.campaign_name,
        "channel": c.channel,
        "campaign_type": c.campaign_type,
        "start_date": str(start.date()),
        "end_date": str(end.date()),
        "duration_days": length,
        "budget": float(c.budget),
        "target_region_group": c.target_region_group,
        "target_category": c.target_category,
        "pre_period": {"start": str(pre_start.date()), "end": str(pre_end.date())},
        "attributed_lines": int(lines.lines),
        "orders": int(lines.orders),
        "units": int(lines.units),
        "revenue": round(float(lines.revenue), 2),
        "aov": round(float(lines.revenue / lines.orders), 2) if lines.orders else None,
        "trading_days_pre": len(pre),
        "trading_days_during": len(during),
        "active_days_pre": int((pre > 0).sum()),
        "active_days_during": int((during > 0).sum()),
        "daily": [
            {"date": str(d.date()), "treated": round(float(t), 2), "control": round(float(k), 2), "post": int(p)}
            for d, t, k, p in zip(treated.date, treated.revenue, control.revenue, treated.post, strict=False)
        ],
    }
    if min(base["active_days_pre"], base["active_days_during"]) < MIN_ACTIVE_DAYS:
        base.update(
            {
                "sufficient_data": False,
                "note": f"Fewer than {MIN_ACTIVE_DAYS} days with sales in the pre or during window; no statistics computed.",
            }
        )
        return base
    diff, lo, hi, p = welch_ci(during, pre)
    incremental = diff * len(during)
    panel = pd.concat([treated.assign(treated=1), control.assign(treated=0)])
    did = smf.ols("revenue ~ treated + post + treated:post", data=panel).fit(cov_type="HC1")
    did_ci = did.conf_int().loc["treated:post"]
    base.update(
        {
            "sufficient_data": True,
            "pre_mean_daily_revenue": round(float(pre.mean()), 2),
            "during_mean_daily_revenue": round(float(during.mean()), 2),
            "observed_uplift_pct": round(100 * diff / pre.mean(), 1) if pre.mean() > 0 else None,
            "difference_mean_daily": round(diff, 2),
            "difference_ci95": [round(lo, 2), round(hi, 2)],
            "welch_p_value": round(p, 4),
            "observed_incremental_revenue": round(incremental, 2),
            "naive_roi_pct": round(100 * (incremental - c.budget) / c.budget, 1),
            "did_estimate_daily": round(float(did.params["treated:post"]), 2),
            "did_ci95": [round(float(did_ci[0]), 2), round(float(did_ci[1]), 2)],
            "did_p_value": round(float(did.pvalues["treated:post"]), 4),
            "control_definition": f"{c.target_category} in all region groups except {c.target_region_group}",
        }
    )
    return base


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    campaigns = con.execute("SELECT * FROM campaigns ORDER BY campaign_id").df()
    groups = [r[0] for r in con.execute("SELECT DISTINCT region_group FROM regions").fetchall()]
    results = [analyse(con, c, groups) for c in campaigns.itertuples()]
    con.close()
    out = {
        "label": "OBSERVATIONAL analysis of SYNTHETIC campaigns laid over real public sales data. No causal claims.",
        "assumptions": [
            "Campaign windows, budgets, channels and targets are synthetic (seeded); real customers never saw these campaigns.",
            "Pre-period of equal length is used as the baseline; seasonality between the two windows is not removed.",
            "Difference-in-differences assumes parallel trends between the target region group and the control groups.",
            "Daily observations are treated as independent in the t-test, which ignores autocorrelation.",
            "ROI uses revenue, not margin, and treats all observed change as incremental (an upper-bound style simplification).",
        ],
        "campaigns": results,
    }
    (MODELS_DIR / "campaigns.json").write_text(json.dumps(out, indent=2))
    for r in results:
        print(
            f"[campaigns] {r['campaign_name']}: sufficient={r['sufficient_data']} uplift={r.get('observed_uplift_pct')} p={r.get('welch_p_value')} did_p={r.get('did_p_value')}"
        )


if __name__ == "__main__":
    main()
