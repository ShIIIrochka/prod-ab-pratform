from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.domain.entities.notification_channel_config import (
    NotificationChannelConfig,
    new_notification_channel_config,
)
from src.domain.value_objects.notification_channel_type import (
    NotificationChannelType,
)


def _build_telegram_webhook_url(bot_token: str, chat_id: str) -> str:
    return (
        f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}"
    )


class ConnectTelegramUseCase:
    def __init__(
        self, repository: NotificationChannelConfigsRepositoryPort
    ) -> None:
        self._repository = repository

    async def execute(
        self,
        name: str,
        bot_token: str,
        chat_id: str,
    ) -> NotificationChannelConfig:
        webhook_url = _build_telegram_webhook_url(bot_token, chat_id)
        config = new_notification_channel_config(
            type=NotificationChannelType.TELEGRAM,
            name=name,
            webhook_url=webhook_url,
            enabled=True,
        )
        await self._repository.save(config)
        return config
