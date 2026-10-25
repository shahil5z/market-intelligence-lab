"""Pydantic request/response models. Nested chart rows are kept as plain dict lists for readability."""

from typing import Any, Literal

from pydantic import BaseModel, Field

Row = dict[str, Any]


class Overview(BaseModel):
    filters: Row
    data_range: Row
    revenue: float
    units: int
    orders: int
    aov: float
    customers: int
    products: int
    growth_rate_pct: float | None
    growth_comparison: str
    top_region: str
    top_region_share_pct: float
    top_category: str
    top_product: str
    currency: str


class TrendResponse(BaseModel):
    grain: str
    rows: list[Row]


class RowsResponse(BaseModel):
    rows: list[Row]


class ProductsResponse(BaseModel):
    categories: list[Row]
    top_products: list[Row]


class DistributionResponse(BaseModel):
    bins: list[Row]
    mean: float
    median: float
    p90: float
    skewness: float


class EdaResponse(BaseModel):
    seasonality: Row
    weekday: Row
    correlations: Row
    discount: Row
    campaign_periods: Row


class ForecastResponse(BaseModel):
    series: str
    target: str
    n_weeks: int
    periods: dict[str, Row]
    horizon_weeks: int
    features: list[str]
    validation_metrics: dict[str, Row]
    test_metrics: dict[str, Row]
    test_metrics_recursive: dict[str, Row]
    evaluation_note: str
    selected_model: str
    lowest_test_mae_model: str
    history: list[Row]
    future: list[Row]
    rf_feature_importance: dict[str, float] | None
    interval_note: str
    available_series: list[str]


class CampaignList(BaseModel):
    label: str
    assumptions: list[str]
    campaigns: list[Row]


class CampaignDetail(BaseModel):
    model_config = {"extra": "allow"}
    campaign_id: int
    campaign_name: str
    sufficient_data: bool
    daily: list[Row]
    label: str
    assumptions: list[str]


class SegmentsResponse(BaseModel):
    n_customers: int
    features: list[str]
    silhouette_by_k: list[Row]
    best_k_silhouette: int
    chosen_k: int
    ward_adjusted_rand_index: float
    pca_explained_variance_pct: list[float]
    medians: Row
    naming_rules: str
    segments: list[Row]
    pca_points: list[Row]


class AnomaliesResponse(BaseModel):
    method: str
    expected_range_rule: str
    severity_rule: str
    total_flagged: int
    n_matching: int
    anomalies: list[Row]
    series_name: str
    series: list[Row]
    series_anomalies: list[Row]
    regions: list[str]


class StatTestRequest(BaseModel):
    test: Literal["welch", "student", "chi_square", "correlation"]
    metric: str | None = Field(None, description="order_value | order_units | order_lines (t-tests)")
    dimension: str | None = Field(None, description="grouping dimension (t-tests)")
    group_a: str | None = None
    group_b: str | None = None
    row_dimension: str | None = None
    col_dimension: str | None = None
    x: str | None = None
    y: str | None = None
    method: Literal["pearson", "spearman"] = "spearman"


class StatTestResponse(BaseModel):
    model_config = {"extra": "allow"}
    test: str
    p_value: float
    significant_at_5pct: bool
    effect_size: Row
    interpretation: str
    business_note: str


class Insight(BaseModel):
    area: str
    text: str
    source: str


class InsightsResponse(BaseModel):
    findings: list[Insight]


class AiRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    use_llm: bool = True


class AiResponse(BaseModel):
    question: str
    intent: str
    tool: str
    result: Row
    answer: str
    explanation_source: Literal["openai", "rule_based"]
    status: str
