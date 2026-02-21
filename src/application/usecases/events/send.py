from __future__ import annotations

import logging

from uuid import UUID

from src.application.dto.events import SendEventsRequest
from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.application.ports.event_id_generator import EventIdGeneratorPort
from src.application.ports.event_types_repository import (
    EventTypesRepositoryPort,
)
from src.application.ports.event_validator import EventValidatorPort
from src.application.ports.events_repository import EventsRepositoryPort
from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.application.ports.metric_aggregator import MetricAggregatorPort
from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.application.ports.pending_events_store import (
    PendingEventsStorePort,
)
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.decision import Decision
from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.aggregates.metric import Metric
from src.domain.value_objects.event_processing import (
    EventProcessingError,
    EventsBatchResult,
)


logger = logging.getLogger(__name__)

EXPOSURE_EVENT_TYPE_KEY = "exposure"

# TTL для Redis-агрегатов: максимальное окно наблюдения (1 час запаса)
_METRIC_AGGREGATOR_TTL_SECONDS = 3600


class SendEventsUseCase:
    def __init__(
        self,
        events_repository: EventsRepositoryPort,
        event_types_repository: EventTypesRepositoryPort,
        decisions_repository: DecisionsRepositoryPort,
        event_id_generator: EventIdGeneratorPort,
        event_validator: EventValidatorPort,
        pending_events_store: PendingEventsStorePort,
        guardrail_configs_repository: GuardrailConfigsRepositoryPort,
        metrics_repository: MetricsRepositoryPort,
        metric_aggregator: MetricAggregatorPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._events_repository = events_repository
        self._event_types_repository = event_types_repository
        self._decisions_repository = decisions_repository
        self._event_id_generator = event_id_generator
        self._event_validator = event_validator
        self._pending_store = pending_events_store
        self._guardrail_configs_repository = guardrail_configs_repository
        self._metrics_repository = metrics_repository
        self._metric_aggregator = metric_aggregator
        self._uow = uow

    async def execute(self, data: SendEventsRequest) -> EventsBatchResult:
        accepted = 0
        duplicates = 0
        rejected = 0
        errors: list[EventProcessingError] = []

        for idx, event_data in enumerate(data.events):
            result = await self._process_single_event(idx, event_data)
            if result is None:
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

        # 2. Валидация обязательных параметров (B4-1, B4-2)
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

        # Проверяем существование decision_id
        try:
            decision_uuid = UUID(event_data.decision_id)
        except ValueError:
            return EventProcessingError(
                index=idx,
                event_type_key=event_data.event_type_key,
                reason=f"Invalid decision_id format: {event_data.decision_id}",
            )
        decision = await self._decisions_repository.get_by_id(decision_uuid)
        if decision is None:
            return EventProcessingError(
                index=idx,
                event_type_key=event_data.event_type_key,
                reason=f"Decision not found: {event_data.decision_id}",
            )

        subject_id = decision.subject_id

        # Генерируем детерминированный ID события
        event_id = self._event_id_generator.generate(
            event_type_key=event_data.event_type_key,
            decision_id=event_data.decision_id,
            subject_id=subject_id,
            timestamp=event_data.timestamp,
            props=event_data.props,
        )

        # Дедупликация
        if await self._events_repository.exists(event_id):
            return None
        if await self._pending_store.exists(str(event_id)):
            return None

        normalized_props = validation.normalized_props or event_data.props
        is_exposure = event_data.event_type_key == EXPOSURE_EVENT_TYPE_KEY

        if is_exposure:
            event = Event(
                id=event_id,
                event_type_key=event_data.event_type_key,
                decision_id=event_data.decision_id,
                subject_id=subject_id,
                timestamp=event_data.timestamp,
                props=normalized_props,
                attribution_status=AttributionStatus.ATTRIBUTED,
            )
            async with self._uow:
                await self._events_repository.save(event)
                await self._attribute_pending_events(
                    event_data.decision_id, decision
                )

            await self._update_metric_aggregates(event, decision)
            return event

        if event_type.requires_exposure:
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
                    subject_id=subject_id,
                    timestamp=event_data.timestamp,
                    props=normalized_props,
                    attribution_status=AttributionStatus.ATTRIBUTED,
                )
                async with self._uow:
                    await self._events_repository.save(event)
                await self._update_metric_aggregates(event, decision)
            else:
                event = Event(
                    id=event_id,
                    event_type_key=event_data.event_type_key,
                    decision_id=event_data.decision_id,
                    subject_id=subject_id,
                    timestamp=event_data.timestamp,
                    props=normalized_props,
                    attribution_status=AttributionStatus.PENDING,
                )
                await self._pending_store.put(event)
            return event

        # Не требует exposure -> сразу в БД со статусом ATTRIBUTED
        event = Event(
            id=event_id,
            event_type_key=event_data.event_type_key,
            decision_id=event_data.decision_id,
            subject_id=subject_id,
            timestamp=event_data.timestamp,
            props=normalized_props,
            attribution_status=AttributionStatus.ATTRIBUTED,
        )
        async with self._uow:
            await self._events_repository.save(event)
        await self._update_metric_aggregates(event, decision)
        return event

    async def _attribute_pending_events(
        self, decision_id: str, decision: Decision
    ) -> None:
        pending_events = await self._pending_store.get_by_decision_id(
            decision_id
        )
        if not pending_events:
            return

        for event in pending_events:
            event.mark_as_attributed()
            await self._events_repository.save(event)
            await self._update_metric_aggregates(event, decision)

        await self._pending_store.delete_by_event_ids(
            [str(e.id) for e in pending_events]
        )

    async def _update_metric_aggregates(
        self, event: Event, decision: Decision
    ) -> None:
        """Обновить Redis-агрегаты при сохранении ATTRIBUTED-события.

        Вызывается только для экспериментальных решений (где есть experiment_id).
        Загружает guardrail-метрики эксперимента и передаёт событие агрегатору.
        """
        if not decision.experiment_id:
            return

        try:
            configs = (
                await self._guardrail_configs_repository.get_by_experiment_id(
                    decision.experiment_id
                )
            )
            if not configs:
                return

            # Batch-load guardrail metrics in a single query
            unique_metric_keys = list({c.metric_key for c in configs})
            metrics_map = await self._metrics_repository.get_by_keys(
                unique_metric_keys
            )
            metrics: list[Metric] = list(metrics_map.values())

            if not metrics:
                return

            max_window = max(c.observation_window_minutes for c in configs)
            # TTL = max observation window * 60 + 2-minute buffer
            ttl = max_window * 60 + 120

            await self._metric_aggregator.update(
                experiment_id=decision.experiment_id,
                event=event,
                metrics=metrics,
                max_ttl_seconds=ttl,
            )
        except Exception as exc:
            # Не блокируем основной поток при ошибке агрегации
            logger.warning(
                "Failed to update metric aggregates for experiment %s: %s",
                decision.experiment_id,
                exc,
            )
