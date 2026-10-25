"""Steps 2-5 - Validate, clean, transform and feature-engineer.

Reads the raw parquet, computes a data-quality report on the RAW data, applies documented cleaning
rules, joins the seeded synthetic dimensions and writes a star schema into DuckDB
(data/processed/mil.duckdb) plus CSV copies of the small dimension tables.
"""

import json

import duckdb
import numpy as np
import pandas as pd
from common import (
    ARTIFACTS_DIR,
    DB_PATH,
    DOCS_DIR,
    PROCESSED_DIR,
    RAW_PARQUET,
)
from generate_synthetic import (
    UK_BANK_HOLIDAYS,
    assign_category,
    campaign_table,
    pack_sizes,
    region_table,
)

PRODUCT_CODE_PATTERN = r"^\d{5}[A-Za-z]*$"  # real merchandise codes; excludes POST, M, BANK CHARGES...
MAX_LINE_QUANTITY = 10_000  # lines above this are treated as data-entry outliers and removed


def pct(part: float, whole: float) -> float:
    return round(100.0 * part / whole, 3) if whole else 0.0


def quality_report(raw: pd.DataFrame) -> dict:
    n = len(raw)
    qty = raw["Quantity"]
    price = raw["Price"]
    is_cancel = raw["Invoice"].str.startswith("C")
    valid = raw[(~is_cancel) & (qty > 0) & (price > 0)]
    q1, q3 = valid["Quantity"].quantile([0.25, 0.75])
    iqr_hi = q3 + 3 * (q3 - q1)
    descs_per_code = raw.dropna(subset=["Description"]).groupby("StockCode")["Description"].nunique()
    min_date, max_date = pd.Timestamp("2009-12-01"), pd.Timestamp("2011-12-31")
    invalid_dates = raw["InvoiceDate"].isna() | (raw["InvoiceDate"] < min_date) | (raw["InvoiceDate"] > max_date)
    return {
        "stage": "raw",
        "rows": n,
        "columns": raw.shape[1],
        "missing_cells_pct": pct(raw.isna().sum().sum(), raw.size),
        "missing_by_column_pct": {c: pct(raw[c].isna().sum(), n) for c in raw.columns},
        "duplicate_rows_pct": pct(raw.duplicated().sum(), n),
        "invalid_dates_pct": pct(invalid_dates.sum(), n),
        "cancellation_rows_pct": pct(is_cancel.sum(), n),
        "negative_quantity_pct": pct((qty < 0).sum(), n),
        "impossible_price_pct": pct((price <= 0).sum(), n),
        "non_product_code_pct": pct((~raw["StockCode"].str.match(PRODUCT_CODE_PATTERN)).sum(), n),
        "inconsistent_category_pct": pct((descs_per_code > 1).sum(), len(descs_per_code)),
        "inconsistent_category_note": "share of stock codes with more than one description spelling",
        "unspecified_country_pct": pct((raw["Country"] == "Unspecified").sum(), n),
        "quantity_outlier_pct": pct((valid["Quantity"] > iqr_hi).sum(), len(valid)),
        "quantity_outlier_rule": f"quantity > Q3 + 3*IQR = {iqr_hi:.0f} among valid sales lines",
        "extreme_quantity_rows": int((qty.abs() > MAX_LINE_QUANTITY).sum()),
    }


def clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    steps = []
    df = raw.copy()

    def log(name: str, mask: pd.Series) -> None:
        steps.append({"rule": name, "rows_removed": int(mask.sum())})

    rules = [
        ("drop exact duplicate rows", df.duplicated()),
    ]
    for name, mask in rules:
        log(name, mask)
        df = df[~mask]
    for name, func in [
        ("drop cancellations (invoice starts with 'C')", lambda d: d["Invoice"].str.startswith("C")),
        ("drop non-positive quantity", lambda d: d["Quantity"] <= 0),
        ("drop non-positive price", lambda d: d["Price"] <= 0),
        ("drop non-merchandise stock codes (postage, fees, manual)", lambda d: ~d["StockCode"].str.match(PRODUCT_CODE_PATTERN)),
        (f"drop extreme quantity lines (> {MAX_LINE_QUANTITY})", lambda d: d["Quantity"] > MAX_LINE_QUANTITY),
        ("drop 'Unspecified' country", lambda d: d["Country"] == "Unspecified"),
        ("drop rows outside 2009-12-01..2011-12-09", lambda d: d["InvoiceDate"].isna()),
    ]:
        mask = func(df)
        log(name, mask)
        df = df[~mask]
    df["StockCode"] = df["StockCode"].str.upper()
    return df.reset_index(drop=True), steps


