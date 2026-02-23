import pytest

from httpx import AsyncClient

from tests.e2e.helpers import ensure_feature_flag


pytestmark = pytest.mark.asyncio


async def test_versions_created_after_update(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "ver_flag_1", default_value="a"
    )
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "ver_flag_1",
            "name": "Version Test 1",
            "audience_fraction": 0.5,
            "variants": [
                {
                    "name": "ctrl",
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
    assert r.status_code == 201, r.text
    exp_id = r.json()["id"]

    patch_r = await client.patch(
        f"/experiments/{exp_id}",
        json={"name": "Version Test 1 Updated"},
        headers=auth_headers,
    )
    assert patch_r.status_code == 200, patch_r.text
    new_version = patch_r.json()["version"]

    ver_r = await client.get(
        f"/experiments/{exp_id}/versions", headers=auth_headers
    )
    assert ver_r.status_code == 200, ver_r.text
    versions = ver_r.json()
    assert isinstance(versions, list)
    assert len(versions) >= 1

    version_numbers = [v["version"] for v in versions]
    assert new_version in version_numbers


async def test_get_specific_version(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "ver_flag_2", default_value="x"
    )
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "ver_flag_2",
            "name": "Version Specific Test",
            "audience_fraction": 0.5,
            "variants": [
                {"name": "c", "value": "x", "weight": 0.1, "is_control": True},
                {"name": "t", "value": "y", "weight": 0.4, "is_control": False},
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]

    await client.patch(
        f"/experiments/{exp_id}",
        json={"name": "Version Specific Updated"},
        headers=auth_headers,
    )

    ver_r = await client.get(
        f"/experiments/{exp_id}/versions", headers=auth_headers
    )
    versions = ver_r.json()
    v_num = versions[0]["version"]

    single_r = await client.get(
        f"/experiments/{exp_id}/versions/{v_num}", headers=auth_headers
    )
    assert single_r.status_code == 200, single_r.text
    data = single_r.json()
    assert data["version"] == v_num
    assert "snapshot" in data
    assert "changed_at" in data


async def test_get_nonexistent_version_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "ver_flag_3", default_value="v"
    )
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "ver_flag_3",
            "name": "Ver 404 Test",
            "audience_fraction": 0.5,
            "variants": [
                {"name": "c", "value": "v", "weight": 0.4, "is_control": True},
                {"name": "t", "value": "w", "weight": 0.1, "is_control": False},
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]

    r2 = await client.get(
        f"/experiments/{exp_id}/versions/999", headers=auth_headers
    )
    assert r2.status_code == 404, r2.text


async def test_versions_unauthenticated(client: AsyncClient) -> None:
    r = await client.get(
        "/experiments/00000000-0000-0000-0000-000000000001/versions"
    )
    assert r.status_code == 401, r.text


async def test_snapshot_contains_experiment_data(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "ver_snapshot_flag", default_value="a"
    )
    r = await client.post(
        "/experiments",
        json={
            "flag_key": "ver_snapshot_flag",
            "name": "Snapshot Test",
            "audience_fraction": 0.75,
            "variants": [
                {
                    "name": "ctrl",
                    "value": "a",
                    "weight": 0.5,
                    "is_control": True,
                },
                {
                    "name": "treat",
                    "value": "b",
                    "weight": 0.25,
                    "is_control": False,
                },
            ],
        },
        headers=auth_headers,
    )
    exp_id = r.json()["id"]

    await client.patch(
        f"/experiments/{exp_id}",
        json={"audience_fraction": 0.75},
        headers=auth_headers,
    )

    ver_r = await client.get(
        f"/experiments/{exp_id}/versions", headers=auth_headers
    )
    versions = ver_r.json()
    assert len(versions) >= 1

    latest = sorted(versions, key=lambda v: v["version"])[-1]
    snap = latest["snapshot"]
    assert "name" in snap
    assert "variants" in snap
    assert "audience_fraction" in snap
    assert snap["audience_fraction"] == 0.75
