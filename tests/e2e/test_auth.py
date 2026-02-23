from __future__ import annotations

import pytest

from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_register_and_login(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/register",
        json={
            "email": "auth_test_1@example.com",
            "password": "secure_pass_123",
            "role": "experimenter",
        },
    )
    assert r.status_code == 201, r.text
    login = await client.post(
        "/auth/login",
        json={
            "email": "auth_test_1@example.com",
            "password": "secure_pass_123",
        },
    )
    assert login.status_code == 200, login.text
    assert "access_token" in login.json()


async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "auth_dup@example.com",
        "password": "pass1234",
        "role": "viewer",
    }
    r1 = await client.post("/auth/register", json=payload)
    assert r1.status_code in (201, 400), r1.text

    r2 = await client.post("/auth/register", json=payload)
    assert r2.status_code == 400, r2.text


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={
            "email": "wrongpass@example.com",
            "password": "correct",
            "role": "viewer",
        },
    )
    r = await client.post(
        "/auth/login",
        json={"email": "wrongpass@example.com", "password": "wrong_password"},
    )
    assert r.status_code == 401, r.text


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    r = await client.post(
        "/auth/login",
        json={"email": "nobody@nowhere.com", "password": "pass"},
    )
    assert r.status_code == 401, r.text


async def test_protected_route_without_token(client: AsyncClient) -> None:
    r = await client.get("/experiments")
    assert r.status_code == 401, r.text


async def test_protected_route_with_invalid_token(client: AsyncClient) -> None:
    r = await client.get(
        "/experiments",
        headers={"Authorization": "Bearer not_a_real_token"},
    )
    assert r.status_code == 401, r.text
