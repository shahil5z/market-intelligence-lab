"""Data-access layer. ALL SQL used by the API lives in this module.

DuckDB is used locally. The queries use standard SQL (joins, GROUP BY, DATE_TRUNC, window-free
aggregates) so moving to PostgreSQL means changing `connect()` and a few date functions here only.
"""

from dataclasses import dataclass
from datetime import date

import duckdb
import pandas as pd

from app.config import DB_PATH


def connect() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"{DB_PATH} not found - run `python scripts/run_pipeline.py` first")
    return duckdb.connect(str(DB_PATH), read_only=True)


def query(sql: str, params: list | None = None) -> pd.DataFrame:
    with connect() as con:
        return con.execute(sql, params or []).df()


@dataclass
class Filters:
    start: date | None = None
    end: date | None = None
    region_group: str | None = None
    category: str | None = None

    def where(self) -> tuple[str, list]:
        clauses, params = ["1=1"], []
        if self.start:
            clauses.append("s.date >= ?")
            params.append(self.start)
        if self.end:
            clauses.append("s.date <= ?")
            params.append(self.end)
        if self.region_group:
            clauses.append("r.region_group = ?")
            params.append(self.region_group)
        if self.category:
            clauses.append("p.category = ?")
            params.append(self.category)
        return " AND ".join(clauses), params


BASE_JOIN = "FROM sales s JOIN regions r USING(region_id) JOIN products p USING(product_id) JOIN calendar c USING(date)"


# ---------- overview / sales ----------
def kpis(f: Filters) -> dict:
    where, params = f.where()
    row = query(
        f"""SELECT COALESCE(SUM(s.revenue),0) AS revenue, COALESCE(SUM(s.quantity),0) AS units,
                    COUNT(DISTINCT s.invoice_id) AS orders, COUNT(DISTINCT s.customer_id) AS customers,
                    COUNT(DISTINCT s.product_id) AS products, MIN(s.date) AS first_date, MAX(s.date) AS last_date
                    {BASE_JOIN} WHERE {where}""",
        params,
    ).iloc[0]
    return row.to_dict()


def date_bounds() -> tuple[date, date]:
    row = query("SELECT MIN(date) AS lo, MAX(date) AS hi FROM sales").iloc[0]
    return row.lo.date(), row.hi.date()


def revenue_between(f: Filters, start: date, end: date) -> float:
    g = Filters(start, end, f.region_group, f.category)
    return float(kpis(g)["revenue"])


def trend(f: Filters, grain: str) -> pd.DataFrame:
    where, params = f.where()
    return query(
        f"""SELECT DATE_TRUNC('{grain}', s.date) AS period, SUM(s.revenue) AS revenue, SUM(s.quantity) AS units,
                     COUNT(DISTINCT s.invoice_id) AS orders {BASE_JOIN} WHERE {where} GROUP BY 1 ORDER BY 1""",
        params,
    )


def by_region(f: Filters) -> pd.DataFrame:
    where, params = f.where()
    return query(
        f"""SELECT r.region_group, SUM(s.revenue) AS revenue, SUM(s.quantity) AS units,
                     COUNT(DISTINCT s.invoice_id) AS orders, COUNT(DISTINCT s.customer_id) AS customers,
                     COUNT(DISTINCT r.country) AS countries {BASE_JOIN} WHERE {where} GROUP BY 1 ORDER BY 2 DESC""",
        params,
    )


def by_category(f: Filters) -> pd.DataFrame:
    where, params = f.where()
    return query(
        f"""SELECT p.category, SUM(s.revenue) AS revenue, SUM(s.quantity) AS units, COUNT(DISTINCT s.product_id) AS products
                     {BASE_JOIN} WHERE {where} GROUP BY 1 ORDER BY 2 DESC""",
        params,
    )


def top_products(f: Filters, limit: int) -> pd.DataFrame:
    where, params = f.where()
    return query(
        f"""SELECT p.product_id, p.stock_code, p.product_name, p.category, SUM(s.revenue) AS revenue,
                     SUM(s.quantity) AS units, MEDIAN(s.unit_price) AS median_price
                     {BASE_JOIN} WHERE {where} GROUP BY 1,2,3,4 ORDER BY 5 DESC LIMIT {int(limit)}""",
        params,
    )


def order_values(f: Filters) -> pd.Series:
    where, params = f.where()
    return query(f"SELECT SUM(s.revenue) AS v {BASE_JOIN} WHERE {where} GROUP BY s.invoice_id", params)["v"]


def dimension_values() -> dict:
    return {
        "region_groups": query("SELECT DISTINCT region_group FROM regions ORDER BY 1")["region_group"].tolist(),
        "categories": query("SELECT DISTINCT category FROM products ORDER BY 1")["category"].tolist(),
    }


# ---------- EDA ----------
def month_of_year(f: Filters) -> pd.DataFrame:
    where, params = f.where()
    return query(f"""SELECT c.year, c.month, SUM(s.revenue) AS revenue {BASE_JOIN} WHERE {where} GROUP BY 1,2 ORDER BY 1,2""", params)


def weekday_profile(f: Filters) -> pd.DataFrame:
    where, params = f.where()
    return query(
        f"""SELECT c.weekday, ISODOW(s.date) AS dow, COUNT(DISTINCT s.date) AS trading_days, SUM(s.revenue) AS revenue,
                     COUNT(DISTINCT s.invoice_id) AS orders {BASE_JOIN} WHERE {where} GROUP BY 1,2 ORDER BY 2""",
        params,
    )


