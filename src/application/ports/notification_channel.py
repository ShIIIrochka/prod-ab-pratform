from abc import ABC, abstractmethod


class NotificationChannelPort(ABC):
    @abstractmethod
    async def send(self, message: str, webhook_url: str) -> None: ...
