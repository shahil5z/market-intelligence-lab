"""Service-level tests: check analytical outputs against independent calculations."""

import numpy as np
import pytest

from app import db
from app.db import Filters
from app.services import ai_analyst, artifacts_views, overview, statistics


def test_overview_matches_raw_sql():
    ov = overview.overview(Filters())
    direct = db.query("SELECT SUM(revenue) r, COUNT(DISTINCT invoice_id) o FROM sales").iloc[0]
    assert ov["revenue"] == pytest.approx(direct.r, rel=1e-9)
    assert ov["aov"] == pytest.approx(direct.r / direct.o, abs=0.01)


def test_region_shares_sum_to_100():
    rows = overview.sales_by_region(Filters())
    assert sum(r["revenue_share_pct"] for r in rows) == pytest.approx(100, abs=0.1)


def test_filters_reduce_revenue():
    full = overview.overview(Filters())["revenue"]
    part = overview.overview(Filters(region_group="Western Europe"))["revenue"]
    assert 0 < part < full


def test_empty_filter_raises():
    with pytest.raises(ValueError):
        overview.overview(Filters(category="Not a category"))


def test_forecast_splits_are_chronological_and_disjoint():
    fc = artifacts_views.forecast("All regions")
    p = fc["periods"]
    assert p["train"]["end"] < p["validation"]["start"] <= p["validation"]["end"] < p["test"]["start"]
    splits = [h["split"] for h in fc["history"]]
    assert splits == sorted(splits, key=["train", "validation", "test"].index)  # no shuffling


def test_forecast_metrics_recomputable():
    fc = artifacts_views.forecast("All regions")
    test_rows = [h for h in fc["history"] if h["split"] == "test"]
    y = np.array([h["actual"] for h in test_rows])
    p = np.array([h["Naive"] for h in test_rows])
    assert np.mean(np.abs(y - p)) == pytest.approx(fc["test_metrics"]["Naive"]["mae"], rel=1e-3)
    assert fc["selected_model"] == min(fc["validation_metrics"], key=lambda m: fc["validation_metrics"][m]["mae"])


def test_segments_cover_all_customers():
    seg = artifacts_views.segments()
    assert sum(s["customers"] for s in seg["segments"]) == seg["n_customers"]
    assert sum(s["revenue_share_pct"] for s in seg["segments"]) == pytest.approx(100, abs=0.1)


def test_welch_matches_scipy():
    from scipy import stats

    res = statistics.two_sample("order_value", "region_group", "United Kingdom", "Western Europe", equal_var=False)
    a = db.order_metric_by_group("order_value", "region_group", "United Kingdom")
    b = db.order_metric_by_group("order_value", "region_group", "Western Europe")
    assert res["p_value"] == pytest.approx(stats.ttest_ind(a, b, equal_var=False).pvalue, rel=1e-6)
    lo, hi = res["difference_ci95"]
    assert lo <= res["difference"] <= hi


def test_significance_wording_follows_p_value():
    assert "NOT" in statistics.significance_sentence(0.2)
    assert "NOT" not in statistics.significance_sentence(0.01)


def test_chi_square_cramers_v_bounds():
    res = statistics.chi_square("region_group", "order_size_band")
    assert 0 <= res["effect_size"]["value"] <= 1


def test_intent_detection():
    assert ai_analyst.detect_intent("Why did sales decline in Q3?") == "quarter_change"
    assert ai_analyst.detect_intent("Which region had the strongest growth?") == "region_growth"
    assert ai_analyst.detect_intent("What are the highest-value customer segments?") == "segments"
    assert ai_analyst.detect_intent("hello") == "overview"


def test_ai_fallback_without_key():
    out = ai_analyst.analyze("Which region had the strongest growth?")
    assert out["explanation_source"] == "rule_based"
    assert out["result"]["rows"][0]["region_group"] in out["answer"]
