"""Unit tests for GetSimilarExperimentsUseCase."""

from __future__ import annotations

from datetime import UTC
from uuid import uuid4

import pytest

from src.application.dto.learnings import GetSimilarCriteria
from src.application.ports.learnings_repository import LearningsRepositoryPort
from src.application.usecases.learnings.get_similar_experiments import (
    GetSimilarExperimentsUseCase,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
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


@pytest.mark.asyncio
async def test_get_similar_delegates_to_repository_and_returns_list() -> None:
    """execute() calls learnings_repository.get_similar and returns result."""
    from datetime import datetime

    v_control = _make_variant("control", 0.1, is_control=True)
    v_b = _make_variant("B", 0.1)
    exp = Experiment(
        id=uuid4(),
        flag_key="flag",
        name="Similar",
        status=ExperimentStatus.COMPLETED,
        version=1,
        audience_fraction=0.2,
        variants=[v_control, v_b],
        targeting_rule=None,
        owner_id=str(uuid4()),
        completion=ExperimentCompletion(
            outcome=ExperimentOutcome.NO_EFFECT,
            winner_variant_id=None,
            comment="No effect",
            completed_at=datetime.now(UTC),
            completed_by=str(uuid4()),
        ),
    )
    criteria = GetSimilarCriteria(query="test", limit=5)

    class FakeLearningsRepo(LearningsRepositoryPort):
        async def save(self, experiment: Experiment) -> None:
            pass

        async def get_similar(
            self, criteria: GetSimilarCriteria
        ) -> list[Experiment]:
            return [exp]

    repo = FakeLearningsRepo()
    use_case = GetSimilarExperimentsUseCase(learnings_repository=repo)

    result = await use_case.execute(criteria)

    assert len(result) == 1
    assert result[0] is exp
    assert result[0].name == "Similar"


@pytest.mark.asyncio
async def test_get_similar_returns_empty_list() -> None:
    """execute() returns empty list when repository returns no results."""
    criteria = GetSimilarCriteria(flag_key="other", limit=10)

    class FakeLearningsRepo(LearningsRepositoryPort):
        async def save(self, experiment: Experiment) -> None:
            pass

        async def get_similar(
            self, criteria: GetSimilarCriteria
        ) -> list[Experiment]:
            return []

    use_case = GetSimilarExperimentsUseCase(
        learnings_repository=FakeLearningsRepo()
    )

    result = await use_case.execute(criteria)

    assert result == []
