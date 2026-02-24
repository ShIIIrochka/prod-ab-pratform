from __future__ import annotations

import logging

from typing import Any

from pydantic import ValidationError

from src.application.dto.events import SendEventRequest, SendEventsRequest
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
from src.infra.observability.metrics import (
    events_received_total,
    events_rejected_total,
    experiment_exposures_total,
)


logger = logging.getLogger(__name__)

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

        batch_size = len(data.events)
        if batch_size:
            events_received_total.inc(batch_size)

        for idx, raw in enumerate(data.events):
            parsed = self._parse_event(idx, raw)
            if isinstance(parsed, EventProcessingError):
                rejected += 1
                errors.append(parsed)
                events_rejected_total.inc()
                continue

            result = await self._process_single_event(idx, parsed)
            if result is None:
                duplicates += 1
            elif isinstance(result, EventProcessingError):
                rejected += 1
                errors.append(result)
            else:
                accepted += 1

                if (
                    parsed.event_type_key == EXPOSURE_EVENT_TYPE_KEY
                    and result.decision_id is not None
                ):
                    experiment_id = (
                        result.decision_id  # will be resolved in repository
                    )
                    experiment_exposures_total.labels(
                        experiment_id=str(experiment_id),
                        variant=result.props.get("variant", "unknown"),
                    ).inc()

        return EventsBatchResult.build(
            accepted=accepted,
            duplicates=duplicates,
            rejected=rejected,
            errors=errors,
        )

    @staticmethod
    def _parse_event(
        idx: int, raw: Any
    ) -> SendEventRequest | EventProcessingError:
        """Попытаться разобрать один элемент батча в SendEventRequest."""
        try:
            return SendEventRequest.model_validate(raw)
        except ValidationError as exc:
            event_type_key = ""
            if isinstance(raw, dict):
                event_type_key = str(raw.get("event_type_key", ""))
            reasons = "; ".join(
                f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}"
                for err in exc.errors()
            )
            return EventProcessingError(
                index=idx,
                event_type_key=event_type_key,
                reason=reasons,
            )
        except Exception as exc:  # noqa: BLE001
            event_type_key = ""
            if isinstance(raw, dict):
                event_type_key = str(raw.get("event_type_key", ""))
            return EventProcessingError(
                index=idx,
                event_type_key=event_type_key,
                reason=str(exc),
            )

    async def _process_single_event(
        self, idx: int, event_data
    ) -> Event | EventProcessingError | None:
        event_type = await self._event_types_repository.get_by_key(
            event_data.event_type_key
        )
        if event_type is None:
            return EventProcessingError(
                index=idx,
                event_type_key=event_data.event_type_key,
                reason=f"Event type not found: {event_data.event_type_key}",
            )

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

        decision_id = event_data.decision_id  # UUID
        decision = await self._decisions_repository.get_by_id(decision_id)
        if decision is None:
            return EventProcessingError(
                index=idx,
                event_type_key=event_data.event_type_key,
                reason=f"Decision not found: {decision_id}",
            )

        subject_id = decision.subject_id

        event_id = self._event_id_generator.generate(
            event_type_key=event_data.event_type_key,
            decision_id=str(decision_id),
            subject_id=subject_id,
            timestamp=event_data.timestamp,
            props=event_data.props,
        )

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
                decision_id=decision_id,
                subject_id=subject_id,
                timestamp=event_data.timestamp,
                props=normalized_props,
                attribution_status=AttributionStatus.ATTRIBUTED,
            )
            async with self._uow:
                await self._events_repository.save(event)
                await self._attribute_pending_events(decision_id, decision)

            await self._update_metric_aggregates(event, decision)
            return event

        if event_type.requires_exposure:
            exposure_events = (
                await self._events_repository.get_exposure_by_decision_id(
                    decision_id
                )
            )
            if exposure_events:
                event = Event(
                    id=event_id,
                    event_type_key=event_data.event_type_key,
                    decision_id=decision_id,
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
                    decision_id=decision_id,
                    subject_id=subject_id,
                    timestamp=event_data.timestamp,
                    props=normalized_props,
                    attribution_status=AttributionStatus.PENDING,
                )
                await self._pending_store.put(event)
            return event

        event = Event(
            id=event_id,
            event_type_key=event_data.event_type_key,
            decision_id=decision_id,
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
        self, decision_id, decision: Decision
    ) -> None:
        pending_events = await self._pending_store.get_by_decision_id(
            str(decision_id)
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

            unique_metric_keys = list({c.metric_key for c in configs})
            metrics_map = await self._metrics_repository.get_by_keys(
                unique_metric_keys
            )
            metrics: list[Metric] = list(metrics_map.values())

            if not metrics:
                return

            max_window = max(c.observation_window_minutes for c in configs)
            ttl = max_window * 60 + 120

            await self._metric_aggregator.update(
                experiment_id=decision.experiment_id,
                event=event,
                metrics=metrics,
                max_ttl_seconds=ttl,
            )
        except Exception as exc:
            logger.warning(
                "Failed to update metric aggregates for experiment %s: %s",
                decision.experiment_id,
                exc,
            )
