"""E2E tests for experiment lifecycle routes."""

from __future__ import annotations

import pytest

from httpx import AsyncClient

from tests.e2e.helpers import (
    create_and_launch_experiment,
    ensure_event_type,
    ensure_feature_flag,
    ensure_metric,
)


pytestmark = pytest.mark.asyncio


async def test_create_experiment(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_lc_flag1")
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_lc_flag1",
            "name": "LC Test 1",
            "audience_fraction": 0.5,
            "variants": [
                {
                    "name": "control",
                    "value": "off",
                    "weight": 0.4,
                    "is_control": True,
                },
                {
                    "name": "treat",
                    "value": "on",
                    "weight": 0.1,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "draft"
    assert data["version"] == 1


async def test_create_experiment_missing_flag_returns_error(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "does_not_exist_xyz",
            "name": "Bad Experiment",
            "audience_fraction": 0.5,
            "variants": [
                {
                    "name": "control",
                    "value": "a",
                    "weight": 0.4,
                    "is_control": True,
                },
                {
                    "name": "treat",
                    "value": "b",
                    "weight": 0.1,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    assert r.status_code == 404, r.text


async def test_full_lifecycle_draft_to_running(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_full_lc_flag")
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_full_lc_flag",
            "name": "Full Lifecycle Test",
            "audience_fraction": 1.0,
            "variants": [
                {
                    "name": "ctrl",
                    "value": "v0",
                    "weight": 0.5,
                    "is_control": True,
                },
                {
                    "name": "treat",
                    "value": "v1",
                    "weight": 0.5,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    exp_id = r.json()["id"]

    # Send to review
    r = await client.post(
        f"/experiments/{exp_id}/send-to-review", headers=auth_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "on_review"

    # Approve
    r = await client.post(
        f"/experiments/{exp_id}/approve",
        json={"comment": "looks good"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "approved"

    # Launch
    r = await client.post(f"/experiments/{exp_id}/launch", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "running"


async def test_pause_running_experiment(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_pause_flag")
    exp_id = await create_and_launch_experiment(
        client, auth_headers, "exp_pause_flag", "Pause Test"
    )
    r = await client.post(f"/experiments/{exp_id}/pause", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "paused"


async def test_cannot_pause_draft_experiment(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_bad_pause_flag")
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_bad_pause_flag",
            "name": "Draft Pause Attempt",
            "audience_fraction": 0.5,
            "variants": [
                {"name": "c", "value": "a", "weight": 0.3, "is_control": True},
                {"name": "t", "value": "b", "weight": 0.2, "is_control": False},
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]
    r2 = await client.post(f"/experiments/{exp_id}/pause", headers=auth_headers)
    assert r2.status_code == 400, r2.text


async def test_complete_experiment(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_complete_flag")
    exp_id = await create_and_launch_experiment(
        client, auth_headers, "exp_complete_flag", "Complete Test"
    )
    r = await client.post(
        f"/experiments/{exp_id}/complete",
        json={
            "outcome": "rollout_winner",
            "winner_variant_id": "control",
            "comment": "Variant won.",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "completed"
    assert data["completion"]["outcome"] == "rollout_winner"
    assert isinstance(data["completion"]["completed_at"], int)


async def test_archive_experiment(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_archive_flag2")
    exp_id = await create_and_launch_experiment(
        client, auth_headers, "exp_archive_flag2", "Archive Test"
    )
    await client.post(
        f"/experiments/{exp_id}/complete",
        json={"outcome": "no_effect", "comment": "done"},
        headers=auth_headers,
    )
    r = await client.post(
        f"/experiments/{exp_id}/archive", headers=auth_headers
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "archived"


async def test_archive_twice_returns_400(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_archive_2x_flag")
    exp_id = await create_and_launch_experiment(
        client, auth_headers, "exp_archive_2x_flag", "Archive 2x"
    )
    await client.post(
        f"/experiments/{exp_id}/complete",
        json={"outcome": "no_effect", "comment": "done"},
        headers=auth_headers,
    )
    await client.post(f"/experiments/{exp_id}/archive", headers=auth_headers)
    r = await client.post(
        f"/experiments/{exp_id}/archive", headers=auth_headers
    )
    assert r.status_code == 400, r.text


async def test_request_changes_on_review(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_req_changes_flag")
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_req_changes_flag",
            "name": "Request Changes Test",
            "audience_fraction": 0.5,
            "variants": [
                {"name": "c", "value": "v0", "weight": 0.4, "is_control": True},
                {
                    "name": "t",
                    "value": "v1",
                    "weight": 0.1,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]
    await client.post(
        f"/experiments/{exp_id}/send-to-review", headers=auth_headers
    )
    r2 = await client.post(
        f"/experiments/{exp_id}/request-changes",
        json={"comment": "please fix"},
        headers=auth_headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "draft"


async def test_reject_experiment_on_review(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_reject_flag")
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_reject_flag",
            "name": "Reject Test",
            "audience_fraction": 0.5,
            "variants": [
                {"name": "c", "value": "v0", "weight": 0.1, "is_control": True},
                {
                    "name": "t",
                    "value": "v1",
                    "weight": 0.4,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]
    await client.post(
        f"/experiments/{exp_id}/send-to-review", headers=auth_headers
    )
    r2 = await client.post(
        f"/experiments/{exp_id}/reject",
        json={"comment": "not ready"},
        headers=auth_headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "rejected"


async def test_get_experiment(client: AsyncClient, auth_headers: dict) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_get_flag")
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_get_flag",
            "name": "Get Me",
            "audience_fraction": 1.0,
            "variants": [
                {"name": "c", "value": "a", "weight": 0.5, "is_control": True},
                {"name": "t", "value": "b", "weight": 0.5, "is_control": False},
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]
    r2 = await client.get(f"/experiments/{exp_id}", headers=auth_headers)
    assert r2.status_code == 200, r2.text
    assert r2.json()["id"] == exp_id


async def test_get_nonexistent_experiment_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.get(
        "/experiments/00000000-0000-0000-0000-000000000099",
        headers=auth_headers,
    )
    assert r.status_code == 404, r.text


async def test_list_experiments(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_list_flag")
    await client.post(
        "/experiments",
        json={
            "flag_key": "exp_list_flag",
            "name": "List Test",
            "audience_fraction": 0.5,
            "variants": [
                {
                    "name": "c",
                    "value": "x",
                    "weight": 0.4,
                    "is_control": True,
                },
                {
                    "name": "t",
                    "value": "y",
                    "weight": 0.1,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    r = await client.get("/experiments", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert isinstance(r.json().get("experiments"), list)


async def test_update_experiment_increments_version(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_update_flag")
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_update_flag",
            "name": "Update Test",
            "audience_fraction": 0.5,
            "variants": [
                {"name": "c", "value": "a", "weight": 0.4, "is_control": True},
                {"name": "t", "value": "b", "weight": 0.1, "is_control": False},
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]
    v_before = r.json()["version"]

    patch_r = await client.patch(
        f"/experiments/{exp_id}",
        json={"name": "Updated Name"},
        headers=auth_headers,
    )
    assert patch_r.status_code == 200, patch_r.text
    assert patch_r.json()["version"] == v_before + 1


async def test_experiment_with_guardrail_config(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "exp_guardrail_cfg_flag")
    await ensure_event_type(client, auth_headers, "exposure", "Exposure")
    await ensure_event_type(
        client, auth_headers, "conversion", "Conversion", requires_exposure=True
    )
    await ensure_metric(
        client,
        auth_headers,
        "cr_metric",
        "Conversion Rate",
        '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"conversion"},"denominator":{"type":"COUNT","event_type_key":"exposure"}}',
    )
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "exp_guardrail_cfg_flag",
            "name": "Guardrail Config Test",
            "audience_fraction": 1.0,
            "variants": [
                {"name": "c", "value": "a", "weight": 0.5, "is_control": True},
                {"name": "t", "value": "b", "weight": 0.5, "is_control": False},
            ],
            "guardrails": [
                {
                    "metric_key": "cr_metric",
                    "threshold": 0.05,
                    "observation_window_minutes": 30,
                    "action": "pause",
                }
            ],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert len(data["guardrails"]) == 1
    g = data["guardrails"][0]
    assert "id" in g and g["id"] is not None
    assert g["threshold"] == 0.05
