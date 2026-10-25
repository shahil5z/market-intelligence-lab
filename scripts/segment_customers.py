"""Step 8 - RFM customer segmentation with K-Means (k chosen by silhouette) and a Ward check."""

import json

import duckdb
import joblib
import numpy as np
import pandas as pd
from common import DB_PATH, MODELS_DIR, SEED
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

K_RANGE = range(2, 9)


def load_rfm(con) -> pd.DataFrame:
    return con.execute("""
        WITH snap AS (SELECT MAX(date) + INTERVAL 1 DAY AS d FROM sales)
        SELECT customer_id,
               DATE_DIFF('day', MAX(date), (SELECT d FROM snap)) AS recency_days,
               COUNT(DISTINCT invoice_id) AS frequency,
               SUM(revenue) AS monetary
        FROM sales WHERE customer_id IS NOT NULL GROUP BY customer_id""").df()


def name_segment(c: pd.Series, med: pd.Series) -> str:
    """Rule-based names from centroid behaviour relative to the customer medians."""
    recent = c.recency_days <= med.recency_days
    frequent = c.frequency >= 2 * med.frequency
    big = c.monetary >= 2 * med.monetary
    if recent and frequent and big:
        return "High Value"
    if recent and c.frequency >= med.frequency:
        return "Loyal / Regular"
    if recent:
        return "New / Recent Low Frequency"
    if c.frequency >= med.frequency:
        return "At Risk (Lapsed Regulars)"
    return "Low Engagement / Lapsed"


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    rfm = load_rfm(con)
    con.close()
    # Frequency and monetary are heavily right-skewed -> log1p before scaling.
    X = np.column_stack([np.log1p(rfm.recency_days), np.log1p(rfm.frequency), np.log1p(rfm.monetary)])
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)

    scores = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=SEED).fit(Xs)
        scores.append(
            {
                "k": k,
                "silhouette": float(silhouette_score(Xs, km.labels_, sample_size=4000, random_state=SEED)),
                "inertia": float(km.inertia_),
            }
        )
    best_k = max(scores, key=lambda s: s["silhouette"])["k"]
    # A 2-cluster split is often "best" by silhouette but too coarse for marketing use; we report
    # it and use the best k >= 3 so segments are actionable (decision documented in methodology).
    chosen_k = max((s for s in scores if s["k"] >= 3), key=lambda s: s["silhouette"])["k"]
    km = KMeans(n_clusters=chosen_k, n_init=10, random_state=SEED).fit(Xs)
    rfm["cluster"] = km.labels_

    # Ward hierarchical clustering on a sample, compared to K-Means via adjusted Rand index.
    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(Xs), size=min(3000, len(Xs)), replace=False)
    ward = AgglomerativeClustering(n_clusters=chosen_k, linkage="ward").fit(Xs[idx])
    ari = float(adjusted_rand_score(km.labels_[idx], ward.labels_))

    med = rfm[["recency_days", "frequency", "monetary"]].median()
    total_rev = rfm.monetary.sum()
    segments = []
    for cl, g in rfm.groupby("cluster"):
        centre = g[["recency_days", "frequency", "monetary"]].median()
        segments.append(
            {
                "cluster": int(cl),
                "name": name_segment(centre, med),
                "customers": len(g),
                "customer_share_pct": round(100 * len(g) / len(rfm), 2),
                "revenue": round(float(g.monetary.sum()), 2),
                "revenue_share_pct": round(100 * g.monetary.sum() / total_rev, 2),
                "avg_spend": round(float(g.monetary.mean()), 2),
                "median_spend": round(float(centre.monetary), 2),
                "avg_frequency": round(float(g.frequency.mean()), 2),
                "avg_recency_days": round(float(g.recency_days.mean()), 1),
            }
        )
    # Disambiguate duplicate names by revenue rank.
    seen = {}
    for s in sorted(segments, key=lambda s: -s["revenue"]):
        seen[s["name"]] = seen.get(s["name"], 0) + 1
        if seen[s["name"]] > 1:
            s["name"] = f"{s['name']} ({seen[s['name']]})"
    pca = PCA(n_components=2, random_state=SEED).fit(Xs)
    pts = pca.transform(Xs[idx[:1500]])
    names = {s["cluster"]: s["name"] for s in segments}
    points = [
        {"pc1": round(float(a), 3), "pc2": round(float(b), 3), "segment": names[int(c)]}
        for (a, b), c in zip(pts, km.labels_[idx[:1500]], strict=False)
    ]
    out = {
        "n_customers": len(rfm),
        "features": ["log1p(recency_days)", "log1p(frequency)", "log1p(monetary)"],
        "silhouette_by_k": scores,
        "best_k_silhouette": best_k,
        "chosen_k": chosen_k,
        "ward_adjusted_rand_index": round(ari, 3),
        "pca_explained_variance_pct": [round(100 * v, 1) for v in pca.explained_variance_ratio_],
        "medians": {k: round(float(v), 2) for k, v in med.items()},
        "naming_rules": "High Value: median recency <= overall median AND frequency and spend >= 2x median; "
        "Loyal / Regular: recent and frequency >= median; New / Recent Low Frequency: recent only; "
        "At Risk: not recent but frequency >= median; Low Engagement: neither.",
        "segments": sorted(segments, key=lambda s: -s["revenue"]),
        "pca_points": points,
    }
    (MODELS_DIR / "segments.json").write_text(json.dumps(out, indent=2))
    joblib.dump({"scaler": scaler, "kmeans": km}, MODELS_DIR / "segmentation_kmeans.joblib")
    print(f"[segments] best k by silhouette={best_k}, chosen k={chosen_k}, ARI vs Ward={ari:.3f}")
    for s in out["segments"]:
        print("   ", s["name"], s["customers"], s["revenue_share_pct"])


if __name__ == "__main__":
    main()
