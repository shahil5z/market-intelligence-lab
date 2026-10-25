# Data

- `raw/` — downloaded by `scripts/ingest.py` from the UCI Machine Learning Repository: *Online Retail II* (id 502), https://archive.ics.uci.edu/dataset/502/online+retail+ii, licence **CC BY 4.0**. Not committed (≈45 MB).
- `processed/mil.duckdb` — star schema built by `scripts/build_dataset.py` (not committed; rebuild with `python scripts/run_pipeline.py`).
- `processed/*.csv` — small dimension tables (products, regions, campaigns) for inspection.

Synthetic parts (seed 42): campaigns, product pack size, region market type. Everything else is real or derived from real data. See `docs/data_dictionary.md`.
