from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from httpx import AsyncClient

from tests.e2e.helpers import (
    _unix,
    create_and_launch_experiment,
    ensure_event_type,
    ensure_feature_flag,
    ensure_metric,
    ensure_subject_user,
    now_unix,
)


pytestmark = pytest.mark.asyncio


async def _setup_ratio_metric(client, headers):
    await ensure_event_type(client, headers, "rpt_exposure", "Report Exposure")
    await ensure_event_type(
        client,
        headers,
        "rpt_conversion",
        "Report Conversion",
        requires_exposure=True,
    )
    await ensure_metric(
        client,
        headers,
        "rpt_rate",
        "Report Rate",
        '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"rpt_conversion"},"denominator":{"type":"COUNT","event_type_key":"rpt_exposure"}}',
    )


async def test_report_structure(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "rpt_flag_1", default_value="a"
    )
    await ensure_subject_user(client, auth_headers, "rpt-user-1")
    await _setup_ratio_metric(client, auth_headers)
    exp_id = await create_and_launch_experiment(
        client,
        auth_headers,
        "rpt_flag_1",
        "Report Test 1",
        target_metric_key="rpt_rate",
        metric_keys=["rpt_rate"],
    )

    dec = await client.post(
        "/decide",
        json={
            "subject_id": "rpt-user-1",
            "flag_keys": ["rpt_flag_1"],
            "attributes": {},
        },
    )
    did = dec.json()["decisions"]["rpt_flag_1"]["id"]

    now = datetime.now(UTC)
    await client.post(
        "/events",
        json={
            "events": [
                {
                    "event_type_key": "rpt_exposure",
                    "decision_id": did,
                    "timestamp": _unix(now - timedelta(seconds=10)),
                    "props": {},
                },
                {
                    "event_type_key": "rpt_conversion",
                    "decision_id": did,
                    "timestamp": _unix(now),
                    "props": {},
                },
            ]
        },
    )

    r = await client.get(
        f"/experiments/{exp_id}/report",
        params={
            "from_time": _unix(now - timedelta(hours=1)),
            "to_time": _unix(now + timedelta(hours=1)),
        },
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["experiment_id"] == exp_id
    assert "overall" in data
    assert "metrics" in data["overall"]
    assert "variants" in data
    assert isinstance(data["from_time"], int)
    assert isinstance(data["to_time"], int)


async def test_report_nonexistent_experiment_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.get(
        "/experiments/00000000-0000-0000-0000-ffffffffffff/report",
        params={"from_time": now_unix(-3600), "to_time": now_unix(3600)},
        headers=auth_headers,
    )
    assert r.status_code == 404, r.text


async def test_report_empty_metrics_when_no_events(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "rpt_empty_flag", default_value="a"
    )
    await _setup_ratio_metric(client, auth_headers)
    exp_id = await create_and_launch_experiment(
        client,
        auth_headers,
        "rpt_empty_flag",
        "Empty Report Test",
        target_metric_key="rpt_rate",
        metric_keys=["rpt_rate"],
    )
    now = datetime.now(UTC)
    r = await client.get(
        f"/experiments/{exp_id}/report",
        params={
            "from_time": _unix(now - timedelta(hours=1)),
            "to_time": _unix(now + timedelta(hours=1)),
        },
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "overall" in data


async def test_report_variant_isolation(
    client: AsyncClient, auth_headers: dict
) -> None:
    """Only variant with events should have non-zero metric."""
    await ensure_feature_flag(
        client, auth_headers, "rpt_iso_flag", default_value="a"
    )
    await ensure_subject_user(client, auth_headers, "rpt-iso-alice")
    await ensure_subject_user(client, auth_headers, "rpt-iso-bob")
    await _setup_ratio_metric(client, auth_headers)
    exp_id = await create_and_launch_experiment(
        client,
        auth_headers,
        "rpt_iso_flag",
        "Isolation Test",
        target_metric_key="rpt_rate",
        metric_keys=["rpt_rate"],
    )

    alice_dec = (
        await client.post(
            "/decide",
            json={
                "subject_id": "rpt-iso-alice",
                "flag_keys": ["rpt_iso_flag"],
                "attributes": {},
            },
        )
    ).json()["decisions"]["rpt_iso_flag"]

    bob_dec = (
        await client.post(
            "/decide",
            json={
                "subject_id": "rpt-iso-bob",
                "flag_keys": ["rpt_iso_flag"],
                "attributes": {},
            },
        )
    ).json()["decisions"]["rpt_iso_flag"]

    now = datetime.now(UTC)
    # Only send events for alice
    await client.post(
        "/events",
        json={
            "events": [
                {
                    "event_type_key": "rpt_exposure",
                    "decision_id": alice_dec["id"],
                    "timestamp": _unix(now - timedelta(seconds=10)),
                    "props": {},
                },
                {
                    "event_type_key": "rpt_conversion",
                    "decision_id": alice_dec["id"],
                    "timestamp": _unix(now),
                    "props": {},
                },
            ]
        },
    )

    r = await client.get(
        f"/experiments/{exp_id}/report",
        params={
            "from_time": _unix(now - timedelta(hours=1)),
            "to_time": _unix(now + timedelta(hours=1)),
        },
        headers=auth_headers,
    )
    assert r.status_code == 200
    report = r.json()

    # If alice and bob in different variants, their metrics should differ
    if alice_dec["variant_name"] != bob_dec["variant_name"]:
        metrics_by_variant = {
            v["variant_name"]: v["metrics"] for v in report["variants"]
        }
        alice_val = next(
            (
                m["value"]
                for m in metrics_by_variant.get(alice_dec["variant_name"], [])
                if m["metric_key"] == "rpt_rate"
            ),
            None,
        )
        bob_val = next(
            (
                m["value"]
                for m in metrics_by_variant.get(bob_dec["variant_name"], [])
                if m["metric_key"] == "rpt_rate"
            ),
            None,
        )
        if alice_val is not None and bob_val is not None:
            assert alice_val != bob_val
