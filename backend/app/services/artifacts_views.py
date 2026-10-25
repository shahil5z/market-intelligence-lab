"""Thin readers over the pipeline artifacts (forecasts, segments, anomalies, campaigns, data quality)."""

from app.utils.artifacts import load


def forecast(series: str) -> dict:
    data = load("forecast_results")
    if series not in data:
        raise KeyError(f"Unknown series '{series}'. Options: {list(data)}")
    out = dict(data[series])
    out["available_series"] = list(data)
    return out


def segments() -> dict:
    return load("segments")


def anomalies(region: str | None, metric: str | None, severity: str | None, limit: int) -> dict:
    data = load("anomalies")
    rows = data["anomalies"]
    if region:
        rows = [r for r in rows if r["region"] == region]
    if metric:
        rows = [r for r in rows if r["metric"] == metric]
    if severity:
        rows = [r for r in rows if r["severity"] == severity]
    series_name = region if region in data["region_series"] else "All regions"
    return {
        "method": data["method"],
        "expected_range_rule": data["expected_range_rule"],
        "severity_rule": data["severity_rule"],
        "total_flagged": data["n_anomalies"],
        "n_matching": len(rows),
        "anomalies": rows[:limit],
        "series_name": series_name,
        "series": data["region_series"][series_name],
        "series_anomalies": [r for r in data["anomalies"] if r["region"] == series_name and r["metric"] == "revenue"],
        "regions": sorted({r["region"] for r in data["anomalies"]}),
    }


def campaigns() -> dict:
    data = load("campaigns")
    rows = [{k: v for k, v in c.items() if k != "daily"} for c in data["campaigns"]]
    return {"label": data["label"], "assumptions": data["assumptions"], "campaigns": rows}


def campaign(campaign_id: int) -> dict:
    data = load("campaigns")
    for c in data["campaigns"]:
        if c["campaign_id"] == campaign_id:
            return {**c, "label": data["label"], "assumptions": data["assumptions"]}
    raise KeyError(f"Campaign {campaign_id} not found")


def data_quality() -> dict:
    return load("data_quality")
