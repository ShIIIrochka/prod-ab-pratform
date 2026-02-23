from uuid import UUID

from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.application.ports.notification_rules_repository import (
    NotificationRulesRepositoryPort,
)
from src.domain.entities.notification_rule import (
    NotificationRule,
    new_notification_rule,
)


class CreateNotificationRuleUseCase:
    def __init__(
        self,
        rules_repository: NotificationRulesRepositoryPort,
        channel_configs_repository: NotificationChannelConfigsRepositoryPort,
    ) -> None:
        self._rules_repository = rules_repository
        self._channel_configs_repository = channel_configs_repository

    async def execute(
        self,
        event_type: str,
        channel_config_id: UUID,
        enabled: bool = True,
        experiment_id: UUID | None = None,
        flag_key: str | None = None,
        owner_id: str | None = None,
        metric_key: str | None = None,
        severity: str | None = None,
        rate_limit_seconds: int = 0,
        template: str | None = None,
    ) -> NotificationRule:
        config = await self._channel_configs_repository.get_by_id(
            channel_config_id
        )
        if config is None:
            msg = f"Channel config {channel_config_id} not found"
            raise ValueError(msg)

        rule = new_notification_rule(
            event_type=event_type,
            channel_config_id=channel_config_id,
            enabled=enabled,
            experiment_id=experiment_id,
            flag_key=flag_key,
            owner_id=owner_id,
            metric_key=metric_key,
            severity=severity,
            rate_limit_seconds=rate_limit_seconds,
            template=template,
        )
        await self._rules_repository.save(rule)
        return rule
