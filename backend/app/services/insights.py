"""Business insights: every sentence is a template filled from computed results."""

from app.db import Filters
from app.services import artifacts_views, eda, overview


def _fmt(v: float) -> str:
    return f"{v:,.0f}"


def key_findings() -> list[dict]:
    out = []
    ov = overview.overview(Filters())
    out.append(
        {
            "area": "Regions",
            "text": f"{ov['top_region']} contributes {ov['top_region_share_pct']:.1f}% of revenue "
            f"({ov['currency']} {_fmt(ov['revenue'])} in total between {ov['data_range']['start']} and {ov['data_range']['end']}).",
            "source": "/api/overview",
        }
    )
    season = eda.seasonality(Filters())
    out.append(
        {
            "area": "Seasonality",
            "text": ("Demand is strongly seasonal: " if season["q4_share_2010_pct"] > 35 else "Seasonality: ")
            + f"in 2010 revenue peaked in {season['peak_month_2010']}, "
            f"and October-December produced {season['q4_share_2010_pct']}% of the year's revenue.",
            "source": "/api/sales/eda",
        }
    )
    seg = artifacts_views.segments()
    top = seg["segments"][0]
    out.append(
        {
            "area": "Customers",
            "text": f"The '{top['name']}' segment is {top['customer_share_pct']:.1f}% of identified customers "
            f"but {top['revenue_share_pct']:.1f}% of their revenue (K-Means, k = {seg['chosen_k']}).",
            "source": "/api/customers/segments",
        }
    )
    fc = artifacts_views.forecast("All regions")
    sel, best = fc["selected_model"], fc["lowest_test_mae_model"]
    naive = fc["test_metrics"]["Naive"]["mae"]
    sel_mae = fc["test_metrics"][sel]["mae"]
    change = 100 * (naive - sel_mae) / naive
    out.append(
        {
            "area": "Forecasting",
            "text": f"For total weekly units, {sel} was selected on validation MAE; on the 12-week test set it has "
            f"MAE {_fmt(sel_mae)} vs {_fmt(naive)} for the naive baseline ({change:+.1f}% {'lower' if change > 0 else 'higher'} error). "
            f"Lowest test MAE: {best}.",
            "source": "/api/demand/forecast",
        }
    )
    camps = [c for c in artifacts_views.campaigns()["campaigns"] if c.get("sufficient_data")]
    if camps:
        c = max(camps, key=lambda c: c["observed_uplift_pct"] or -1e9)
        sig = "statistically significant" if c["welch_p_value"] < 0.05 else "not statistically significant"
        out.append(
            {
                "area": "Campaigns",
                "text": f"{c['campaign_name']} shows the strongest observed uplift ({c['observed_uplift_pct']:+.1f}% "
                f"daily revenue vs its pre-period), which is {sig} (Welch p = {c['welch_p_value']:.3f}). Campaigns are synthetic and "
                "the analysis is observational.",
                "source": "/api/campaigns",
            }
        )
    an = artifacts_views.anomalies(None, None, "high", 5)
    if an["anomalies"]:
        a = an["anomalies"][0]
        out.append(
            {
                "area": "Anomalies",
                "text": f"{an['n_matching']} high-severity anomalies were flagged; the strongest is a {a['direction']} "
                f"on the week of {a['date']} ({a['product']}, {a['region']}): observed {_fmt(a['observed'])} vs expected {_fmt(a['expected'])}.",
                "source": "/api/anomalies",
            }
        )
    corr = eda.correlations(Filters())
    out.append(
        {
            "area": "Pricing",
            "text": f"Across product-weeks, average price and units sold have a Spearman correlation of "
            f"{corr['price_vs_units_spearman']:.2f}: "
            + (
                "cheaper items tend to sell in larger quantities"
                if corr["price_vs_units_spearman"] < 0
                else "higher prices go with higher quantities"
            )
            + " (association, not causation).",
            "source": "/api/sales/eda",
        }
    )
    return out
