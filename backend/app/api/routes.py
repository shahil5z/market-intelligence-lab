"""HTTP routes. Each route validates input, calls one service function and returns a Pydantic model."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app import db
from app.db import Filters
from app.schemas import models as m
from app.services import ai_analyst, artifacts_views, eda, insights, overview, statistics

router = APIRouter(prefix="/api")


def filters(start: date | None = None, end: date | None = None, region_group: str | None = None, category: str | None = None) -> Filters:
    if start and end and start > end:
        raise HTTPException(400, "start must be on or before end")
    return Filters(start, end, region_group or None, category or None)


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "database": db.DB_PATH.exists()}


@router.get("/meta/dimensions")
def dimensions() -> dict:
    lo, hi = db.date_bounds()
    return {**db.dimension_values(), "date_min": str(lo), "date_max": str(hi)}


@router.get("/overview", response_model=m.Overview)
def get_overview(start: date | None = None, end: date | None = None, region_group: str | None = None, category: str | None = None):
    return overview.overview(filters(start, end, region_group, category))


@router.get("/sales/trend", response_model=m.TrendResponse)
def get_trend(
    grain: str = "month", start: date | None = None, end: date | None = None, region_group: str | None = None, category: str | None = None
):
    return {"grain": grain, "rows": overview.sales_trend(filters(start, end, region_group, category), grain)}


@router.get("/sales/by-region", response_model=m.RowsResponse)
def get_by_region(start: date | None = None, end: date | None = None, category: str | None = None):
    return {"rows": overview.sales_by_region(filters(start, end, None, category))}


@router.get("/sales/by-product", response_model=m.ProductsResponse)
def get_by_product(
    start: date | None = None, end: date | None = None, region_group: str | None = None, limit: int = Query(15, ge=1, le=100)
):
    return overview.sales_by_product(filters(start, end, region_group, None), limit)


@router.get("/sales/distribution", response_model=m.DistributionResponse)
def get_distribution(start: date | None = None, end: date | None = None, region_group: str | None = None, category: str | None = None):
    return overview.order_value_distribution(filters(start, end, region_group, category))


@router.get("/sales/eda", response_model=m.EdaResponse)
def get_eda(region_group: str | None = None, category: str | None = None):
    return eda.eda(filters(None, None, region_group, category))


@router.get("/demand/forecast", response_model=m.ForecastResponse)
def get_forecast(series: str = "All regions"):
    return artifacts_views.forecast(series)


@router.get("/campaigns", response_model=m.CampaignList)
def get_campaigns():
    return artifacts_views.campaigns()


@router.get("/campaigns/{campaign_id}", response_model=m.CampaignDetail)
def get_campaign(campaign_id: int):
    return artifacts_views.campaign(campaign_id)


@router.get("/customers/segments", response_model=m.SegmentsResponse)
def get_segments():
    return artifacts_views.segments()


@router.get("/anomalies", response_model=m.AnomaliesResponse)
def get_anomalies(region: str | None = None, metric: str | None = None, severity: str | None = None, limit: int = Query(50, ge=1, le=500)):
    return artifacts_views.anomalies(region or None, metric or None, severity or None, limit)


@router.get("/statistics/options")
def get_stat_options():
    return statistics.options()


@router.post("/statistics/test", response_model=m.StatTestResponse)
def run_stat_test(req: m.StatTestRequest):
    if req.test in ("welch", "student"):
        if not (req.metric and req.dimension and req.group_a and req.group_b):
            raise HTTPException(422, "metric, dimension, group_a and group_b are required for t-tests")
        return statistics.two_sample(req.metric, req.dimension, req.group_a, req.group_b, equal_var=req.test == "student")
    if req.test == "chi_square":
        if not (req.row_dimension and req.col_dimension):
            raise HTTPException(422, "row_dimension and col_dimension are required")
        return statistics.chi_square(req.row_dimension, req.col_dimension)
    if not (req.x and req.y):
        raise HTTPException(422, "x and y are required for correlation")
    return statistics.correlation(req.x, req.y, req.method)


@router.get("/insights", response_model=m.InsightsResponse)
def get_insights():
    return {"findings": insights.key_findings()}


@router.get("/data-quality")
def get_data_quality():
    return artifacts_views.data_quality()


@router.post("/ai/analyze", response_model=m.AiResponse)
def ai_analyze(req: m.AiRequest):
    return ai_analyst.analyze(req.question, req.use_llm)
