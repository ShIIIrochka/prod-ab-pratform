from __future__ import annotations

import pytest

from httpx import AsyncClient

from tests.e2e.helpers import ensure_feature_flag


pytestmark = pytest.mark.asyncio


async def test_create_feature_flag(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/feature-flags",
        json={
            "key": "new_feature_flag",
            "value_type": "string",
            "default_value": "blue",
        },
        headers=auth_headers,
    )
    data = r.json()
    assert r.status_code == 201, r.text

    assert data["key"] == "new_feature_flag"
    assert data["default_value"] == "blue"


async def test_create_duplicate_flag_returns_400(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "ff_dup_key")
    r = await client.post(
        "/feature-flags",
        json={
            "key": "ff_dup_key",
            "value_type": "string",
            "default_value": "v",
        },
        headers=auth_headers,
    )
    assert r.status_code == 400, r.text


async def test_list_feature_flags(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "ff_list_1")
    r = await client.get("/feature-flags", headers=auth_headers)
    assert r.status_code == 200, r.text
    flags = r.json().get("flags")
    assert isinstance(flags, list)
    keys = [f["key"] for f in flags]
    assert "ff_list_1" in keys


async def test_get_feature_flag(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(client, auth_headers, "ff_get_test")
    r = await client.get("/feature-flags/ff_get_test", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert r.json()["key"] == "ff_get_test"


async def test_get_nonexistent_flag_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.get(
        "/feature-flags/nonexistent_flag_xyz", headers=auth_headers
    )
    assert r.status_code == 404, r.text


async def test_update_flag_default_value(
    client: AsyncClient, auth_headers: dict
) -> None:
    await ensure_feature_flag(
        client, auth_headers, "ff_update_test", default_value="old"
    )
    r = await client.patch(
        "/feature-flags/ff_update_test",
        json={"default_value": "new"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    assert r.json()["default_value"] == "new"


async def test_create_flag_bool_type(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/feature-flags",
        json={
            "key": "ff_bool_test",
            "value_type": "bool",
            "default_value": False,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["value_type"] == "bool"
