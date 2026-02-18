from __future__ import annotations

from src.application.dto.events import SendEventsRequest
from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.application.ports.event_id_generator import EventIdGeneratorPort
from src.application.ports.event_types_repository import (
    EventTypesRepositoryPort,
)
from src.application.ports.event_validator import EventValidatorPort
from src.application.ports.events_repository import EventsRepositoryPort
from src.application.ports.pending_events_store import (
    PendingEventsStorePort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.value_objects.event_processing import (
    EventProcessingError,
    EventsBatchResult,
)


# Ключ типа события «экспозиция» — факт показа варианта пользователю
EXPOSURE_EVENT_TYPE_KEY = "exposure"


class SendEventsUseCase:
    def __init__(
        self,
        events_repository: EventsRepositoryPort,
        event_types_repository: EventTypesRepositoryPort,
        decisions_repository: DecisionsRepositoryPort,
        event_id_generator: EventIdGeneratorPort,
        event_validator: EventValidatorPort,
        pending_events_store: PendingEventsStorePort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._events_repository = events_repository
        self._event_types_repository = event_types_repository
        self._decisions_repository = decisions_repository
        self._event_id_generator = event_id_generator
        self._event_validator = event_validator
        self._pending_store = pending_events_store
        self._uow = uow

    async def execute(self, data: SendEventsRequest) -> EventsBatchResult:
        accepted = 0
        duplicates = 0
        rejected = 0
        errors: list[EventProcessingError] = []

        for idx, event_data in enumerate(data.events):
            result = await self._process_single_event(idx, event_data)
            if result is None:
                # Дубликат
                duplicates += 1
            elif isinstance(result, EventProcessingError):
                rejected += 1
                errors.append(result)
            else:
                accepted += 1

        return EventsBatchResult.build(
            accepted=accepted,
            duplicates=duplicates,
            rejected=rejected,
            errors=errors,
        )

    async def _process_single_event(
        self, idx: int, event_data
    ) -> Event | EventProcessingError | None:
        """Обработать одно событие.

        Returns:
            Event — успешно принято,
            EventProcessingError — отклонено с причиной,
            None — дубликат.
        """
        # 1. Проверяем существование типа события
        event_type = await self._event_types_repository.get_by_key(
            event_data.event_type_key
        )
        if event_type is None:
            return EventProcessingError(
                index=idx,
                event_type_key=event_data.event_type_key,
                reason=f"Event type not found: {event_data.event_type_key}",
            )

        # 2. Валидация обязательных параметров через EventValidatorPort
        #    (B4-1, B4-2: типы и обязательные поля)
        validation = self._event_validator.validate(
            required_params=event_type.required_params,
            props=event_data.props,
        )
        if not validation.success:
            reasons = "; ".join(
                f"{e.field}: {e.message}" for e in validation.errors
            )
            return EventProcessingError(
                index=idx,
                event_type_key=event_data.event_type_key,
                reason=reasons,
            )

        # 3. Проверяем существование decision_id (B4-4)
        decision = await self._decisions_repository.get_by_id(
            event_data.decision_id
        )
        if decision is None:
            return EventProcessingError(
                index=idx,
                event_type_key=event_data.event_type_key,
                reason=f"Decision not found: {event_data.decision_id}",
            )

        # 4. Генерируем детерминированный ID события
        event_id = self._event_id_generator.generate(
            event_type_key=event_data.event_type_key,
            decision_id=event_data.decision_id,
            subject_id=event_data.subject_id,
            timestamp=event_data.timestamp,
            props=event_data.props,
        )

        # 5. Дедупликация: проверяем в БД и в pending-хранилище (B4-3)
        if await self._events_repository.exists(event_id):
            return None
        if await self._pending_store.exists(str(event_id)):
            return None

        # Используем нормализованные props из валидатора
        normalized_props = validation.normalized_props or event_data.props

        is_exposure = event_data.event_type_key == EXPOSURE_EVENT_TYPE_KEY

        if is_exposure:
            # Exposure сохраняется в БД сразу со статусом ATTRIBUTED
            event = Event(
                id=event_id,
                event_type_key=event_data.event_type_key,
                decision_id=event_data.decision_id,
                subject_id=event_data.subject_id,
                timestamp=event_data.timestamp,
                props=normalized_props,
                attribution_status=AttributionStatus.ATTRIBUTED,
            )
            async with self._uow:
                await self._events_repository.save(event)
                # Переносим все pending-события этого decision_id → ATTRIBUTED
                await self._attribute_pending_events(event_data.decision_id)
            return event

        if event_type.requires_exposure:
            # Exposure мог прийти раньше этого события (out-of-order delivery).
            # Проверяем БД: если exposure уже есть — атрибутируем сразу,
            # иначе кладём в Redis и ждём его прихода (или TTL → REJECTED).
            exposure_events = (
                await self._events_repository.get_exposure_by_decision_id(
                    event_data.decision_id
                )
            )
            if exposure_events:
                event = Event(
                    id=event_id,
                    event_type_key=event_data.event_type_key,
                    decision_id=event_data.decision_id,
                    subject_id=event_data.subject_id,
                    timestamp=event_data.timestamp,
                    props=normalized_props,
                    attribution_status=AttributionStatus.ATTRIBUTED,
                )
                async with self._uow:
                    await self._events_repository.save(event)
            else:
                event = Event(
                    id=event_id,
                    event_type_key=event_data.event_type_key,
                    decision_id=event_data.decision_id,
                    subject_id=event_data.subject_id,
                    timestamp=event_data.timestamp,
                    props=normalized_props,
                    attribution_status=AttributionStatus.PENDING,
                )
                await self._pending_store.put(event)
            return event

        # Не требует exposure → сразу в БД со статусом ATTRIBUTED
        event = Event(
            id=event_id,
            event_type_key=event_data.event_type_key,
            decision_id=event_data.decision_id,
            subject_id=event_data.subject_id,
            timestamp=event_data.timestamp,
            props=normalized_props,
            attribution_status=AttributionStatus.ATTRIBUTED,
        )
        async with self._uow:
            await self._events_repository.save(event)
        return event

    async def _attribute_pending_events(self, decision_id: str) -> None:
        pending_events = await self._pending_store.get_by_decision_id(
            decision_id
        )
        if not pending_events:
            return

        for event in pending_events:
            event.mark_as_attributed()
            await self._events_repository.save(event)

        await self._pending_store.delete_by_event_ids(
            [str(e.id) for e in pending_events]
        )
