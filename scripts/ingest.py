"""Step 1 - Ingest: download UCI Online Retail II (CC BY 4.0) and store both sheets as one parquet file."""

import io
import urllib.request
import zipfile

import pandas as pd
from common import RAW_DIR, RAW_PARQUET, RAW_XLSX, SOURCE_URL


def download_if_missing() -> None:
    if RAW_XLSX.exists():
        print(f"[ingest] raw file already present: {RAW_XLSX.name}")
        return
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[ingest] downloading {SOURCE_URL}")
    with urllib.request.urlopen(SOURCE_URL, timeout=120) as resp:
        payload = resp.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as zf:
        zf.extractall(RAW_DIR)


def main() -> None:
    download_if_missing()
    if RAW_PARQUET.exists() and RAW_PARQUET.stat().st_mtime > RAW_XLSX.stat().st_mtime:
        print("[ingest] parquet cache is up to date")
        return
    print("[ingest] reading Excel (two yearly sheets, takes ~40s)")
    sheets = pd.read_excel(RAW_XLSX, sheet_name=None, dtype={"Invoice": str, "StockCode": str})
    df = pd.concat(sheets.values(), ignore_index=True)
    df["Country"] = df["Country"].astype(str)
    df["Description"] = df["Description"].astype("string")
    df.to_parquet(RAW_PARQUET, index=False)
    print(f"[ingest] wrote {len(df):,} raw rows -> {RAW_PARQUET.name}")


if __name__ == "__main__":
    main()
