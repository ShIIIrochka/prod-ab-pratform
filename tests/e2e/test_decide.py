from __future__ import annotations

import pytest

from httpx import AsyncClient

from tests.e2e.helpers import (
    create_and_launch_experiment,
    ensure_feature_flag,
    ensure_subject_user,
)


pytestmark = pytest.mark.asyncio


async def test_decide_with_running_experiment(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "decide_flag_1", default_value="off"
    )
    await ensure_subject_user(client, auth_headers, "decide-user-1")
    exp_id = await create_and_launch_experiment(
        client, auth_headers, "decide_flag_1", "Decide Test 1"
    )

    r = await client.post(
        "/decide",
        json={
            "subject_id": "decide-user-1",
            "flag_keys": ["decide_flag_1"],
            "attributes": {},
        },
    )
    assert r.status_code == 200, r.text
    decision = r.json()["decisions"]["decide_flag_1"]
    assert decision["value"] in ("off", "on")
    assert decision["experiment_id"] == exp_id
    assert decision["variant_name"] in ("control", "treatment")
    assert isinstance(decision["timestamp"], int)


async def test_decide_returns_default_when_no_experiment(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client=client,
        headers=auth_headers,
        key="decide_no_exp_flag",
        default_value="the_default",
    )
    await ensure_subject_user(client, auth_headers, "decide-user-noexp")

    r = await client.post(
        "/decide",
        json={
            "subject_id": "decide-user-noexp",
            "flag_keys": ["decide_no_exp_flag"],
            "attributes": {},
        },
    )
    assert r.status_code == 200, r.text
    decision = r.json()["decisions"]["decide_no_exp_flag"]
    assert decision["value"] == "the_default"
    assert decision["experiment_id"] is None


async def test_decide_multiple_flags(
    client: AsyncClient, auth_headers: dict
) -> None:
    for key in ["mflag_a", "mflag_b"]:
        await ensure_feature_flag(
            client, auth_headers, key, default_value=f"{key}_default"
        )
    await ensure_subject_user(client, auth_headers, "decide-multi-user")

    r = await client.post(
        "/decide",
        json={
            "subject_id": "decide-multi-user",
            "flag_keys": ["mflag_a", "mflag_b"],
            "attributes": {},
        },
    )
    assert r.status_code == 200, r.text
    decisions = r.json()["decisions"]
    assert "mflag_a" in decisions
    assert "mflag_b" in decisions


async def test_decide_consistency_same_subject(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "decide_sticky_flag", default_value="x"
    )
    await ensure_subject_user(client, auth_headers, "sticky-user-1")
    await create_and_launch_experiment(
        client, auth_headers, "decide_sticky_flag", "Sticky Test"
    )

    results = []
    for _ in range(3):
        r = await client.post(
            "/decide",
            json={
                "subject_id": "sticky-user-1",
                "flag_keys": ["decide_sticky_flag"],
                "attributes": {},
            },
        )
        assert r.status_code == 200
        results.append(
            r.json()["decisions"]["decide_sticky_flag"]["variant_name"]
        )

    assert len(set(results)) == 1, f"Sticky assignment failed, got: {results}"


async def test_decide_unknown_flag_returns_empty(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_subject_user(client, auth_headers, "e2e-user-alice")
    r = await client.post(
        "/decide",
        json={
            "subject_id": "e2e-user-alice",
            "flag_keys": ["totally_unknown_flag_xyz"],
            "attributes": {},
        },
    )
    assert r.status_code == 404, r.text
