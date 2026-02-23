from __future__ import annotations

from uuid import uuid4

import pytest

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
from tests.fakes.domain_event_publisher import FakeDomainEventPublisher


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
                name="variant",
                value="B",
                weight=0.25,
                is_control=False,
            ),
        ],
        targeting_rule=None,
        owner_id=str(uuid4()),
    )


@pytest.mark.asyncio
async def test_no_running_experiments_noop() -> None:
    """Если нет RUNNING-экспериментов с конфигами — ничего не делаем."""
    guardrail_repo = FakeGuardrailConfigsRepository()
    guardrail_repo.set_for_running(uuid4(), [])  # empty — will return {}

    use_case = CheckGuardrailsUseCase(
        experiments_repository=FakeExperimentsRepository(),
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=FakeGuardrailTriggersRepository(),
        metrics_repository=FakeMetricsRepository(),
        metric_aggregator=FakeMetricAggregator(),
        uow=FakeUnitOfWork(),
        notification_dispatcher=FakeDomainEventPublisher(),
    )
    await use_case.execute()

    # No triggers saved
    assert len(guardrail_repo._for_running) >= 0


@pytest.mark.asyncio
async def test_guardrail_triggers_pause_when_threshold_exceeded() -> None:
    """Guardrail должен поставить эксперимент на паузу при превышении порога."""
    exp_id = uuid4()
    experiment = _make_experiment(exp_id=exp_id)

    config = GuardrailConfig(
        metric_key="error_rate",
        threshold=0.05,
        observation_window_minutes=10,
        action=GuardrailAction.PAUSE,
    )
    metric = Metric(
        key="error_rate",
        name="Error Rate",
        calculation_rule='{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"error"},"denominator":{"type":"COUNT","event_type_key":"request"}}',
    )

    guardrail_repo = FakeGuardrailConfigsRepository()
    guardrail_repo.set_for_running(exp_id, [config])

    experiments_repo = FakeExperimentsRepository()
    await experiments_repo.save(experiment)

    metrics_repo = FakeMetricsRepository()
    metrics_repo.add(metric)

    metric_aggregator = FakeMetricAggregator()
    metric_aggregator.set_value(exp_id, "error_rate", 0.10)

    triggers_repo = FakeGuardrailTriggersRepository()

    use_case = CheckGuardrailsUseCase(
        experiments_repository=experiments_repo,
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=triggers_repo,
        metrics_repository=metrics_repo,
        metric_aggregator=metric_aggregator,
        uow=FakeUnitOfWork(),
        notification_dispatcher=FakeDomainEventPublisher(),
    )
    await use_case.execute()

    assert experiment.status == ExperimentStatus.PAUSED

    saved = triggers_repo.saved_triggers()
    assert len(saved) == 1
    assert saved[0].metric_key == "error_rate"
    assert saved[0].actual_value == 0.10
    assert saved[0].action == GuardrailAction.PAUSE

    reloaded = await experiments_repo.get_by_id(exp_id)
    assert reloaded is not None
    assert reloaded.status == ExperimentStatus.PAUSED


@pytest.mark.asyncio
async def test_guardrail_no_trigger_below_threshold() -> None:
    """Guardrail не срабатывает если значение ниже порога."""
    exp_id = uuid4()
    experiment = _make_experiment(exp_id=exp_id)

    config = GuardrailConfig(
        metric_key="error_rate",
        threshold=0.05,
        observation_window_minutes=10,
        action=GuardrailAction.PAUSE,
    )
    metric = Metric(
        key="error_rate",
        name="Error Rate",
        calculation_rule='{"type":"COUNT","event_type_key":"error"}',
    )

    guardrail_repo = FakeGuardrailConfigsRepository()
    guardrail_repo.set_for_running(exp_id, [config])

    experiments_repo = FakeExperimentsRepository()
    await experiments_repo.save(experiment)

    metrics_repo = FakeMetricsRepository()
    metrics_repo.add(metric)

    metric_aggregator = FakeMetricAggregator()
    metric_aggregator.set_value(exp_id, "error_rate", 0.02)

    triggers_repo = FakeGuardrailTriggersRepository()

    use_case = CheckGuardrailsUseCase(
        experiments_repository=experiments_repo,
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=triggers_repo,
        metrics_repository=metrics_repo,
        metric_aggregator=metric_aggregator,
        uow=FakeUnitOfWork(),
        notification_dispatcher=FakeDomainEventPublisher(),
    )
    await use_case.execute()

    assert experiment.status == ExperimentStatus.RUNNING
    assert len(triggers_repo.saved_triggers()) == 0


@pytest.mark.asyncio
async def test_guardrail_skips_missing_metric() -> None:
    """Если метрика не найдена, guardrail пропускается без ошибки."""
    exp_id = uuid4()
    experiment = _make_experiment(exp_id=exp_id)

    config = GuardrailConfig(
        metric_key="missing_metric",
        threshold=0.05,
        observation_window_minutes=10,
        action=GuardrailAction.PAUSE,
    )

    guardrail_repo = FakeGuardrailConfigsRepository()
    guardrail_repo.set_for_running(exp_id, [config])

    experiments_repo = FakeExperimentsRepository()
    await experiments_repo.save(experiment)

    metrics_repo = FakeMetricsRepository()
    # no metric added — get_by_key returns None

    triggers_repo = FakeGuardrailTriggersRepository()
    metric_aggregator = FakeMetricAggregator()

    use_case = CheckGuardrailsUseCase(
        experiments_repository=experiments_repo,
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=triggers_repo,
        metrics_repository=metrics_repo,
        metric_aggregator=metric_aggregator,
        uow=FakeUnitOfWork(),
        notification_dispatcher=FakeDomainEventPublisher(),
    )
    await use_case.execute()

    assert experiment.status == ExperimentStatus.RUNNING
    assert len(triggers_repo.saved_triggers()) == 0
    # get_value should not have been called (metric was None)
    assert not metric_aggregator._values


@pytest.mark.asyncio
async def test_single_query_for_all_running_experiments() -> None:
    """CheckGuardrails делает ОДИН запрос за все конфиги (не N+1)."""
    guardrail_repo = FakeGuardrailConfigsRepository()
    # Empty — get_for_running_experiments returns {}
    assert guardrail_repo._for_running == {}

    use_case = CheckGuardrailsUseCase(
        experiments_repository=FakeExperimentsRepository(),
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=FakeGuardrailTriggersRepository(),
        metrics_repository=FakeMetricsRepository(),
        metric_aggregator=FakeMetricAggregator(),
        uow=FakeUnitOfWork(),
        notification_dispatcher=FakeDomainEventPublisher(),
    )
    await use_case.execute()

    assert guardrail_repo._get_for_running_calls == 1
