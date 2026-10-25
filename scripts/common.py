"""Shared paths and constants for the pipeline scripts (all paths are relative to the repo root)."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
DOCS_DIR = ROOT / "docs"
DB_PATH = PROCESSED_DIR / "mil.duckdb"

SOURCE_URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
RAW_XLSX = RAW_DIR / "online_retail_II.xlsx"
RAW_PARQUET = RAW_DIR / "online_retail_ii_raw.parquet"

SEED = 42  # every synthetic dimension is generated from this seed
