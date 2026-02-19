"""Unit tests for CheckGuardrailsUseCase with Redis aggregator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

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
from src.application.usecases.guardrails.check_guardrails import (
    CheckGuardrailsUseCase,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.metric import Metric
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.domain.value_objects.guardrail_config import (
    GuardrailAction,
    GuardrailConfig,
)


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


def _make_uow():
    uow = MagicMock()
    uow.__aenter__ = AsyncMock(return_value=None)
    uow.__aexit__ = AsyncMock(return_value=False)
    return uow


@pytest.mark.asyncio
async def test_no_running_experiments_noop():
    """Если нет RUNNING-экспериментов с конфигами — ничего не делаем."""
    guardrail_repo = AsyncMock(spec=GuardrailConfigsRepositoryPort)
    guardrail_repo.get_for_running_experiments = AsyncMock(return_value={})

    use_case = CheckGuardrailsUseCase(
        experiments_repository=AsyncMock(spec=ExperimentsRepositoryPort),
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=AsyncMock(
            spec=GuardrailTriggersRepositoryPort
        ),
        metrics_repository=AsyncMock(spec=MetricsRepositoryPort),
        metric_aggregator=AsyncMock(spec=MetricAggregatorPort),
        uow=_make_uow(),
    )
    await use_case.execute()

    guardrail_repo.get_for_running_experiments.assert_called_once()


@pytest.mark.asyncio
async def test_guardrail_triggers_pause_when_threshold_exceeded():
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

    guardrail_repo = AsyncMock(spec=GuardrailConfigsRepositoryPort)
    guardrail_repo.get_for_running_experiments = AsyncMock(
        return_value={exp_id: [config]}
    )

    experiments_repo = AsyncMock(spec=ExperimentsRepositoryPort)
    experiments_repo.get_by_id = AsyncMock(return_value=experiment)
    experiments_repo.save = AsyncMock()

    metrics_repo = AsyncMock(spec=MetricsRepositoryPort)
    metrics_repo.get_by_key = AsyncMock(return_value=metric)

    metric_aggregator = AsyncMock(spec=MetricAggregatorPort)
    metric_aggregator.get_value = AsyncMock(return_value=0.10)

    triggers_repo = AsyncMock(spec=GuardrailTriggersRepositoryPort)
    triggers_repo.save = AsyncMock()

    use_case = CheckGuardrailsUseCase(
        experiments_repository=experiments_repo,
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=triggers_repo,
        metrics_repository=metrics_repo,
        metric_aggregator=metric_aggregator,
        uow=_make_uow(),
    )
    await use_case.execute()

    assert experiment.status == ExperimentStatus.PAUSED

    triggers_repo.save.assert_called_once()
    saved_trigger = triggers_repo.save.call_args[0][0]
    assert saved_trigger.metric_key == "error_rate"
    assert saved_trigger.actual_value == 0.10
    assert saved_trigger.action == GuardrailAction.PAUSE

    experiments_repo.save.assert_called_once()


@pytest.mark.asyncio
async def test_guardrail_no_trigger_below_threshold():
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

    guardrail_repo = AsyncMock(spec=GuardrailConfigsRepositoryPort)
    guardrail_repo.get_for_running_experiments = AsyncMock(
        return_value={exp_id: [config]}
    )

    experiments_repo = AsyncMock(spec=ExperimentsRepositoryPort)
    experiments_repo.get_by_id = AsyncMock(return_value=experiment)
    experiments_repo.save = AsyncMock()

    metrics_repo = AsyncMock(spec=MetricsRepositoryPort)
    metrics_repo.get_by_key = AsyncMock(return_value=metric)

    metric_aggregator = AsyncMock(spec=MetricAggregatorPort)
    metric_aggregator.get_value = AsyncMock(return_value=0.02)

    triggers_repo = AsyncMock(spec=GuardrailTriggersRepositoryPort)
    triggers_repo.save = AsyncMock()

    use_case = CheckGuardrailsUseCase(
        experiments_repository=experiments_repo,
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=triggers_repo,
        metrics_repository=metrics_repo,
        metric_aggregator=metric_aggregator,
        uow=_make_uow(),
    )
    await use_case.execute()

    assert experiment.status == ExperimentStatus.RUNNING
    triggers_repo.save.assert_not_called()
    experiments_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_guardrail_skips_missing_metric():
    """Если метрика не найдена, guardrail пропускается без ошибки."""
    exp_id = uuid4()
    experiment = _make_experiment(exp_id=exp_id)

    config = GuardrailConfig(
        metric_key="missing_metric",
        threshold=0.05,
        observation_window_minutes=10,
        action=GuardrailAction.PAUSE,
    )

    guardrail_repo = AsyncMock(spec=GuardrailConfigsRepositoryPort)
    guardrail_repo.get_for_running_experiments = AsyncMock(
        return_value={exp_id: [config]}
    )

    experiments_repo = AsyncMock(spec=ExperimentsRepositoryPort)
    experiments_repo.get_by_id = AsyncMock(return_value=experiment)

    metrics_repo = AsyncMock(spec=MetricsRepositoryPort)
    metrics_repo.get_by_key = AsyncMock(return_value=None)

    triggers_repo = AsyncMock(spec=GuardrailTriggersRepositoryPort)
    metric_aggregator = AsyncMock(spec=MetricAggregatorPort)

    use_case = CheckGuardrailsUseCase(
        experiments_repository=experiments_repo,
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=triggers_repo,
        metrics_repository=metrics_repo,
        metric_aggregator=metric_aggregator,
        uow=_make_uow(),
    )
    await use_case.execute()

    assert experiment.status == ExperimentStatus.RUNNING
    metric_aggregator.get_value.assert_not_called()
    triggers_repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_single_query_for_all_running_experiments():
    """CheckGuardrails делает ОДИН запрос за все конфиги (не N+1)."""
    guardrail_repo = AsyncMock(spec=GuardrailConfigsRepositoryPort)
    guardrail_repo.get_for_running_experiments = AsyncMock(return_value={})

    use_case = CheckGuardrailsUseCase(
        experiments_repository=AsyncMock(spec=ExperimentsRepositoryPort),
        guardrail_configs_repository=guardrail_repo,
        guardrail_triggers_repository=AsyncMock(
            spec=GuardrailTriggersRepositoryPort
        ),
        metrics_repository=AsyncMock(spec=MetricsRepositoryPort),
        metric_aggregator=AsyncMock(spec=MetricAggregatorPort),
        uow=_make_uow(),
    )
    await use_case.execute()

    assert guardrail_repo.get_for_running_experiments.call_count == 1
    guardrail_repo.get_by_experiment_id.assert_not_called()
