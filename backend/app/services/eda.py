"""Exploratory analysis: seasonality, weekday pattern, correlations, price/discount vs demand."""

import numpy as np
from scipy import stats

from app import db
from app.db import Filters

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def seasonality(f: Filters) -> dict:
    df = db.month_of_year(f)
    lo, hi = db.date_bounds()
    # Only full calendar months are comparable: 2010 and 2011 Jan-Nov.
    full = df[(df.year == 2010) | ((df.year == 2011) & (df.month <= 11))]
    rows = []
    for m in range(1, 13):
        row = {"month": MONTHS[m - 1]}
        for y in (2010, 2011):
            v = full[(full.year == y) & (full.month == m)].revenue
            row[str(y)] = round(float(v.iat[0]), 2) if len(v) else None
        rows.append(row)
    y2010 = full[full.year == 2010].set_index("month").revenue
    peak = int(y2010.idxmax()) if len(y2010) else None
    share_q4 = round(100 * y2010[y2010.index >= 10].sum() / y2010.sum(), 1) if len(y2010) else None
    return {
        "rows": rows,
        "peak_month_2010": MONTHS[peak - 1] if peak else None,
        "q4_share_2010_pct": share_q4,
        "note": "Dec 2009 and Dec 2011 are excluded from this chart because they are partial months in the dataset.",
    }


def weekday(f: Filters) -> dict:
    df = db.weekday_profile(f)
    df["revenue_per_trading_day"] = df.revenue / df.trading_days
    rows = df[["weekday", "trading_days", "revenue_per_trading_day", "orders"]].round(2).to_dict(orient="records")
    missing = sorted(set(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]) - set(df.weekday))
    best = df.sort_values("revenue_per_trading_day").iloc[-1]
    return {"rows": rows, "days_without_sales": missing, "best_weekday": best.weekday}


def correlations(f: Filters) -> dict:
    pw = db.product_weeks(f)
    cols = ["units", "avg_price", "discount_pct", "customers", "is_pre_christmas"]
    pw = pw[cols].astype(float)
    corr = pw.corr(method="spearman").round(3)
    rho, p = stats.spearmanr(pw.avg_price, pw.units)
    # Price vs demand: average weekly units per product in price deciles.
    pw["price_bin"] = np.ceil(pw.avg_price.rank(pct=True) * 10).clip(1, 10).astype(int)
    bins = (
        pw.groupby("price_bin")
        .agg(median_price=("avg_price", "median"), mean_units=("units", "mean"), median_units=("units", "median"), n=("units", "size"))
        .reset_index()
        .round(2)
    )
    return {
        "unit": "product-week (one row per product per ISO week)",
        "n": len(pw),
        "method": "Spearman rank correlation",
        "matrix": [{"variable": i, **{c: float(corr.loc[i, c]) for c in cols}} for i in cols],
        "price_vs_units_spearman": round(float(rho), 3),
        "price_vs_units_p_value": float(p),
        "price_deciles": bins.to_dict(orient="records"),
    }


def discount(f: Filters) -> dict:
    df = db.discount_bands(f).round(3)
    return {
        "definition": "discount_pct = max(0, 1 - unit_price / product median price). Derived from real prices; "
        "the dataset has no explicit discount field.",
        "rows": df.drop(columns="sort_key").to_dict(orient="records"),
    }


def campaign_periods(f: Filters) -> dict:
    s = db.campaign_share(f)
    share = 100 * s["campaign_revenue"] / s["total_revenue"] if s["total_revenue"] else 0
    return {
        "campaign_revenue": round(float(s["campaign_revenue"] or 0), 2),
        "campaign_share_pct": round(float(share), 2),
        "note": "Campaigns are synthetic; this is the share of real revenue that falls inside a synthetic campaign's target segment and window.",
    }


def eda(f: Filters) -> dict:
    return {
        "seasonality": seasonality(f),
        "weekday": weekday(f),
        "correlations": correlations(f),
        "discount": discount(f),
        "campaign_periods": campaign_periods(f),
    }
