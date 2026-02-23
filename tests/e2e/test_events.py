from __future__ import annotations

import pytest

from httpx import AsyncClient

from tests.e2e.helpers import (
    create_and_launch_experiment,
    ensure_event_type,
    ensure_feature_flag,
    ensure_subject_user,
    now_unix,
)


pytestmark = pytest.mark.asyncio


async def test_create_event_type(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/event-types",
        json={
            "key": "et_create_test",
            "name": "Create Test",
            "description": "A test event type",
            "required_params": {},
            "requires_exposure": False,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    assert r.json()["key"] == "et_create_test"


async def test_list_event_types(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_event_type(client, auth_headers, "et_list_test", "List Test")
    r = await client.get("/event-types", headers=auth_headers)
    assert r.status_code == 200, r.text
    keys = [e["key"] for e in r.json().get("event_types")]
    assert "et_list_test" in keys


async def test_get_event_type(client: AsyncClient, auth_headers: dict) -> None:
    await ensure_event_type(client, auth_headers, "et_get_test", "Get Test")
    r = await client.get("/event-types/et_get_test", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["key"] == "et_get_test"


async def test_get_nonexistent_event_type_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.get(
        "/event-types/nonexistent_et_xyz", headers=auth_headers
    )
    assert r.status_code == 404, r.text


async def test_send_event_accepted(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "events_flag_1", default_value="x"
    )
    await ensure_subject_user(client, auth_headers, "events-user-1")
    await ensure_event_type(client, auth_headers, "ev_basic", "Basic Event")
    await create_and_launch_experiment(
        client, auth_headers, "events_flag_1", "Events Test 1"
    )

    dec = await client.post(
        "/decide",
        json={
            "subject_id": "events-user-1",
            "flag_keys": ["events_flag_1"],
            "attributes": {},
        },
    )
    decision_id = dec.json()["decisions"]["events_flag_1"]["id"]

    r = await client.post(
        "/events",
        json={
            "events": [
                {
                    "event_type_key": "ev_basic",
                    "decision_id": decision_id,
                    "timestamp": now_unix(),
                    "props": {},
                }
            ]
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["accepted"] == 1
    assert body["rejected"] == 0


async def test_event_deduplication(
    client: AsyncClient, auth_headers: dict
) -> None:
    """Same event sent twice should be deduplicated."""
    await ensure_feature_flag(
        client, auth_headers, "events_dedup_flag", default_value="x"
    )
    await ensure_subject_user(client, auth_headers, "events-dedup-user")
    await ensure_event_type(client, auth_headers, "ev_dedup", "Dedup Event")
    await create_and_launch_experiment(
        client, auth_headers, "events_dedup_flag", "Dedup Test"
    )
    dec = await client.post(
        "/decide",
        json={
            "subject_id": "events-dedup-user",
            "flag_keys": ["events_dedup_flag"],
            "attributes": {},
        },
    )
    decision_id = dec.json()["decisions"]["events_dedup_flag"]["id"]

    event = {
        "event_type_key": "ev_dedup",
        "decision_id": decision_id,
        "timestamp": now_unix(),
        "props": {},
    }
    r1 = await client.post("/events", json={"events": [event]})
    assert r1.status_code == 200
    assert r1.json()["accepted"] == 1

    r2 = await client.post("/events", json={"events": [event]})
    assert r2.status_code == 200
    assert r2.json()["duplicates"] == 1
    assert r2.json()["accepted"] == 0


async def test_event_unknown_type_rejected(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "events_unk_flag", default_value="x"
    )
    await ensure_subject_user(client, auth_headers, "events-unk-user")
    await ensure_event_type(client, auth_headers, "ev_valid", "Valid Event")
    await create_and_launch_experiment(
        client, auth_headers, "events_unk_flag", "Unknown Event Test"
    )
    dec = await client.post(
        "/decide",
        json={
            "subject_id": "events-unk-user",
            "flag_keys": ["events_unk_flag"],
            "attributes": {},
        },
    )
    decision_id = dec.json()["decisions"]["events_unk_flag"]["id"]

    r = await client.post(
        "/events",
        json={
            "events": [
                {
                    "event_type_key": "totally_nonexistent_xyz",
                    "decision_id": decision_id,
                    "timestamp": now_unix(),
                    "props": {},
                }
            ]
        },
    )
    assert r.status_code == 200
    assert r.json()["rejected"] == 1


async def test_batch_partial_reject(
    client: AsyncClient, auth_headers: dict
) -> None:
    """One invalid event in batch doesn't abort others."""
    await ensure_feature_flag(
        client, auth_headers, "events_partial_flag", default_value="x"
    )
    await ensure_subject_user(client, auth_headers, "events-partial-user")
    await ensure_event_type(client, auth_headers, "ev_partial", "Partial Event")
    await create_and_launch_experiment(
        client, auth_headers, "events_partial_flag", "Partial Test"
    )
    dec = await client.post(
        "/decide",
        json={
            "subject_id": "events-partial-user",
            "flag_keys": ["events_partial_flag"],
            "attributes": {},
        },
    )
    decision_id = dec.json()["decisions"]["events_partial_flag"]["id"]

    r = await client.post(
        "/events",
        json={
            "events": [
                {
                    "event_type_key": "ev_partial",
                    "decision_id": decision_id,
                    "timestamp": "NOT_A_TIMESTAMP",
                    "props": {},
                },
                {
                    "event_type_key": "ev_partial",
                    "decision_id": decision_id,
                    "timestamp": now_unix(-1),
                    "props": {},
                },
            ]
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rejected"] == 1
    assert body["accepted"] >= 1 or body["duplicates"] >= 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["index"] == 0
