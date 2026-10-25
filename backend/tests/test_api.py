"""API tests: every endpoint responds with the documented shape."""

import pytest

GET_ENDPOINTS = [
    "/api/health",
    "/api/meta/dimensions",
    "/api/overview",
    "/api/sales/trend?grain=week",
    "/api/sales/by-region",
    "/api/sales/by-product",
    "/api/sales/distribution",
    "/api/sales/eda",
    "/api/demand/forecast",
    "/api/demand/forecast?series=United%20Kingdom",
    "/api/campaigns",
    "/api/campaigns/1",
    "/api/customers/segments",
    "/api/anomalies",
    "/api/anomalies?severity=high",
    "/api/statistics/options",
    "/api/insights",
    "/api/data-quality",
]


@pytest.mark.parametrize("url", GET_ENDPOINTS)
def test_get_endpoints(client, url):
    r = client.get(url)
    assert r.status_code == 200, r.text
    assert r.json()


def test_overview_filters(client):
    r = client.get("/api/overview", params={"start": "2011-01-01", "end": "2011-03-31", "region_group": "United Kingdom"})
    body = r.json()
    assert body["filters"]["region_group"] == "United Kingdom"
    assert body["top_region"] == "United Kingdom"


def test_bad_inputs(client):
    assert client.get("/api/overview", params={"start": "2011-05-01", "end": "2011-01-01"}).status_code == 400
    assert client.get("/api/sales/trend", params={"grain": "decade"}).status_code == 400
    assert client.get("/api/campaigns/999").status_code == 404
    assert client.get("/api/demand/forecast", params={"series": "Mars"}).status_code == 404


@pytest.mark.parametrize(
    "body",
    [
        {"test": "welch", "metric": "order_value", "dimension": "weekday_type", "group_a": "Weekday", "group_b": "Weekend"},
        {"test": "student", "metric": "order_units", "dimension": "quarter", "group_a": "Q1", "group_b": "Q4"},
        {"test": "chi_square", "row_dimension": "customer_type", "col_dimension": "order_size_band"},
        {"test": "correlation", "x": "discount_pct", "y": "units", "method": "pearson"},
    ],
)
def test_statistics(client, body):
    r = client.post("/api/statistics/test", json=body)
    assert r.status_code == 200, r.text
    assert 0 <= r.json()["p_value"] <= 1


def test_statistics_validation(client):
    assert client.post("/api/statistics/test", json={"test": "welch"}).status_code == 422
    assert (
        client.post(
            "/api/statistics/test",
            json={
                "test": "welch",
                "metric": "order_value",
                "dimension": "region_group",
                "group_a": "United Kingdom",
                "group_b": "United Kingdom",
            },
        ).status_code
        == 400
    )


def test_ai_analyze(client):
    r = client.post("/api/ai/analyze", json={"question": "What are the top products?"})
    assert r.status_code == 200
    assert r.json()["intent"] == "top_products"
    assert client.post("/api/ai/analyze", json={"question": ""}).status_code == 422
