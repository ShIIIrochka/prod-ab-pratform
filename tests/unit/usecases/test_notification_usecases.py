"""Unit tests for notification usecases: channel configs, rules, deliveries."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.usecases.notifications.create_channel_config import (
    CreateChannelConfigUseCase,
)
from src.application.usecases.notifications.create_rule import (
    CreateNotificationRuleUseCase,
)
from src.application.usecases.notifications.list_channel_configs import (
    ListChannelConfigsUseCase,
)
from src.application.usecases.notifications.update_rule import (
    UpdateNotificationRuleUseCase,
)
from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
    new_notification_channel_config,
)
from src.domain.entities.notification_rule import new_notification_rule
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)
from tests.fakes.notification_rules_repository import (
    FakeNotificationRulesRepository,
)


pytestmark = pytest.mark.asyncio


# ── Minimal in-memory channel configs repo for tests ─────────────────────────


class FakeChannelConfigsRepository:
    def __init__(self) -> None:
        self._store: dict = {}

    async def save(self, config) -> None:
        self._store[config.id] = config

    async def get_by_id(self, config_id) -> NotificationChannelConfig | None:
        return self._store.get(config_id)

    async def list_all(self, enabled_only: bool = False):
        configs = list(self._store.values())
        if enabled_only:
            configs = [c for c in configs if c.enabled]
        return configs

    async def delete(self, config_id) -> None:
        self._store.pop(config_id, None)


# ── CreateChannelConfigUseCase ────────────────────────────────────────────────


async def test_create_channel_config() -> None:
    repo = FakeChannelConfigsRepository()
    uc = CreateChannelConfigUseCase(repository=repo)

    config = await uc.execute(
        type=NotificationChannelType.SLACK,
        name="My Slack",
        webhook_url="https://hooks.slack.com/test",
    )

    assert config.type == NotificationChannelType.SLACK
    assert config.name == "My Slack"
    assert config.webhook_url == "https://hooks.slack.com/test"
    assert config.enabled is True

    saved = await repo.get_by_id(config.id)
    assert saved is not None


async def test_create_telegram_channel_config() -> None:
    repo = FakeChannelConfigsRepository()
    uc = CreateChannelConfigUseCase(repository=repo)

    config = await uc.execute(
        type=NotificationChannelType.TELEGRAM,
        name="My TG",
        webhook_url="https://api.telegram.org/bot/sendMessage",
        enabled=False,
    )
    assert config.type == NotificationChannelType.TELEGRAM
    assert config.enabled is False


async def test_list_channel_configs_empty() -> None:
    repo = FakeChannelConfigsRepository()
    uc = ListChannelConfigsUseCase(repository=repo)
    result = await uc.execute()
    assert result == []


async def test_list_channel_configs_enabled_only() -> None:
    repo = FakeChannelConfigsRepository()
    create_uc = CreateChannelConfigUseCase(repository=repo)
    await create_uc.execute(
        NotificationChannelType.SLACK, "Active", "https://x.com/1", enabled=True
    )
    await create_uc.execute(
        NotificationChannelType.SLACK,
        "Inactive",
        "https://x.com/2",
        enabled=False,
    )

    list_uc = ListChannelConfigsUseCase(repository=repo)
    enabled = await list_uc.execute(enabled_only=True)
    assert len(enabled) == 1
    assert enabled[0].name == "Active"


# ── CreateNotificationRuleUseCase ─────────────────────────────────────────────


async def test_create_rule_valid_channel() -> None:
    cfg_repo = FakeChannelConfigsRepository()
    config = new_notification_channel_config(
        type=NotificationChannelType.SLACK,
        name="Slack",
        webhook_url="https://x.com",
    )
    await cfg_repo.save(config)

    rules_repo = FakeNotificationRulesRepository()
    uc = CreateNotificationRuleUseCase(
        rules_repository=rules_repo,
        channel_configs_repository=cfg_repo,
    )
    rule = await uc.execute(
        event_type="experiment.launched",
        channel_config_id=config.id,
        rate_limit_seconds=300,
    )

    assert rule.event_type == "experiment.launched"
    assert rule.channel_config_id == config.id
    assert rule.rate_limit_seconds == 300


async def test_create_rule_invalid_channel_raises() -> None:
    cfg_repo = FakeChannelConfigsRepository()
    rules_repo = FakeNotificationRulesRepository()
    uc = CreateNotificationRuleUseCase(
        rules_repository=rules_repo,
        channel_configs_repository=cfg_repo,
    )
    with pytest.raises(ValueError, match="not found"):
        await uc.execute(
            event_type="experiment.launched",
            channel_config_id=uuid4(),  # nonexistent
        )


# ── UpdateNotificationRuleUseCase ─────────────────────────────────────────────


async def test_update_rule_enabled_flag() -> None:
    rules_repo = FakeNotificationRulesRepository()
    rule = new_notification_rule(
        event_type="experiment.paused",
        channel_config_id=uuid4(),
        enabled=True,
    )
    await rules_repo.save(rule)

    uc = UpdateNotificationRuleUseCase(repository=rules_repo)
    updated = await uc.execute(rule_id=rule.id, enabled=False)

    assert updated.enabled is False


async def test_update_rule_rate_limit() -> None:
    rules_repo = FakeNotificationRulesRepository()
    rule = new_notification_rule(
        event_type="guardrail.triggered",
        channel_config_id=uuid4(),
        rate_limit_seconds=0,
    )
    await rules_repo.save(rule)

    uc = UpdateNotificationRuleUseCase(repository=rules_repo)
    updated = await uc.execute(rule_id=rule.id, rate_limit_seconds=3600)

    assert updated.rate_limit_seconds == 3600


async def test_update_rule_not_found_raises() -> None:
    rules_repo = FakeNotificationRulesRepository()
    uc = UpdateNotificationRuleUseCase(repository=rules_repo)

    with pytest.raises(ValueError, match="not found"):
        await uc.execute(rule_id=uuid4(), enabled=False)
