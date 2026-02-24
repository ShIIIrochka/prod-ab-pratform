"""Unit tests for UpdateExperimentLearningUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from src.application.dto.learnings import UpdateLearningRequest
from src.application.ports.learnings_repository import LearningsRepositoryPort
from src.application.usecases.learnings.update_experiment_learning import (
    UpdateExperimentLearningUseCase,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.aggregates.learning import Learning
from src.domain.entities.variant import Variant
from src.domain.exceptions.learnings import LearningNotFoundError
from src.domain.value_objects.experiment_completion import (
    ExperimentCompletion,
    ExperimentOutcome,
)
from src.domain.value_objects.experiment_status import ExperimentStatus


def _make_variant(
    name: str, weight: float, is_control: bool = False
) -> Variant:
    return Variant(
        id=uuid4(), name=name, value=name, weight=weight, is_control=is_control
    )


def _make_completed_experiment() -> Experiment:
    return Experiment(
        id=uuid4(),
        flag_key="flag",
        name="Exp",
        status=ExperimentStatus.COMPLETED,
        version=1,
        audience_fraction=0.2,
        variants=[
            _make_variant("control", 0.1, is_control=True),
            _make_variant("B", 0.1),
        ],
        targeting_rule=None,
        owner_id=str(uuid4()),
        completion=ExperimentCompletion(
            outcome=ExperimentOutcome.NO_EFFECT,
            winner_variant_id=None,
            comment="Done",
            completed_at=datetime.now(UTC),
            completed_by=str(uuid4()),
        ),
    )


@pytest.mark.asyncio
async def test_update_learning_merges_and_returns_learning() -> None:
    exp = _make_completed_experiment()
    exp_id = exp.id
    updated_learning = Learning.from_completed_experiment(
        exp
    ).with_updated_editable(
        hypothesis="New hypothesis",
        context_and_segment="old segment",
        links=["https://report/1"],
        notes="Updated",
        tags=["new-tag"],
    )

    class FakeRepo(LearningsRepositoryPort):
        async def save(self, learning: Learning) -> None:
            pass

        async def update_learning(self, learning: Learning) -> None:
            pass

        async def get_by_experiment_id(
            self,
            experiment_id: UUID,
        ) -> Learning | None:
            if experiment_id == exp_id:
                return updated_learning
            return None

        async def get_similar(
            self,
            limit: int,
            query: str | None = None,
            flag_key: str | None = None,
            owner_id: str | None = None,
            outcome=None,
            date_from=None,
            date_to=None,
            target_metric_key: str | None = None,
        ) -> list[Learning]:
            return []

    use_case = UpdateExperimentLearningUseCase(learnings_repository=FakeRepo())
    data = UpdateLearningRequest(
        hypothesis="New hypothesis",
        links=["https://report/1"],
        notes="Updated",
        tags=["new-tag"],
    )

    result = await use_case.execute(exp_id, data)

    assert result.experiment_id == exp_id
    assert result.hypothesis == "New hypothesis"
    assert result.context_and_segment == "old segment"
    assert list(result.links) == ["https://report/1"]
    assert result.notes == "Updated"
    assert list(result.tags) == ["new-tag"]


@pytest.mark.asyncio
async def test_update_learning_raises_when_not_found() -> None:
    exp_id = uuid4()

    class FakeRepo(LearningsRepositoryPort):
        async def save(self, learning: Learning) -> None:
            pass

        async def update_learning(self, learning: Learning) -> None:
            pass

        async def get_by_experiment_id(
            self,
            experiment_id: UUID,
        ) -> Learning | None:
            return None

        async def get_similar(
            self,
            limit: int,
            query: str | None = None,
            flag_key: str | None = None,
            owner_id: str | None = None,
            outcome=None,
            date_from=None,
            date_to=None,
            target_metric_key: str | None = None,
        ) -> list[Learning]:
            return []

    use_case = UpdateExperimentLearningUseCase(learnings_repository=FakeRepo())
    data = UpdateLearningRequest(hypothesis="New")

    with pytest.raises(LearningNotFoundError) as exc_info:
        await use_case.execute(exp_id, data)

    assert str(exp_id) in str(exc_info.value.message)