def build_products(df: pd.DataFrame) -> pd.DataFrame:
    # Most frequent description per code resolves inconsistent spellings.
    desc = df.dropna(subset=["Description"]).groupby("StockCode")["Description"].agg(lambda s: s.str.strip().str.upper().mode().iat[0])
    base = df.groupby("StockCode")["Price"].median()
    products = pd.DataFrame({"stock_code": base.index, "base_price": base.values.round(2)})
    products["product_name"] = products["stock_code"].map(desc).fillna("UNKNOWN").astype(str)
    products["category"] = products["product_name"].map(assign_category)
    products["pack_size"] = pack_sizes(len(products))
    products.insert(0, "product_id", np.arange(1, len(products) + 1))
    return products


def build_calendar(start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    cal = pd.DataFrame({"date": dates})
    cal["year"] = cal.date.dt.year
    cal["month"] = cal.date.dt.month
    cal["quarter"] = cal.date.dt.quarter
    cal["week"] = cal.date.dt.isocalendar().week.astype(int)
    cal["week_start"] = cal.date - pd.to_timedelta(cal.date.dt.day_of_week, unit="D")
    cal["weekday"] = cal.date.dt.day_name()
    cal["is_weekend"] = cal.date.dt.day_of_week >= 5
    cal["holiday_flag"] = cal.date.dt.strftime("%Y-%m-%d").isin(UK_BANK_HOLIDAYS)
    cal["is_pre_christmas"] = (cal.month == 11) | ((cal.month == 12) & (cal.date.dt.day <= 20))
    return cal


def main() -> None:
    raw = pd.read_parquet(RAW_PARQUET)
    report = quality_report(raw)
    df, steps = clean(raw)

    products = build_products(df)
    regions = region_table(df["Country"].unique().tolist())
    df["date"] = df["InvoiceDate"].dt.normalize()
    calendar = build_calendar(df["date"].min(), df["date"].max() + pd.Timedelta(days=90))

    sales = pd.DataFrame(
        {
            "transaction_id": np.arange(1, len(df) + 1),
            "invoice_id": df["Invoice"].values,
            "invoice_ts": df["InvoiceDate"].values,
            "date": df["date"].values,
            "customer_id": df["Customer ID"].astype("Int64").values,
            "product_id": df["StockCode"].map(products.set_index("stock_code")["product_id"]).values,
            "region_id": df["Country"].map(regions.set_index("country")["region_id"]).values,
            "quantity": df["Quantity"].values,
            "unit_price": df["Price"].values,
        }
    )
    sales["revenue"] = (sales["quantity"] * sales["unit_price"]).round(2)
    # Feature: price reduction vs the product's median price (a REAL-data proxy for discount).
    base_price = sales["product_id"].map(products.set_index("product_id")["base_price"])
    sales["discount_pct"] = (1 - sales["unit_price"] / base_price).clip(lower=0).round(4)

    # Synthetic campaign attribution: a line belongs to a campaign if date, region group and
    # category match the campaign's (synthetic) window and targets.
    campaigns = campaign_table(
        df["date"].min(), df["date"].max(), sorted(products["category"].unique()), sorted(regions["region_group"].unique())
    )
    group = sales["region_id"].map(regions.set_index("region_id")["region_group"])
    cat = sales["product_id"].map(products.set_index("product_id")["category"])
    sales["campaign_id"] = pd.array([pd.NA] * len(sales), dtype="Int64")
    for c in campaigns.itertuples():
        mask = (
            sales["date"].between(c.start_date, c.end_date)
            & (group == c.target_region_group)
            & (cat == c.target_category)
            & sales["campaign_id"].isna()
        )
        sales.loc[mask, "campaign_id"] = c.campaign_id

    cust = sales.dropna(subset=["customer_id"])
    first = cust.groupby("customer_id").agg(first_purchase_date=("date", "min"))
    home = cust.groupby("customer_id")["region_id"].agg(lambda s: s.mode().iat[0])
    customers = first.assign(region_id=home).reset_index()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    for name, table in [
        ("sales", sales),
        ("products", products),
        ("regions", regions),
        ("customers", customers),
        ("campaigns", campaigns),
        ("calendar", calendar),
    ]:
        con.register("tmp", table)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp")
        con.unregister("tmp")
    # Post-build referential checks (invalid foreign keys).
    fk = {
        "sales.product_id": con.execute(
            "SELECT COUNT(*) FROM sales s LEFT JOIN products p USING(product_id) WHERE p.product_id IS NULL"
        ).fetchone()[0],
        "sales.region_id": con.execute(
            "SELECT COUNT(*) FROM sales s LEFT JOIN regions r USING(region_id) WHERE r.region_id IS NULL"
        ).fetchone()[0],
        "sales.customer_id (non-null)": con.execute(
            "SELECT COUNT(*) FROM sales s LEFT JOIN customers c USING(customer_id) WHERE s.customer_id IS NOT NULL AND c.customer_id IS NULL"
        ).fetchone()[0],
        "sales.campaign_id (non-null)": con.execute(
            "SELECT COUNT(*) FROM sales s LEFT JOIN campaigns c USING(campaign_id) WHERE s.campaign_id IS NOT NULL AND c.campaign_id IS NULL"
        ).fetchone()[0],
        "sales.date": con.execute("SELECT COUNT(*) FROM sales s LEFT JOIN calendar c USING(date) WHERE c.date IS NULL").fetchone()[0],
    }
    con.close()
    for name, table in [("products", products), ("regions", regions), ("campaigns", campaigns)]:
        table.to_csv(PROCESSED_DIR / f"{name}.csv", index=False)

    clean_report = {
        "stage": "clean",
        "rows": len(sales),
        "rows_removed_total": len(raw) - len(sales),
        "rows_removed_pct": pct(len(raw) - len(sales), len(raw)),
        "missing_customer_id_pct": pct(sales["customer_id"].isna().sum(), len(sales)),
        "invalid_foreign_keys": {k: int(v) for k, v in fk.items()},
        "customers": len(customers),
        "products": len(products),
        "countries": len(regions),
        "campaign_lines_pct": pct(sales["campaign_id"].notna().sum(), len(sales)),
        "date_min": str(sales["date"].min().date()),
        "date_max": str(sales["date"].max().date()),
    }
    out = {"raw": report, "cleaning_steps": steps, "clean": clean_report}
    (ARTIFACTS_DIR / "data_quality.json").write_text(json.dumps(out, indent=2))
    write_markdown_report(out)
    print(f"[build] {len(sales):,} clean sales lines, {len(customers):,} customers, {len(products):,} products")


def write_markdown_report(out: dict) -> None:
    r, c = out["raw"], out["clean"]
    lines = [
        "# Data Quality Report",
        "",
        "_Generated by `scripts/build_dataset.py` from the actual data. Do not edit by hand._",
        "",
        "## Raw data (UCI Online Retail II, both sheets)",
        "",
        "| Check | Value |",
        "|---|---|",
    ]
    for key in [
        "rows",
        "missing_cells_pct",
        "duplicate_rows_pct",
        "invalid_dates_pct",
        "cancellation_rows_pct",
        "negative_quantity_pct",
        "impossible_price_pct",
        "non_product_code_pct",
        "inconsistent_category_pct",
        "unspecified_country_pct",
        "quantity_outlier_pct",
        "extreme_quantity_rows",
    ]:
        v = r[key]
        lines.append(f"| {key} | {v:,} |" if isinstance(v, int) else f"| {key} | {v}% |")
    lines += [
        "",
        f"Outlier rule: {r['quantity_outlier_rule']}.",
        f"Inconsistent categories: {r['inconsistent_category_note']}.",
        "",
        "Missing by column (%): " + ", ".join(f"{k}: {v}" for k, v in r["missing_by_column_pct"].items()),
        "",
        "## Cleaning steps (applied in order)",
        "",
        "| Rule | Rows removed |",
        "|---|---|",
    ]
    lines += [f"| {s['rule']} | {s['rows_removed']:,} |" for s in out["cleaning_steps"]]
    lines += ["", "## Clean data", "", "| Check | Value |", "|---|---|"]
    for k, v in c.items():
        if k != "invalid_foreign_keys":
            lines.append(f"| {k} | {v} |")
    lines += ["", "Invalid foreign keys after build: " + ", ".join(f"{k} = {v}" for k, v in c["invalid_foreign_keys"].items())]
    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "data_quality_report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
