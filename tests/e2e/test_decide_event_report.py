from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


def _unix(dt: datetime) -> int:
    """Return unix seconds (UTC) from a datetime."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


def _ts_unix(offset_seconds: int = 0) -> int:
    return _unix(datetime.now(UTC) + timedelta(seconds=offset_seconds))


@pytest.mark.asyncio
async def test_decide_event_report_flow(
    client: AsyncClient,
    auth_headers: dict[str, str],
    create_subject_users,
) -> None:
    flag_resp = await client.post(
        "/feature-flags",
        json={
            "key": "e2e_button_color",
            "value_type": "string",
            "default_value": "green",
        },
        headers=auth_headers,
    )
    assert flag_resp.status_code in (201, 400), flag_resp.text

    for et in [
        {
            "key": "exposure",
            "name": "Exposure",
            "description": "User saw the variant",
            "required_params": {},
            "requires_exposure": False,
        },
        {
            "key": "e2e_conversion",
            "name": "E2E Conversion",
            "description": "User converted",
            "required_params": {},
            "requires_exposure": True,
        },
    ]:
        r = await client.post("/event-types", json=et, headers=auth_headers)
        assert r.status_code in (201, 400), r.text

    metric_resp = await client.post(
        "/metrics",
        json={
            "key": "e2e_conversion_rate",
            "name": "E2E Conversion Rate",
            "calculation_rule": '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"e2e_conversion"},"denominator":{"type":"COUNT","event_type_key":"exposure"}}',
            "aggregation_unit": "user",
        },
        headers=auth_headers,
    )
    assert metric_resp.status_code in (201, 400), metric_resp.text

    exp_create = await client.post(
        "/experiments",
        json={
            "flag_key": "e2e_button_color",
            "name": "E2E Button Color Test",
            "audience_fraction": 1.0,
            "variants": [
                {
                    "name": "control",
                    "value": "green",
                    "weight": 0.5,
                    "is_control": True,
                },
                {
                    "name": "treatment",
                    "value": "blue",
                    "weight": 0.5,
                    "is_control": False,
                },
            ],
            "target_metric_key": "e2e_conversion_rate",
            "metric_keys": ["e2e_conversion_rate"],
        },
        headers=auth_headers,
    )
    assert exp_create.status_code == 201, exp_create.text
    experiment_id = exp_create.json()["id"]

    r = await client.post(
        f"/experiments/{experiment_id}/send-to-review",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text

    r = await client.post(
        f"/experiments/{experiment_id}/approve",
        json={"comment": "LGTM"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    r = await client.post(
        f"/experiments/{experiment_id}/launch",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "running"

    subjects = ["e2e-user-alice", "e2e-user-bob"]
    decision_ids: dict[str, str] = {}
    variant_names: dict[str, str] = {}

    for subj in subjects:
        decide_resp = await client.post(
            "/decide",
            json={
                "subject_id": subj,
                "flag_keys": ["e2e_button_color"],
                "attributes": {},
            },
        )
        assert decide_resp.status_code == 200, decide_resp.text
        decision = decide_resp.json()["decisions"]["e2e_button_color"]
        decision_ids[subj] = str(decision["id"])
        variant_names[subj] = decision["variant_name"]
        # timestamp returned as unix int
        assert isinstance(decision["timestamp"], int), (
            f"Expected int timestamp, got {type(decision['timestamp'])}: {decision['timestamp']}"
        )

    assert any(v is not None for v in variant_names.values())

    # Send events with unix timestamps
    now = datetime.now(UTC)
    events_payload = []
    for subj in subjects:
        did = decision_ids[subj]
        events_payload.append(
            {
                "event_type_key": "exposure",
                "decision_id": did,
                "timestamp": _unix(now - timedelta(seconds=10)),
                "props": {},
            }
        )
        events_payload.append(
            {
                "event_type_key": "e2e_conversion",
                "decision_id": did,
                "timestamp": _unix(now),
                "props": {},
            }
        )

    events_resp = await client.post(
        "/events",
        json={"events": events_payload},
    )
    assert events_resp.status_code == 200, events_resp.text
    batch = events_resp.json()
    assert batch["rejected"] == 0, f"Some events rejected: {batch}"
    assert batch["accepted"] > 0

    # Report with unix from/to
    from_unix = _unix(now - timedelta(hours=1))
    to_unix = _unix(now + timedelta(hours=1))

    report_resp = await client.get(
        f"/experiments/{experiment_id}/report",
        params={"from_time": from_unix, "to_time": to_unix},
        headers=auth_headers,
    )
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()

    assert report["experiment_id"] == experiment_id
    assert len(report["variants"]) == 2

    # from_time / to_time in report response are unix ints
    assert isinstance(report["from_time"], int), report["from_time"]
    assert isinstance(report["to_time"], int), report["to_time"]

    # overall section must be present
    assert "overall" in report, "Report must contain 'overall' section"
    assert "metrics" in report["overall"], "overall must have 'metrics'"

    # Each variant should have metrics
    for variant_report in report["variants"]:
        assert "metrics" in variant_report
        assert "variant_name" in variant_report
        if variant_report["metrics"]:
            primary = next(
                (m for m in variant_report["metrics"] if m["is_primary"]),
                None,
            )
            if primary is not None:
                assert primary["metric_key"] == "e2e_conversion_rate"
                assert "aggregation_unit" in primary
                assert primary["aggregation_unit"] == "user"


# ---------------------------------------------------------------------------
# Test: /decide returns default when no active experiment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decide_returns_default_without_experiment(
    client: AsyncClient,
    auth_headers: dict[str, str],
    create_subject_users,
) -> None:
    """B2-1: system returns default value when no active experiment exists."""
    flag_key = "e2e_no_exp_flag"
    r = await client.post(
        "/feature-flags",
        json={
            "key": flag_key,
            "value_type": "string",
            "default_value": "default_val",
        },
        headers=auth_headers,
    )
    assert r.status_code in (201, 400), r.text

    decide_resp = await client.post(
        "/decide",
        json={
            "subject_id": "anon-user",
            "flag_keys": [flag_key],
            "attributes": {},
        },
    )
    assert decide_resp.status_code == 200, decide_resp.text
    decision = decide_resp.json()["decisions"][flag_key]
    assert decision["value"] == "default_val"
    assert decision["experiment_id"] is None
    assert decision["variant_name"] is None


# ---------------------------------------------------------------------------
# Test: event deduplication
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_deduplication(
    client: AsyncClient,
    auth_headers: dict[str, str],
    create_subject_users,
) -> None:
    """B4-3: duplicate events (same payload) are not double-counted."""
    decide_resp = await client.post(
        "/decide",
        json={
            "subject_id": "dedup-test-user",
            "flag_keys": ["e2e_button_color"],
            "attributes": {},
        },
    )
    assert decide_resp.status_code == 200, decide_resp.text
    decision = decide_resp.json()["decisions"]["e2e_button_color"]
    decision_id = str(decision["id"])

    now_unix = _ts_unix()
    event = {
        "event_type_key": "exposure",
        "decision_id": decision_id,
        "timestamp": now_unix,
        "props": {},
    }

    r1 = await client.post("/events", json={"events": [event]})
    assert r1.status_code == 200
    assert r1.json()["accepted"] == 1

    r2 = await client.post("/events", json={"events": [event]})
    assert r2.status_code == 200
    r2_body = r2.json()
    assert r2_body["duplicates"] == 1
    assert r2_body["accepted"] == 0


# ---------------------------------------------------------------------------
# Test: event validation rejects unknown event type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_unknown_type_rejected(
    client: AsyncClient,
    auth_headers: dict[str, str],
    create_subject_users,
) -> None:
    """B4-1/B4-2: events with unknown type_key are rejected."""
    decide_resp = await client.post(
        "/decide",
        json={
            "subject_id": "validation-user",
            "flag_keys": ["e2e_button_color"],
            "attributes": {},
        },
    )
    assert decide_resp.status_code == 200
    decision_id = str(decide_resp.json()["decisions"]["e2e_button_color"]["id"])

    r = await client.post(
        "/events",
        json={
            "events": [
                {
                    "event_type_key": "nonexistent_event_xyz",
                    "decision_id": decision_id,
                    "timestamp": _ts_unix(),
                    "props": {},
                }
            ]
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["rejected"] == 1
    assert body["accepted"] == 0


# ---------------------------------------------------------------------------
# Test: experiment archive (COMPLETED → ARCHIVED)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_experiment_archive_flow(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify COMPLETED → ARCHIVED transition via POST /experiments/{id}/archive."""
    flag_key = "e2e_archive_flag"
    r = await client.post(
        "/feature-flags",
        json={"key": flag_key, "value_type": "bool", "default_value": False},
        headers=auth_headers,
    )
    assert r.status_code in (201, 400), r.text

    exp_resp = await client.post(
        "/experiments",
        json={
            "flag_key": flag_key,
            "name": "E2E Archive Test",
            "audience_fraction": 0.5,
            "variants": [
                {
                    "name": "ctrl",
                    "value": False,
                    "weight": 0.25,
                    "is_control": True,
                },
                {
                    "name": "treat",
                    "value": True,
                    "weight": 0.25,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    assert exp_resp.status_code == 201, exp_resp.text
    exp_id = exp_resp.json()["id"]

    await client.post(
        f"/experiments/{exp_id}/send-to-review", headers=auth_headers
    )
    await client.post(
        f"/experiments/{exp_id}/approve",
        json={"comment": "ok"},
        headers=auth_headers,
    )
    await client.post(f"/experiments/{exp_id}/launch", headers=auth_headers)
    complete_resp = await client.post(
        f"/experiments/{exp_id}/complete",
        json={
            "outcome": "no_effect",
            "comment": "No significant difference found.",
        },
        headers=auth_headers,
    )
    assert complete_resp.status_code == 200, complete_resp.text
    completed = complete_resp.json()
    assert completed["status"] == "completed"
    # completed_at must be unix int
    assert isinstance(completed["completion"]["completed_at"], int), (
        f"Expected int for completed_at, got: {completed['completion']['completed_at']}"
    )

    archive_resp = await client.post(
        f"/experiments/{exp_id}/archive",
        headers=auth_headers,
    )
    assert archive_resp.status_code == 200, archive_resp.text
    assert archive_resp.json()["status"] == "archived"

    # Archiving again should fail
    archive_again = await client.post(
        f"/experiments/{exp_id}/archive",
        headers=auth_headers,
    )
    assert archive_again.status_code == 400


# ---------------------------------------------------------------------------
# Test: report respects time window — now uses unix from/to
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_time_window_filter(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """B6-1: report filtered by time window (unix seconds) → 404 for non-existent experiment."""
    from_unix = _unix(datetime(2020, 1, 1, tzinfo=UTC))
    to_unix = _unix(datetime(2020, 1, 2, tzinfo=UTC))

    report_resp = await client.get(
        "/experiments/00000000-0000-0000-0000-000000000001/report",
        params={"from_time": from_unix, "to_time": to_unix},
        headers=auth_headers,
    )
    assert report_resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: batch /events continues processing after a type-invalid item (B4-1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_events_batch_partial_reject(
    client: AsyncClient,
    auth_headers: dict[str, str],
    create_subject_users,
) -> None:
    """B4-1: a single malformed event in a batch does not abort the whole batch."""
    decide_resp = await client.post(
        "/decide",
        json={
            "subject_id": "e2e-user-alice",
            "flag_keys": ["e2e_button_color"],
            "attributes": {},
        },
    )
    assert decide_resp.status_code == 200, decide_resp.text
    decision_id = decide_resp.json()["decisions"]["e2e_button_color"]["id"]

    invalid_event = {
        "event_type_key": "exposure",
        "decision_id": decision_id,
        "timestamp": "NOT_A_DATE",
        "props": {},
    }
    valid_event = {
        "event_type_key": "exposure",
        "decision_id": decision_id,
        "timestamp": _ts_unix(-5),
        "props": {},
    }

    r = await client.post(
        "/events",
        json={"events": [invalid_event, valid_event]},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["rejected"] == 1, f"Expected 1 rejected, got: {body}"
    assert body["accepted"] >= 1 or body["duplicates"] >= 1, (
        f"The valid event should be accepted or deduped: {body}"
    )
    assert len(body["errors"]) == 1
    assert body["errors"][0]["index"] == 0


# ---------------------------------------------------------------------------
# Test: guardrail configs have UUID ids; B6-2 variant isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guardrail_config_has_uuid_id(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Guardrail configs must expose 'id' (UUID) in experiment response."""
    flag_key = "e2e_guardrail_uuid_flag"
    r = await client.post(
        "/feature-flags",
        json={"key": flag_key, "value_type": "string", "default_value": "off"},
        headers=auth_headers,
    )
    assert r.status_code in (201, 400), r.text

    exp_resp = await client.post(
        "/experiments",
        json={
            "flag_key": flag_key,
            "name": "E2E Guardrail UUID Test",
            "audience_fraction": 1.0,
            "variants": [
                {
                    "name": "control",
                    "value": "off",
                    "weight": 0.5,
                    "is_control": True,
                },
                {
                    "name": "treatment",
                    "value": "on",
                    "weight": 0.5,
                    "is_control": False,
                },
            ],
            "guardrails": [
                {
                    "metric_key": "e2e_conversion_rate",
                    "threshold": 0.05,
                    "observation_window_minutes": 60,
                    "action": "pause",
                }
            ],
        },
        headers=auth_headers,
    )
    assert exp_resp.status_code == 201, exp_resp.text
    exp_data = exp_resp.json()

    assert len(exp_data["guardrails"]) == 1, exp_data["guardrails"]
    guardrail = exp_data["guardrails"][0]
    assert "id" in guardrail, f"guardrail missing 'id': {guardrail}"
    assert guardrail["id"] is not None, (
        "guardrail 'id' must not be None after save"
    )
    # Must look like a UUID string
    import re

    uuid_pattern = (
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    )
    assert re.match(uuid_pattern, guardrail["id"]), (
        f"guardrail 'id' is not a valid UUID: {guardrail['id']}"
    )


@pytest.mark.asyncio
async def test_report_variants_differ_when_only_one_has_events(
    client: AsyncClient,
    auth_headers: dict[str, str],
    create_subject_users,
) -> None:
    flag_key = "e2e_variant_diff_flag"
    r = await client.post(
        "/feature-flags",
        json={"key": flag_key, "value_type": "string", "default_value": "a"},
        headers=auth_headers,
    )
    assert r.status_code in (201, 400), r.text

    # Ensure event types and metric exist
    for et in [
        {
            "key": "exposure",
            "name": "Exposure",
            "description": "",
            "required_params": {},
            "requires_exposure": False,
        },
        {
            "key": "e2e_conversion",
            "name": "E2E Conversion",
            "description": "",
            "required_params": {},
            "requires_exposure": True,
        },
    ]:
        await client.post("/event-types", json=et, headers=auth_headers)

    await client.post(
        "/metrics",
        json={
            "key": "e2e_conversion_rate",
            "name": "E2E Conversion Rate",
            "calculation_rule": '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"e2e_conversion"},"denominator":{"type":"COUNT","event_type_key":"exposure"}}',
            "aggregation_unit": "user",
        },
        headers=auth_headers,
    )

    exp_resp = await client.post(
        "/experiments",
        json={
            "flag_key": flag_key,
            "name": "E2E Variant Diff Test",
            "audience_fraction": 1.0,
            "variants": [
                {
                    "name": "control",
                    "value": "a",
                    "weight": 0.5,
                    "is_control": True,
                },
                {
                    "name": "treatment",
                    "value": "b",
                    "weight": 0.5,
                    "is_control": False,
                },
            ],
            "target_metric_key": "e2e_conversion_rate",
            "metric_keys": ["e2e_conversion_rate"],
        },
        headers=auth_headers,
    )
    assert exp_resp.status_code == 201, exp_resp.text
    exp_id = exp_resp.json()["id"]

    # Launch experiment
    await client.post(
        f"/experiments/{exp_id}/send-to-review", headers=auth_headers
    )
    await client.post(
        f"/experiments/{exp_id}/approve",
        json={"comment": "ok"},
        headers=auth_headers,
    )
    await client.post(f"/experiments/{exp_id}/launch", headers=auth_headers)

    from icecream import ic

    ic(
        (
            await client.post(
                "/decide",
                json={
                    "subject_id": "alice-diff",
                    "flag_keys": [flag_key],
                    "attributes": {},
                },
            )
        ).json()
    )

    alice_dec = (
        await client.post(
            "/decide",
            json={
                "subject_id": "alice-diff",
                "flag_keys": [flag_key],
                "attributes": {},
            },
        )
    ).json()["decisions"][flag_key]
    bob_dec = (
        await client.post(
            "/decide",
            json={
                "subject_id": "bob-diff",
                "flag_keys": [flag_key],
                "attributes": {},
            },
        )
    ).json()["decisions"][flag_key]

    # Only send events for alice's decision
    now = datetime.now(UTC)
    events = [
        {
            "event_type_key": "exposure",
            "decision_id": str(alice_dec["id"]),
            "timestamp": _unix(now - timedelta(seconds=30)),
            "props": {},
        },
        {
            "event_type_key": "e2e_conversion",
            "decision_id": str(alice_dec["id"]),
            "timestamp": _unix(now - timedelta(seconds=15)),
            "props": {},
        },
    ]
    r = await client.post("/events", json={"events": events})
    assert r.status_code == 200

    from_unix = _unix(now - timedelta(hours=1))
    to_unix = _unix(now + timedelta(hours=1))

    report_resp = await client.get(
        f"/experiments/{exp_id}/report",
        params={"from_time": from_unix, "to_time": to_unix},
        headers=auth_headers,
    )
    assert report_resp.status_code == 200, report_resp.text
    report = report_resp.json()

    # overall must be present
    assert "overall" in report
    overall_metrics = report["overall"]["metrics"]
    assert len(overall_metrics) > 0, "overall must have metrics"

    # If alice and bob landed in different variants, one variant should have
    # events and the other should have 0 events → different metric values
    alice_variant = alice_dec["variant_name"]
    bob_variant = bob_dec["variant_name"]

    if (
        alice_variant != bob_variant
        and alice_variant is not None
        and bob_variant is not None
    ):
        metrics_by_variant = {
            v["variant_name"]: v["metrics"] for v in report["variants"]
        }
        alice_m = metrics_by_variant.get(alice_variant, [])
        bob_m = metrics_by_variant.get(bob_variant, [])
        alice_val = next(
            (
                m["value"]
                for m in alice_m
                if m["metric_key"] == "e2e_conversion_rate"
            ),
            None,
        )
        bob_val = next(
            (
                m["value"]
                for m in bob_m
                if m["metric_key"] == "e2e_conversion_rate"
            ),
            None,
        )
        # Alice received events, bob did not → alice's metric != bob's metric
        assert alice_val != bob_val, (
            f"Variants should have different metrics when only one has events: "
            f"alice={alice_val}, bob={bob_val}"
        )
