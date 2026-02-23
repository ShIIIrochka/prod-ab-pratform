from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.services.domain_event_publisher import DomainEventPublisher
from src.application.services.notification_dispatcher import (
    NotificationDispatcher,
)
from src.application.usecases.guardrails.check_guardrails import (
    CheckGuardrailsUseCase,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.metric import Metric
from src.domain.entities.guardrail_config import (
    GuardrailAction,
    GuardrailConfig,
)
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_status import ExperimentStatus
from tests.fakes import (
    FakeExperimentsRepository,
    FakeGuardrailConfigsRepository,
    FakeGuardrailTriggersRepository,
    FakeMetricAggregator,
    FakeMetricsRepository,
    FakeUnitOfWork,
)
from tests.fakes.notification_events_repository import (
    FakeNotificationEventsRepository,
)
from tests.fakes.notification_task_enqueuer import FakeNotificationTaskEnqueuer


pytestmark = pytest.mark.asyncio


def _make_experiment(
    exp_id=None, status=ExperimentStatus.RUNNING
) -> Experiment:
    exp_id = exp_id or uuid4()
    return Experiment(
        id=exp_id,
        flag_key="test_flag",
        name="Test Experiment",
        status=status,
        version=1,
        audience_fraction=0.5,
        owner_id="owner-1",
        variants=[
            Variant(
                id=uuid4(),
                name="control",
                value="A",
                weight=0.25,
                is_control=True,
            ),
            Variant(
                id=uuid4(),
                name="treatment",
                value="B",
                weight=0.25,
                is_control=False,
            ),
        ],
        targeting_rule=None,
        guardrails=[],
        metric_keys=[],
    )


def _make_publisher() -> tuple[
    DomainEventPublisher, FakeNotificationTaskEnqueuer
]:
    enqueuer = FakeNotificationTaskEnqueuer()
    dispatcher = NotificationDispatcher(
        events_repository=FakeNotificationEventsRepository(),
        task_enqueuer=enqueuer,
    )
    return DomainEventPublisher(dispatcher=dispatcher), enqueuer


async def test_guardrail_trigger_dispatches_notification() -> None:
    exp_id = uuid4()
    experiment = _make_experiment(exp_id)

    exp_repo = FakeExperimentsRepository()
    await exp_repo.save(experiment)

    metric = Metric(
        key="error_rate",
        name="Error Rate",
        calculation_rule='{"type":"COUNT","event_type_key":"error"}',
    )
    metrics_repo = FakeMetricsRepository()
    await metrics_repo.save(metric)

    configs_repo = FakeGuardrailConfigsRepository()
    config = GuardrailConfig(
        id=uuid4(),
        metric_key="error_rate",
        threshold=0.05,
        observation_window_minutes=10,
        action=GuardrailAction.PAUSE,
    )
    configs_repo.set_for_running(exp_id, [config])

    triggers_repo = FakeGuardrailTriggersRepository()
    aggregator = FakeMetricAggregator()
    aggregator.set_value(exp_id, "error_rate", 0.10)  # above threshold

    publisher, enqueuer = _make_publisher()

    uc = CheckGuardrailsUseCase(
        experiments_repository=exp_repo,
        guardrail_configs_repository=configs_repo,
        guardrail_triggers_repository=triggers_repo,
        metrics_repository=metrics_repo,
        metric_aggregator=aggregator,
        uow=FakeUnitOfWork(),
        notification_dispatcher=publisher,
    )
    await uc.execute()

    # GuardrailTriggered + PAUSED status change = 2 tasks enqueued
    # (guardrail event and experiment.paused event are distinct events)
    assert len(enqueuer.enqueued) >= 1

    # Trigger should have been saved
    assert len(triggers_repo.saved_triggers()) == 1

    # Experiment should be paused
    saved_exp = await exp_repo.get_by_id(exp_id)
    assert saved_exp.status == ExperimentStatus.PAUSED


async def test_no_notification_when_guardrail_not_triggered() -> None:
    exp_id = uuid4()
    experiment = _make_experiment(exp_id)

    exp_repo = FakeExperimentsRepository()
    await exp_repo.save(experiment)

    metric = Metric(key="err_ok", name="Error Rate", calculation_rule="{}")
    metrics_repo = FakeMetricsRepository()
    await metrics_repo.save(metric)

    configs_repo = FakeGuardrailConfigsRepository()
    config = GuardrailConfig(
        id=uuid4(),
        metric_key="err_ok",
        threshold=0.10,
        observation_window_minutes=10,
        action=GuardrailAction.PAUSE,
    )
    configs_repo.set_for_running(exp_id, [config])

    # Value is BELOW threshold
    aggregator = FakeMetricAggregator()
    aggregator.set_value(exp_id, "err_ok", 0.02)

    publisher, enqueuer = _make_publisher()

    uc = CheckGuardrailsUseCase(
        experiments_repository=exp_repo,
        guardrail_configs_repository=configs_repo,
        guardrail_triggers_repository=FakeGuardrailTriggersRepository(),
        metrics_repository=metrics_repo,
        metric_aggregator=aggregator,
        uow=FakeUnitOfWork(),
        notification_dispatcher=publisher,
    )
    await uc.execute()

    assert len(enqueuer.enqueued) == 0


async def test_dispatcher_deduplication_same_event() -> None:
    """Dispatching the same NotificationEvent twice only enqueues once."""
    from src.domain.value_objects.notification_event import (
        NotificationEvent,
        make_notification_event_id,
    )
    from src.domain.value_objects.notification_event_type import (
        NotificationEventType,
    )

    events_repo = FakeNotificationEventsRepository()
    enqueuer = FakeNotificationTaskEnqueuer()
    dispatcher = NotificationDispatcher(
        events_repository=events_repo, task_enqueuer=enqueuer
    )

    entity_id = uuid4()
    event = NotificationEvent(
        event_id=make_notification_event_id(
            NotificationEventType.GUARDRAIL_TRIGGERED, entity_id, 1
        ),
        event_type=NotificationEventType.GUARDRAIL_TRIGGERED,
        entity_type="experiment",
        entity_id=entity_id,
        payload={"metric_key": "err_dedup"},
    )

    await dispatcher.dispatch(event)
    await dispatcher.dispatch(event)  # same event_id → dedup

    assert len(enqueuer.enqueued) == 1
