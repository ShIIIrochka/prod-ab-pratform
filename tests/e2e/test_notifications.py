"""E2E tests for /notifications routes."""

from __future__ import annotations

import pytest

from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_create_channel_config(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/notifications/channel-configs",
        json={
            "type": "slack",
            "name": "Test Slack Channel",
            "webhook_url": "https://hooks.slack.com/test",
            "enabled": True,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["type"] == "slack"
    assert data["name"] == "Test Slack Channel"
    assert "id" in data


async def test_list_channel_configs(
    client: AsyncClient, auth_headers: dict
) -> None:
    await client.post(
        "/notifications/channel-configs",
        json={
            "type": "telegram",
            "name": "TG Test",
            "webhook_url": "https://t.me/test",
        },
        headers=auth_headers,
    )
    r = await client.get("/notifications/channel-configs", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


async def test_list_channel_configs_enabled_only(
    client: AsyncClient, auth_headers: dict
) -> None:
    await client.post(
        "/notifications/channel-configs",
        json={
            "type": "slack",
            "name": "Enabled",
            "webhook_url": "https://hooks.slack.com/1",
            "enabled": True,
        },
        headers=auth_headers,
    )
    await client.post(
        "/notifications/channel-configs",
        json={
            "type": "slack",
            "name": "Disabled",
            "webhook_url": "https://hooks.slack.com/2",
            "enabled": False,
        },
        headers=auth_headers,
    )
    r = await client.get(
        "/notifications/channel-configs",
        params={"enabled_only": True},
        headers=auth_headers,
    )
    assert r.status_code == 200
    for cfg in r.json():
        assert cfg["enabled"] is True


async def test_create_notification_rule(
    client: AsyncClient, auth_headers: dict
) -> None:
    cfg_r = await client.post(
        "/notifications/channel-configs",
        json={
            "type": "slack",
            "name": "Rule Test Channel",
            "webhook_url": "https://hooks.slack.com/rule-test",
        },
        headers=auth_headers,
    )
    cfg_id = cfg_r.json()["id"]

    r = await client.post(
        "/notifications/rules",
        json={
            "event_type": "experiment.launched",
            "channel_config_id": cfg_id,
            "enabled": True,
            "rate_limit_seconds": 300,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["event_type"] == "experiment.launched"
    assert data["channel_config_id"] == cfg_id
    assert data["rate_limit_seconds"] == 300


async def test_create_rule_invalid_channel_config_returns_error(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/notifications/rules",
        json={
            "event_type": "experiment.launched",
            "channel_config_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=auth_headers,
    )
    assert r.status_code in (400, 422), r.text


async def test_list_notification_rules(
    client: AsyncClient, auth_headers: dict
) -> None:
    cfg_r = await client.post(
        "/notifications/channel-configs",
        json={
            "type": "slack",
            "name": "List Rules Channel",
            "webhook_url": "https://hooks.slack.com/list-rules",
        },
        headers=auth_headers,
    )
    cfg_id = cfg_r.json()["id"]
    await client.post(
        "/notifications/rules",
        json={"event_type": "guardrail.triggered", "channel_config_id": cfg_id},
        headers=auth_headers,
    )
    r = await client.get("/notifications/rules", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


async def test_update_notification_rule(
    client: AsyncClient, auth_headers: dict
) -> None:
    cfg_r = await client.post(
        "/notifications/channel-configs",
        json={
            "type": "slack",
            "name": "Update Rule Channel",
            "webhook_url": "https://hooks.slack.com/upd",
        },
        headers=auth_headers,
    )
    cfg_id = cfg_r.json()["id"]
    rule_r = await client.post(
        "/notifications/rules",
        json={
            "event_type": "experiment.paused",
            "channel_config_id": cfg_id,
            "rate_limit_seconds": 0,
        },
        headers=auth_headers,
    )
    rule_id = rule_r.json()["id"]

    r = await client.patch(
        f"/notifications/rules/{rule_id}",
        json={"enabled": False, "rate_limit_seconds": 600},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["enabled"] is False
    assert data["rate_limit_seconds"] == 600


async def test_list_deliveries(client: AsyncClient, auth_headers: dict) -> None:
    r = await client.get("/notifications/deliveries", headers=auth_headers)
    assert r.status_code == 200, r.text
    assert isinstance(r.json(), list)


async def test_list_deliveries_unauthenticated(client: AsyncClient) -> None:
    r = await client.get("/notifications/deliveries")
    assert r.status_code == 401, r.text


async def test_create_channel_config_unauthenticated(
    client: AsyncClient,
) -> None:
    r = await client.post(
        "/notifications/channel-configs",
        json={
            "type": "slack",
            "name": "NoAuth",
            "webhook_url": "https://x.com",
        },
    )
    assert r.status_code == 401, r.text


# ── Connect / Disconnect routes ───────────────────────────────────────────────


async def test_connect_telegram(
    client: AsyncClient, auth_headers: dict
) -> None:
    r = await client.post(
        "/notifications/telegram/connect",
        json={
            "name": "Team Telegram",
            "bot_token": "123456:ABC-DEF",
            "chat_id": "-1001234567890",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["type"] == "telegram"
    assert data["name"] == "Team Telegram"
    assert "id" in data
    assert "bot***" in data["webhook_url"] or "***" in data["webhook_url"]
    assert "123456:ABC-DEF" not in data["webhook_url"]


async def test_connect_slack(client: AsyncClient, auth_headers: dict) -> None:
    r = await client.post(
        "/notifications/slack/connect",
        json={
            "name": "Team Slack",
            "webhook_url": "https://hooks.slack.com/services/T00/B00/xxx",
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["type"] == "slack"
    assert data["name"] == "Team Slack"
    assert "id" in data
    assert "xxx" not in data["webhook_url"]


async def test_disconnect_telegram(
    client: AsyncClient, auth_headers: dict
) -> None:
    connect_r = await client.post(
        "/notifications/telegram/connect",
        json={
            "name": "TG to disconnect",
            "bot_token": "token",
            "chat_id": "123",
        },
        headers=auth_headers,
    )
    assert connect_r.status_code == 201
    config_id = connect_r.json()["id"]

    r = await client.delete(
        f"/notifications/telegram/{config_id}",
        headers=auth_headers,
    )
    assert r.status_code == 204, r.text

    list_r = await client.get(
        "/notifications/channel-configs",
        headers=auth_headers,
    )
    assert list_r.status_code == 200
    ids = [c["id"] for c in list_r.json()]
    assert config_id not in ids


async def test_disconnect_slack(
    client: AsyncClient, auth_headers: dict
) -> None:
    connect_r = await client.post(
        "/notifications/slack/connect",
        json={
            "name": "Slack to disconnect",
            "webhook_url": "https://hooks.slack.com/services/a/b/c",
        },
        headers=auth_headers,
    )
    assert connect_r.status_code == 201
    config_id = connect_r.json()["id"]

    r = await client.delete(
        f"/notifications/slack/{config_id}",
        headers=auth_headers,
    )
    assert r.status_code == 204, r.text

    list_r = await client.get(
        "/notifications/channel-configs",
        headers=auth_headers,
    )
    assert list_r.status_code == 200
    ids = [c["id"] for c in list_r.json()]
    assert config_id not in ids


async def test_disconnect_telegram_with_slack_config_returns_404(
    client: AsyncClient, auth_headers: dict
) -> None:
    connect_r = await client.post(
        "/notifications/slack/connect",
        json={
            "name": "Slack config",
            "webhook_url": "https://hooks.slack.com/services/x/y/z",
        },
        headers=auth_headers,
    )
    assert connect_r.status_code == 201
    slack_config_id = connect_r.json()["id"]

    r = await client.delete(
        f"/notifications/telegram/{slack_config_id}",
        headers=auth_headers,
    )
    assert r.status_code == 404, r.text
