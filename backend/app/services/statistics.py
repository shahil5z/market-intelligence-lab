"""Statistics Lab: two-sample t-tests, chi-square test of independence and correlation."""

import numpy as np
from scipy import stats

from app import db

ALPHA = 0.05
BUSINESS_NOTE = (
    "Statistical significance does not necessarily imply business significance: with thousands of "
    "orders, very small differences can be 'significant'. Judge the size of the difference and its CI."
)
CORRELATION_VARIABLES = ["units", "avg_price", "discount_pct", "customers"]


def mean_ci(x: np.ndarray, level: float = 0.95) -> list[float]:
    half = stats.t.ppf(0.5 + level / 2, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))
    return [float(x.mean() - half), float(x.mean() + half)]


def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    pooled = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return float((a.mean() - b.mean()) / pooled) if pooled else 0.0


def size_label(value: float, cuts: tuple[float, float, float]) -> str:
    v = abs(value)
    return "negligible" if v < cuts[0] else "small" if v < cuts[1] else "medium" if v < cuts[2] else "large"


def significance_sentence(p: float) -> str:
    if p < ALPHA:
        return "The observed difference is statistically significant at the 5% level (p < 0.05)."
    return "The observed difference is NOT statistically significant at the 5% level (p >= 0.05)."


def two_sample(metric: str, dimension: str, group_a: str, group_b: str, equal_var: bool) -> dict:
    if metric not in db.ORDER_METRICS or dimension not in db.ORDER_DIMENSIONS:
        raise ValueError("Unknown metric or dimension")
    if group_a == group_b:
        raise ValueError("Choose two different groups")
    a = db.order_metric_by_group(metric, dimension, group_a).to_numpy(float)
    b = db.order_metric_by_group(metric, dimension, group_b).to_numpy(float)
    if len(a) < 2 or len(b) < 2:
        raise ValueError("Each group needs at least 2 orders")
    res = stats.ttest_ind(a, b, equal_var=equal_var)
    ci = res.confidence_interval(0.95)
    d = cohens_d(a, b)
    return {
        "test": "Student t-test (equal variances)" if equal_var else "Welch t-test (unequal variances)",
        "unit": "order (invoice)",
        "metric": metric,
        "dimension": dimension,
        "groups": [
            {
                "name": g,
                "n": len(x),
                "mean": float(x.mean()),
                "median": float(np.median(x)),
                "std": float(x.std(ddof=1)),
                "mean_ci95": mean_ci(x),
            }
            for g, x in ((group_a, a), (group_b, b))
        ],
        "difference": float(a.mean() - b.mean()),
        "difference_ci95": [float(ci.low), float(ci.high)],
        "statistic": float(res.statistic),
        "p_value": float(res.pvalue),
        "df": float(res.df),
        "effect_size": {"name": "Cohen's d", "value": d, "magnitude": size_label(d, (0.2, 0.5, 0.8))},
        "significant_at_5pct": bool(res.pvalue < ALPHA),
        "interpretation": significance_sentence(res.pvalue)
        + f" The effect size (Cohen's d = {d:.2f}) is {size_label(d, (0.2, 0.5, 0.8))}.",
        "business_note": BUSINESS_NOTE,
        "caveat": "Order values are right-skewed; the t-test relies on large samples (CLT). Observational data: no causal claim.",
    }


def chi_square(row_dim: str, col_dim: str) -> dict:
    if row_dim not in db.ORDER_DIMENSIONS or col_dim not in db.ORDER_DIMENSIONS or row_dim == col_dim:
        raise ValueError("Choose two different known dimensions")
    ct = db.crosstab(row_dim, col_dim).pivot(index="row_level", columns="col_level", values="n").fillna(0)
    chi2, p, dof, expected = stats.chi2_contingency(ct.to_numpy())
    n = ct.to_numpy().sum()
    v = float(np.sqrt(chi2 / (n * (min(ct.shape) - 1))))
    return {
        "test": "Chi-square test of independence",
        "unit": "order (invoice)",
        "row_dimension": row_dim,
        "col_dimension": col_dim,
        "table": [{"level": str(i), **{str(c): int(ct.loc[i, c]) for c in ct.columns}} for i in ct.index],
        "columns": [str(c) for c in ct.columns],
        "n": int(n),
        "statistic": float(chi2),
        "df": int(dof),
        "p_value": float(p),
        "min_expected_count": float(expected.min()),
        "effect_size": {"name": "Cramer's V", "value": v, "magnitude": size_label(v, (0.1, 0.3, 0.5))},
        "significant_at_5pct": bool(p < ALPHA),
        "interpretation": (
            "The association between the two variables is statistically significant at the 5% level."
            if p < ALPHA
            else "No statistically significant association at the 5% level."
        )
        + f" Cramer's V = {v:.3f} ({size_label(v, (0.1, 0.3, 0.5))}).",
        "business_note": BUSINESS_NOTE,
        "caveat": "Expected counts below 5 make the chi-square approximation unreliable." if expected.min() < 5 else None,
    }


def correlation(x: str, y: str, method: str) -> dict:
    if x not in CORRELATION_VARIABLES or y not in CORRELATION_VARIABLES or x == y:
        raise ValueError(f"x and y must be two different variables from {CORRELATION_VARIABLES}")
    pw = db.product_weeks(db.Filters())
    a, b = pw[x].to_numpy(float), pw[y].to_numpy(float)
    if method == "pearson":
        r, p = stats.pearsonr(a, b)
    elif method == "spearman":
        r, p = stats.spearmanr(a, b)
    else:
        raise ValueError("method must be 'pearson' or 'spearman'")
    z, se = np.arctanh(r), 1 / np.sqrt(len(a) - 3)  # Fisher z interval
    ci = [float(np.tanh(z - 1.96 * se)), float(np.tanh(z + 1.96 * se))]
    rng = np.random.default_rng(0)
    idx = rng.choice(len(a), size=min(600, len(a)), replace=False)
    return {
        "test": f"{method.title()} correlation",
        "unit": "product-week",
        "x": x,
        "y": y,
        "n": len(a),
        "r": float(r),
        "r_ci95": ci,
        "p_value": float(p),
        "r_squared": float(r * r),
        "effect_size": {"name": "|r|", "value": float(abs(r)), "magnitude": size_label(r, (0.1, 0.3, 0.5))},
        "significant_at_5pct": bool(p < ALPHA),
        "interpretation": (
            f"The correlation is statistically significant at the 5% level (r = {r:.3f})."
            if p < ALPHA
            else f"The correlation is not statistically significant at the 5% level (r = {r:.3f})."
        )
        + " Correlation does not imply causation.",
        "business_note": BUSINESS_NOTE,
        "sample_points": [{"x": round(float(a[i]), 3), "y": round(float(b[i]), 3)} for i in idx],
        "caveat": "Fisher-z CI is exact for Pearson and approximate for Spearman.",
    }


def options() -> dict:
    return {
        "metrics": list(db.ORDER_METRICS),
        "correlation_variables": CORRELATION_VARIABLES,
        "dimensions": {d: db.order_dimension_levels(d) for d in db.ORDER_DIMENSIONS},
    }
