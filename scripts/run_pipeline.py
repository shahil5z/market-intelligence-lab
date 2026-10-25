"""Run the whole pipeline end to end: python scripts/run_pipeline.py"""

import time

import analyze_campaigns
import build_dataset
import detect_anomalies
import ingest
import segment_customers
import train_forecast

def pack_database():
    """Write backend/artifacts/mil.duckdb.gz - the copy that is committed and deployed (the API unpacks it)."""
    import gzip
    import shutil

    from common import DB_PATH

    with open(DB_PATH, "rb") as src, gzip.GzipFile(DB_PATH.with_name(DB_PATH.name + ".gz"), "wb", compresslevel=9, mtime=0) as dst:
        shutil.copyfileobj(src, dst)


STEPS = [
    ("1. ingest (download + parquet cache)", ingest.main),
    ("2-5. validate, clean, transform, features -> DuckDB", build_dataset.main),
    ("6. demand forecasting (train + evaluate)", train_forecast.main),
    ("7. customer segmentation", segment_customers.main),
    ("8. anomaly detection", detect_anomalies.main),
    ("9. campaign analysis", analyze_campaigns.main),
    ("10. pack database for the API", pack_database),
]

if __name__ == "__main__":
    t0 = time.time()
    for name, step in STEPS:
        print(f"\n=== {name} ===")
        t = time.time()
        step()
        print(f"    done in {time.time() - t:.1f}s")
    print(f"\nPipeline finished in {time.time() - t0:.1f}s. Artifacts: backend/artifacts/ (DB + JSON), models/ (joblib), docs/data_quality_report.md")
