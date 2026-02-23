"""E2E tests for ExperimentsRepository variant upsert — uses Postgres test DB."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.infra.adapters.db.models.user import UserModel
from src.infra.adapters.repositories.experiments_repository import (
    ExperimentsRepository,
)


def _make_experiment(
    variants: list[Variant], owner_id: str = "owner-1"
) -> Experiment:
    return Experiment(
        id=uuid4(),
        flag_key="flag",
        name="Test",
        status=ExperimentStatus.DRAFT,
        version=1,
        audience_fraction=0.2,
        variants=variants,
        targeting_rule=None,
        owner_id=owner_id,
    )


pytestmark = pytest.mark.asyncio


@pytest.fixture
async def owner(client) -> None:
    """Create an owner user required by Experiment FK."""
    await UserModel.get_or_create(
        id="owner-1",
        defaults={
            "email": "owner@example.com",
            "password": "hashed",
            "role": "experimenter",
        },
    )


async def test_upsert_existing_variant_does_not_delete(client, owner) -> None:
    """При сохранении с теми же именами вариантов удаление не вызывается."""
    existing_id = uuid4()
    variant = Variant(
        id=existing_id, name="control", value="A", weight=0.1, is_control=True
    )
    variant_b = Variant(
        id=uuid4(), name="B", value="b", weight=0.1, is_control=False
    )
    experiment = _make_experiment([variant, variant_b])

    repo = ExperimentsRepository()
    await repo.save(experiment)

    reloaded = await repo.get_by_id(experiment.id)
    assert reloaded is not None
    assert len(reloaded.variants) == 2
    names = {v.name for v in reloaded.variants}
    assert names == {"control", "B"}

    await repo.save(experiment)
    reloaded2 = await repo.get_by_id(experiment.id)
    assert reloaded2 is not None
    assert len(reloaded2.variants) == 2


async def test_upsert_new_variant_creates_it(client, owner) -> None:
    """Новый вариант (не существует в БД) создаётся через save()."""
    variant = Variant(
        id=uuid4(), name="control", value="A", weight=0.1, is_control=True
    )
    variant_new = Variant(
        id=uuid4(), name="C", value="c", weight=0.1, is_control=False
    )
    experiment = _make_experiment([variant, variant_new])

    repo = ExperimentsRepository()
    await repo.save(experiment)

    reloaded = await repo.get_by_id(experiment.id)
    assert reloaded is not None
    assert len(reloaded.variants) == 2
    names = {v.name: v.value for v in reloaded.variants}
    assert names["control"] == "A"
    assert names["C"] == "c"


async def test_upsert_removes_variant_not_in_incoming(client, owner) -> None:
    """Вариант, отсутствующий во входящем списке, удаляется из БД."""
    variant_a = Variant(
        id=uuid4(), name="A", value="a", weight=0.2, is_control=True
    )
    variant_b = Variant(
        id=uuid4(), name="B", value="b", weight=0.0, is_control=False
    )
    experiment = _make_experiment([variant_a, variant_b])

    repo = ExperimentsRepository()
    await repo.save(experiment)

    reloaded = await repo.get_by_id(experiment.id)
    assert reloaded is not None
    assert len(reloaded.variants) == 2

    variant_a_only = Variant(
        id=variant_a.id, name="A", value="a", weight=0.2, is_control=True
    )
    experiment.variants = [variant_a_only]
    await repo.save(experiment)

    reloaded2 = await repo.get_by_id(experiment.id)
    assert reloaded2 is not None
    assert len(reloaded2.variants) == 1
    assert reloaded2.variants[0].name == "A"
