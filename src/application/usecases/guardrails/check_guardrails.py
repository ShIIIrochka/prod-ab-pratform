"""
Алгоритм:
  Для каждого RUNNING эксперимента:
    Для каждого guardrail-правила:
      1. Получить все события за последние observation_window_minutes минут
      2. Вычислить значение метрики
      3. Если значение > порога → сработал guardrail:
         - Выполнить action (PAUSE или ROLLBACK_TO_CONTROL)
         - Записать GuardrailTrigger в историю
"""

from __future__ import annotations

import logging

from datetime import UTC, datetime, timedelta

from src.application.ports.events_repository import EventsRepositoryPort
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.application.ports.guardrail_triggers_repository import (
    GuardrailTriggersRepositoryPort,
)
from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.application.ports.uow import UnitOfWorkPort
from src.domain.aggregates.event import AttributionStatus
from src.domain.services.metric_calculator import calculate_metric
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.guardrail_config import GuardrailAction
from src.domain.value_objects.guardrail_trigger import GuardrailTrigger


logger = logging.getLogger(__name__)


class CheckGuardrailsUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        events_repository: EventsRepositoryPort,
        guardrail_configs_repository: GuardrailConfigsRepositoryPort,
        guardrail_triggers_repository: GuardrailTriggersRepositoryPort,
        metrics_repository: MetricsRepositoryPort,
        uow: UnitOfWorkPort,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._events_repository = events_repository
        self._guardrail_configs_repository = guardrail_configs_repository
        self._guardrail_triggers_repository = guardrail_triggers_repository
        self._metrics_repository = metrics_repository
        self._uow = uow

    async def execute(self) -> None:
        running_experiments = await self._experiments_repository.list_all(
            status=ExperimentStatus.RUNNING
        )

        for experiment in running_experiments:
            configs = (
                await self._guardrail_configs_repository.get_by_experiment_id(
                    experiment.id
                )
            )
            if not configs:
                continue

            for config in configs:
                # Если rollback уже активен для этого guardrail action — пропускаем повторный trigger
                if (
                    config.action == GuardrailAction.ROLLBACK_TO_CONTROL
                    and experiment.rollback_to_control_active
                ):
                    continue

                now = datetime.now(UTC)
                window_start = now - timedelta(
                    minutes=config.observation_window_minutes
                )

                events = await self._events_repository.get_by_experiment(
                    experiment_id=experiment.id,
                    from_time=window_start,
                    to_time=now,
                    attribution_status=AttributionStatus.ATTRIBUTED,
                )

                metric = await self._metrics_repository.get_by_key(
                    config.metric_key
                )
                if metric is None:
                    logger.warning(
                        "Guardrail metric '%s' not found for experiment %s, skipping",
                        config.metric_key,
                        experiment.id,
                    )
                    continue

                actual_value = calculate_metric(metric, events)

                if actual_value <= config.threshold:
                    continue

                # Guardrail сработал
                trigger = GuardrailTrigger(
                    experiment_id=str(experiment.id),
                    metric_key=config.metric_key,
                    threshold=config.threshold,
                    observation_window_minutes=config.observation_window_minutes,
                    action=config.action,
                    actual_value=actual_value,
                    triggered_at=now,
                )

                logger.warning(
                    "Guardrail triggered for experiment %s: metric=%s actual=%.4f threshold=%.4f action=%s",
                    experiment.id,
                    config.metric_key,
                    actual_value,
                    config.threshold,
                    config.action,
                )

                async with self._uow:
                    # Записываем в аудит (B5-5)
                    await self._guardrail_triggers_repository.save(trigger)

                    # Выполняем action (B5-4)
                    if config.action == GuardrailAction.PAUSE:
                        experiment.pause()
                    elif config.action == GuardrailAction.ROLLBACK_TO_CONTROL:
                        experiment.activate_rollback_to_control()

                    await self._experiments_repository.save(experiment)

                # После паузы дальше guardrails этого эксперимента не проверяем
                if config.action == GuardrailAction.PAUSE:
                    break
