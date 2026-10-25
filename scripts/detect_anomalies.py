"""Step 9 - Anomaly detection on WEEKLY revenue (region groups) and weekly units (top products).

Method (robust rolling z-score): values are log1p-transformed because daily sales are right-skewed.
For each week, expected = median of the PREVIOUS 12 weeks, spread = 1.4826 x MAD of those weeks.
Robust |z| >= 3.5 is flagged (Iglewicz & Hoaglin rule). Weeks whose 12-week median is zero are skipped
(the series is inactive, so "deviation" is meaningless). Severity: |z| >= 6 high, >= 4.5 medium, else low.
"""

import json

import duckdb
import numpy as np
import pandas as pd
from common import DB_PATH, MODELS_DIR

WINDOW = 12  # weeks
Z_THRESHOLD = 3.5
REGION_GROUPS = ["United Kingdom", "Western Europe", "Ireland & Channel Is."]


def flag(series: pd.DataFrame, value_col: str, region: str, product: str, metric: str) -> list[dict]:
    s = series.set_index("date")[value_col].astype(float)
    logs = np.log1p(s)
    prev = logs.shift(1).rolling(WINDOW, min_periods=WINDOW)
    med = prev.median()
    mad = logs.shift(1).rolling(WINDOW, min_periods=WINDOW).apply(lambda w: np.median(np.abs(w - np.median(w))), raw=True)
    z = (logs - med) / (1.4826 * mad.replace(0, np.nan))
    raw_prev = s.shift(1).rolling(WINDOW, min_periods=WINDOW)
    q1, q3, raw_med = raw_prev.quantile(0.25), raw_prev.quantile(0.75), raw_prev.median()
    rows = []
    for d in z[(z.abs() >= Z_THRESHOLD) & (raw_med > 0)].index:
        zz = float(z[d])
        iqr = q3[d] - q1[d]
        rows.append(
            {
                "date": str(d.date()),
                "region": region,
                "product": product,
                "metric": metric,
                "observed": round(float(s[d]), 2),
                "expected": round(float(raw_med[d]), 2),
                "expected_low": round(float(max(q1[d] - 1.5 * iqr, 0)), 2),
                "expected_high": round(float(q3[d] + 1.5 * iqr), 2),
                "deviation_pct": round(100 * (s[d] - raw_med[d]) / raw_med[d], 1),
                "z_score": round(zz, 2),
                "direction": "spike" if zz > 0 else "drop",
                "severity": "high" if abs(zz) >= 6 else "medium" if abs(zz) >= 4.5 else "low",
                "reason": (
                    f"{'Above' if zz > 0 else 'Below'} the previous {WINDOW}-week median "
                    f"({raw_med[d]:,.0f}) by a robust z-score of {abs(zz):.1f}"
                    + (
                        "; week overlaps the Christmas/New Year closure"
                        if (d.month == 12 and d.day >= 19) or (d.month == 1 and d.day <= 3)
                        else ""
                    )
                ),
            }
        )
    return rows


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    region_daily = con.execute("""
        SELECT r.region_group, c.week_start AS date, SUM(s.revenue) AS revenue
        FROM sales s JOIN regions r USING(region_id) JOIN calendar c USING(date) GROUP BY 1, 2 ORDER BY 1, 2""").df()
    top_products = con.execute("""
        SELECT p.product_id, p.product_name FROM sales s JOIN products p USING(product_id)
        GROUP BY 1, 2 ORDER BY SUM(s.quantity) DESC LIMIT 10""").df()
    # Complete weeks only (the final week of the dataset is partial).
    trading_days = con.execute("""SELECT DISTINCT c.week_start AS date FROM sales s JOIN calendar c USING(date)
        WHERE c.week_start + INTERVAL 6 DAY <= (SELECT MAX(date) FROM sales) ORDER BY 1""").df()
    prod_daily = con.execute("""
        SELECT product_id, c.week_start AS date, SUM(quantity) AS units FROM sales JOIN calendar c USING(date)
        WHERE product_id IN (SELECT product_id FROM sales GROUP BY 1 ORDER BY SUM(quantity) DESC LIMIT 10)
        GROUP BY 1, 2""").df()
    con.close()

    anomalies, series_out = [], {}
    total = region_daily.groupby("date", as_index=False)["revenue"].sum()
    total["region_group"] = "All regions"
    region_daily = pd.concat([region_daily[region_daily.region_group.isin(REGION_GROUPS)], total])
    for group, g in region_daily.groupby("region_group"):
        # Reindex to all complete weeks so a week without sales counts as zero.
        g = trading_days.merge(g[["date", "revenue"]], how="left").fillna({"revenue": 0})
        anomalies += flag(g, "revenue", group, "All products", "revenue")
        series_out[group] = [{"date": str(d.date()), "value": round(float(v), 2)} for d, v in zip(g.date, g.revenue, strict=False)]
    for p in top_products.itertuples():
        g = trading_days.merge(prod_daily[prod_daily.product_id == p.product_id][["date", "units"]], how="left").fillna({"units": 0})
        anomalies += flag(g, "units", "All regions", p.product_name, "units")
    anomalies.sort(key=lambda a: -abs(a["z_score"]))
    out = {
        "method": f"Robust rolling z-score on log1p(value): median and 1.4826*MAD of the previous {WINDOW} weeks; flagged when |z| >= {Z_THRESHOLD} and the series was active (median > 0).",
        "expected_range_rule": "Q1 - 1.5*IQR to Q3 + 1.5*IQR of the previous 12 weeks",
        "severity_rule": "high |z|>=6, medium |z|>=4.5, low |z|>=3.5",
        "n_anomalies": len(anomalies),
        "anomalies": anomalies,
        "region_series": series_out,
    }
    (MODELS_DIR / "anomalies.json").write_text(json.dumps(out))
    print(f"[anomalies] {len(anomalies)} flagged points")


if __name__ == "__main__":
    main()
