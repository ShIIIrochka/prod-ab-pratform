import logging

from datetime import UTC, datetime

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.application.ports.guardrail_triggers_repository import (
    GuardrailTriggersRepositoryPort,
)
from src.application.ports.metric_aggregator import MetricAggregatorPort
from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.application.ports.uow import UnitOfWorkPort
from src.application.services.domain_event_publisher import DomainEventPublisher
from src.domain.entities.guardrail_config import GuardrailAction
from src.domain.events.experiment import GuardrailTriggered
from src.domain.value_objects.guardrail_trigger import GuardrailTrigger


logger = logging.getLogger(__name__)


class CheckGuardrailsUseCase:
    def __init__(
        self,
        experiments_repository: ExperimentsRepositoryPort,
        guardrail_configs_repository: GuardrailConfigsRepositoryPort,
        guardrail_triggers_repository: GuardrailTriggersRepositoryPort,
        metrics_repository: MetricsRepositoryPort,
        metric_aggregator: MetricAggregatorPort,
        uow: UnitOfWorkPort,
        notification_dispatcher: DomainEventPublisher,
    ) -> None:
        self._experiments_repository = experiments_repository
        self._guardrail_configs_repository = guardrail_configs_repository
        self._guardrail_triggers_repository = guardrail_triggers_repository
        self._metrics_repository = metrics_repository
        self._metric_aggregator = metric_aggregator
        self._uow = uow
        self._publisher = notification_dispatcher

    async def execute(self) -> None:
        configs_by_experiment = await self._guardrail_configs_repository.get_for_running_experiments()
        if not configs_by_experiment:
            return

        for experiment_id, configs in configs_by_experiment.items():
            experiment = await self._experiments_repository.get_by_id(
                experiment_id
            )
            if experiment is None:
                continue

            for config in configs:
                if (
                    config.action == GuardrailAction.ROLLBACK_TO_CONTROL
                    and experiment.rollback_to_control_active
                ):
                    continue

                metric = await self._metrics_repository.get_by_key(
                    config.metric_key
                )
                if metric is None:
                    logger.warning(
                        "Guardrail metric '%s' not found for experiment %s, skipping",
                        config.metric_key,
                        experiment_id,
                    )
                    continue

                actual_value = await self._metric_aggregator.get_value(
                    experiment_id=experiment_id,
                    metric=metric,
                    window_minutes=config.observation_window_minutes,
                )
                if actual_value <= config.threshold:
                    continue

                now = datetime.now(UTC)
                trigger = GuardrailTrigger(
                    experiment_id=experiment_id,
                    metric_key=config.metric_key,
                    threshold=config.threshold,
                    observation_window_minutes=config.observation_window_minutes,
                    action=config.action,
                    actual_value=actual_value,
                    triggered_at=now,
                )

                logger.warning(
                    "Guardrail triggered for experiment %s: metric=%s actual=%.4f threshold=%.4f action=%s",
                    experiment_id,
                    config.metric_key,
                    actual_value,
                    config.threshold,
                    config.action,
                )

                async with self._uow:
                    await self._guardrail_triggers_repository.save(trigger)

                    if config.action == GuardrailAction.PAUSE:
                        experiment.pause()
                    elif config.action == GuardrailAction.ROLLBACK_TO_CONTROL:
                        experiment.activate_rollback_to_control()

                    await self._experiments_repository.save(experiment)

                domain_event = GuardrailTriggered(
                    experiment_id=experiment_id,
                    experiment_name=experiment.name,
                    flag_key=experiment.flag_key,
                    owner_id=experiment.owner_id,
                    metric_key=config.metric_key,
                    threshold=config.threshold,
                    actual_value=actual_value,
                    action=config.action.value,
                    triggered_at=now,
                    version=experiment.version,
                )
                await self._publisher.publish(domain_event)
                await self._publisher.publish_from(experiment)

                if config.action == GuardrailAction.PAUSE:
                    break