def product_weeks(f: Filters) -> pd.DataFrame:
    """One row per product per week: the unit used for price/discount vs demand analysis."""
    where, params = f.where()
    return query(
        f"""SELECT s.product_id, c.week_start, SUM(s.quantity) AS units, AVG(s.unit_price) AS avg_price,
                     AVG(s.discount_pct) AS discount_pct, COUNT(DISTINCT s.customer_id) AS customers,
                     MAX(c.is_pre_christmas::INT) AS is_pre_christmas
                     {BASE_JOIN} WHERE {where} GROUP BY 1,2""",
        params,
    )


def discount_bands(f: Filters) -> pd.DataFrame:
    where, params = f.where()
    return query(
        f"""SELECT CASE WHEN s.discount_pct = 0 THEN '0% (at/above median price)'
                                 WHEN s.discount_pct < 0.10 THEN '0-10%'
                                 WHEN s.discount_pct < 0.25 THEN '10-25%' ELSE '25%+' END AS band,
                            MIN(s.discount_pct) AS sort_key, COUNT(*) AS lines, AVG(s.quantity) AS avg_quantity,
                            MEDIAN(s.quantity) AS median_quantity, SUM(s.revenue) AS revenue
                     {BASE_JOIN} WHERE {where} GROUP BY 1 ORDER BY 2""",
        params,
    )


def campaign_share(f: Filters) -> dict:
    where, params = f.where()
    return (
        query(
            f"""SELECT SUM(CASE WHEN s.campaign_id IS NOT NULL THEN s.revenue ELSE 0 END) AS campaign_revenue,
                     SUM(s.revenue) AS total_revenue {BASE_JOIN} WHERE {where}""",
            params,
        )
        .iloc[0]
        .to_dict()
    )


# ---------- statistics lab ----------
ORDER_DIMENSIONS = {
    "region_group": "o.region_group",
    "weekday_type": "o.weekday_type",
    "campaign_period": "o.campaign_period",
    "quarter": "o.quarter",
    "customer_type": "o.customer_type",
    "order_size_band": "o.order_size_band",
}
ORDER_METRICS = {"order_value": "o.order_value", "order_units": "o.order_units", "order_lines": "o.order_lines"}

ORDERS_CTE = """
WITH o AS (
  SELECT s.invoice_id,
         ANY_VALUE(r.region_group) AS region_group,
         CASE WHEN ANY_VALUE(c.is_weekend) THEN 'Weekend' ELSE 'Weekday' END AS weekday_type,
         CASE WHEN COUNT(s.campaign_id) > 0 THEN 'In campaign' ELSE 'Not in campaign' END AS campaign_period,
         'Q' || ANY_VALUE(c.quarter)::VARCHAR AS quarter,
         CASE WHEN ANY_VALUE(s.customer_id) IS NULL THEN 'Guest (no ID)' ELSE 'Registered' END AS customer_type,
         SUM(s.revenue) AS order_value, SUM(s.quantity) AS order_units, COUNT(*) AS order_lines,
         CASE WHEN SUM(s.revenue) < 100 THEN 'Small (<100)' WHEN SUM(s.revenue) < 500 THEN 'Medium (100-500)'
              ELSE 'Large (500+)' END AS order_size_band
  FROM sales s JOIN regions r USING(region_id) JOIN calendar c USING(date)
  GROUP BY s.invoice_id)
"""


def order_metric_by_group(metric: str, dimension: str, group: str) -> pd.Series:
    sql = f"{ORDERS_CTE} SELECT {ORDER_METRICS[metric]} AS v FROM o WHERE {ORDER_DIMENSIONS[dimension]} = ?"
    return query(sql, [group])["v"]


def order_dimension_levels(dimension: str) -> list[str]:
    return query(f"{ORDERS_CTE} SELECT DISTINCT {ORDER_DIMENSIONS[dimension]} AS v FROM o ORDER BY 1")["v"].tolist()


def crosstab(row_dim: str, col_dim: str) -> pd.DataFrame:
    return query(f"""{ORDERS_CTE} SELECT {ORDER_DIMENSIONS[row_dim]} AS row_level, {ORDER_DIMENSIONS[col_dim]} AS col_level,
                     COUNT(*) AS n FROM o GROUP BY 1,2""")


# ---------- AI analyst helpers ----------
def quarterly_revenue_by_region() -> pd.DataFrame:
    return query(f"""SELECT c.year, c.quarter, r.region_group, SUM(s.revenue) AS revenue {BASE_JOIN}
                     GROUP BY 1,2,3 ORDER BY 1,2,3""")


def quarterly_category_revenue(year: int, quarters: list[int]) -> pd.DataFrame:
    return query(
        f"""SELECT c.quarter, p.category, SUM(s.revenue) AS revenue {BASE_JOIN}
                     WHERE c.year = ? AND c.quarter IN ({",".join("?" * len(quarters))}) GROUP BY 1,2""",
        [year, *quarters],
    )


def yearly_region_revenue() -> pd.DataFrame:
    return query(f"""SELECT c.year, r.region_group, SUM(s.revenue) AS revenue, COUNT(DISTINCT s.date) AS trading_days
                     {BASE_JOIN} GROUP BY 1,2 ORDER BY 1,2""")
