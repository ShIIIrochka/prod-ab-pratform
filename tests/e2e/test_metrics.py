"""E2E tests for /metrics routes."""

from __future__ import annotations

import pytest

from httpx import AsyncClient


pytestmark = pytest.mark.asyncio

_RATIO_RULE = '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"click"},"denominator":{"type":"COUNT","event_type_key":"view"}}'
_SUM_RULE = '{"type":"SUM","event_type_key":"purchase","prop_key":"amount"}'
_AVG_RULE = '{"type":"AVG","event_type_key":"session","prop_key":"duration"}'
_PERCENTILE_RULE = '{"type":"PERCENTILE","event_type_key":"latency","prop_key":"ms","percentile":95}'
_COUNT_RULE = '{"type":"COUNT","event_type_key":"pageview"}'


async def test_create_metric(client: AsyncClient, auth_headers: dict) -> None:
    r = await client.post(
        "/metrics",
        json={
            "key": "test_ratio_metric",
            "name": "Click-through Rate",
            "calculation_rule": _RATIO_RULE,
            "aggregation_unit": "user",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["key"] == "test_ratio_metric"
    assert data["aggregation_unit"] == "user"


async def test_create_metric_duplicate_returns_400(
    client: AsyncClient, auth_headers: dict
) -> None:
    payload = {
        "key": "metric_dup_test",
        "name": "Dup Metric",
        "calculation_rule": _COUNT_RULE,
        "aggregation_unit": "event",
    }
    r1 = await client.post("/metrics", json=payload, headers=auth_headers)
    assert r1.status_code in (201, 400)
    r2 = await client.post("/metrics", json=payload, headers=auth_headers)
    assert r2.status_code == 400, r2.text


async def test_list_metrics(client: AsyncClient, auth_headers: dict) -> None:
    await client.post(
        "/metrics",
        json={
            "key": "metric_list_test_1",
            "name": "List Test 1",
            "calculation_rule": _COUNT_RULE,
            "aggregation_unit": "event",
        },
        headers=auth_headers,
    )
    r = await client.get("/metrics", headers=auth_headers)
    assert r.status_code == 200, r.text

    keys = [m["key"] for m in r.json().get("metrics")]
    assert "metric_list_test_1" in keys


async def test_get_metric(client: AsyncClient, auth_headers: dict) -> None:
    await client.post(
        "/metrics",
        json={
            "key": "metric_get_test",
            "name": "Get Test",
            "calculation_rule": _SUM_RULE,
            "aggregation_unit": "user",
        },
        headers=auth_headers,
    )
    r = await client.get("/metrics/metric_get_test", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["key"] == "metric_get_test"


async def test_get_nonexistent_metric_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.get("/metrics/no_such_metric_xyz", headers=auth_headers)
    assert r.status_code == 404, r.text


async def test_create_percentile_metric(
    client: AsyncClient, auth_headers: dict
) -> None:
    """PERCENTILE type must be accepted by the API."""
    r = await client.post(
        "/metrics",
        json={
            "key": "p95_latency_metric",
            "name": "P95 Latency",
            "calculation_rule": _PERCENTILE_RULE,
            "aggregation_unit": "user",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["key"] == "p95_latency_metric"


async def test_create_avg_metric(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/metrics",
        json={
            "key": "avg_session_dur",
            "name": "Avg Session Duration",
            "calculation_rule": _AVG_RULE,
            "aggregation_unit": "user",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
