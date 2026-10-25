"""Executive overview KPIs and the sales breakdowns behind the Overview page."""

from datetime import timedelta

import numpy as np

from app import db
from app.db import Filters

GRAINS = {"day": "day", "week": "week", "month": "month", "quarter": "quarter"}


def _records(df):
    out = df.copy()
    for col in out.columns:
        if str(out[col].dtype).startswith("datetime"):
            out[col] = out[col].dt.strftime("%Y-%m-%d")
    return out.round(2).to_dict(orient="records")


def overview(f: Filters) -> dict:
    lo, hi = db.date_bounds()
    f.start, f.end = f.start or lo, f.end or hi
    k = db.kpis(f)
    if not k["orders"]:
        raise ValueError("No sales match the selected filters")
    # Growth: selected period vs the equally long period immediately before it.
    length = (f.end - f.start).days + 1
    prev_end = f.start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=length - 1)
    growth = None
    if prev_start >= lo:
        prev = db.revenue_between(f, prev_start, prev_end)
        growth = round(100 * (k["revenue"] - prev) / prev, 2) if prev else None
    regions = db.by_region(f)
    cats = db.by_category(f)
    prods = db.top_products(f, 1)
    return {
        "filters": {"start": str(f.start), "end": str(f.end), "region_group": f.region_group, "category": f.category},
        "data_range": {"start": str(lo), "end": str(hi)},
        "revenue": round(float(k["revenue"]), 2),
        "units": int(k["units"]),
        "orders": int(k["orders"]),
        "aov": round(float(k["revenue"] / k["orders"]), 2),
        "customers": int(k["customers"]),
        "products": int(k["products"]),
        "growth_rate_pct": growth,
        "growth_comparison": f"{prev_start} to {prev_end}" if growth is not None else "not available (no earlier data of equal length)",
        "top_region": regions.region_group.iat[0],
        "top_region_share_pct": round(100 * regions.revenue.iat[0] / regions.revenue.sum(), 2),
        "top_category": cats.category.iat[0],
        "top_product": prods.product_name.iat[0],
        "currency": "GBP",
    }


def sales_trend(f: Filters, grain: str) -> list[dict]:
    if grain not in GRAINS:
        raise ValueError(f"grain must be one of {list(GRAINS)}")
    return _records(db.trend(f, GRAINS[grain]))


def sales_by_region(f: Filters) -> list[dict]:
    df = db.by_region(f)
    df["revenue_share_pct"] = 100 * df.revenue / df.revenue.sum()
    df["aov"] = df.revenue / df.orders
    return _records(df)


def sales_by_product(f: Filters, limit: int = 15) -> dict:
    cats = db.by_category(f)
    cats["revenue_share_pct"] = 100 * cats.revenue / cats.revenue.sum()
    return {"categories": _records(cats), "top_products": _records(db.top_products(f, limit))}


def order_value_distribution(f: Filters) -> dict:
    v = db.order_values(f)
    edges = [0, 50, 100, 200, 300, 500, 750, 1000, 2000, 5000, np.inf]
    counts, _ = np.histogram(v, bins=edges)
    labels = [f"{int(a)}-{int(b)}" if np.isfinite(b) else f"{int(a)}+" for a, b in zip(edges[:-1], edges[1:], strict=False)]
    return {
        "bins": [{"bin": lab, "orders": int(c)} for lab, c in zip(labels, counts, strict=False)],
        "mean": round(float(v.mean()), 2),
        "median": round(float(v.median()), 2),
        "p90": round(float(v.quantile(0.9)), 2),
        "skewness": round(float(v.skew()), 2),
    }
