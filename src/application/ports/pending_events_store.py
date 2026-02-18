from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.aggregates.event import Event


class PendingEventsStorePort(ABC):
    @abstractmethod
    async def put(
        self,
        event: Event,
        ttl_seconds: int = 7 * 24 * 3600,
    ) -> None:
        """Сохранить событие как pending.

        Args:
            event: Доменное событие.
            ttl_seconds: Время жизни ключа в секундах (по умолчанию 7 дней).
        """
        raise NotImplementedError

    @abstractmethod
    async def exists(self, event_id: str) -> bool:
        """Проверить наличие pending-события по его ID.

        Args:
            event_id: ID события.

        Returns:
            True если событие есть в pending-хранилище.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_decision_id(self, decision_id: str) -> list[Event]:
        """Получить все pending-события для данного decision_id.

        Args:
            decision_id: ID решения.

        Returns:
            Список pending-событий.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete_by_event_ids(self, event_ids: list[str]) -> None:
        """Удалить pending-события по их ID.

        Args:
            event_ids: Список ID событий для удаления.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_by_event_id(self, event_id: str) -> Event | None:
        """Получить pending-событие по его ID без удаления.

        Используется TTL-листенером: при срабатывании keyspace notification
        по expired-ключу читаем данные события и переносим в БД как REJECTED.

        Args:
            event_id: ID события.

        Returns:
            Доменное событие или None если уже удалено.
        """
        raise NotImplementedError
