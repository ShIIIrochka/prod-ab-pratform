"""Unit tests for LearningsRepository (OpenSearch adapter)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.application.dto.learnings import GetSimilarCriteria
from src.domain.aggregates.experiment import Experiment
from src.domain.entities.variant import Variant
from src.domain.value_objects.experiment_completion import (
    ExperimentCompletion,
    ExperimentOutcome,
)
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.infra.adapters.repositories.learnings_repository import (
    LearningsRepository,
    _experiment_to_doc,
)


def _make_variant(
    name: str, weight: float, is_control: bool = False
) -> Variant:
    return Variant(
        id=uuid4(), name=name, value=name, weight=weight, is_control=is_control
    )


def _make_completed_experiment() -> Experiment:
    v_control = _make_variant("control", 0.1, is_control=True)
    v_b = _make_variant("B", 0.1)
    exp = Experiment(
        id=uuid4(),
        flag_key="button_color",
        name="Test button color",
        status=ExperimentStatus.COMPLETED,
        version=1,
        audience_fraction=0.2,
        variants=[v_control, v_b],
        targeting_rule=None,
        owner_id=str(uuid4()),
        target_metric_key="ctr",
        completion=ExperimentCompletion(
            outcome=ExperimentOutcome.ROLLOUT_WINNER,
            winner_variant_id="B",
            comment="B won, rolling out",
            completed_at=datetime.now(UTC),
            completed_by=str(uuid4()),
        ),
    )
    return exp


@pytest.mark.asyncio
async def test_save_indexes_completed_experiment() -> None:
    """save() calls OpenSearch index with document when experiment is COMPLETED."""
    indexed: list[tuple[str, dict]] = []

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def index(
            self, index: str, id: str, body: dict, refresh: bool = True
        ) -> None:
            indexed.append((id, body))

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    exp = _make_completed_experiment()

    await repo.save(exp)

    assert len(indexed) == 1
    doc_id, doc = indexed[0]
    assert doc_id == str(exp.id)
    assert doc["experiment_id"] == str(exp.id)
    assert doc["name"] == "Test button color"
    assert doc["flag_key"] == "button_color"
    assert doc["outcome"] == "rollout_winner"
    assert doc["target_metric_key"] == "ctr"
    assert "B won, rolling out" in doc["search_text"]
    assert doc["comment"] == "B won, rolling out"
    assert "experiment_snapshot" in doc
    assert doc["experiment_snapshot"]["name"] == "Test button color"


@pytest.mark.asyncio
async def test_save_skips_non_completed_experiment() -> None:
    """save() does not call index when experiment is not COMPLETED."""
    indexed: list[tuple[str, dict]] = []

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def index(
            self, index: str, id: str, body: dict, refresh: bool = True
        ) -> None:
            indexed.append((id, body))

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    v_control = _make_variant("control", 0.1, is_control=True)
    v_b = _make_variant("B", 0.1)
    exp = Experiment(
        id=uuid4(),
        flag_key="flag",
        name="Draft",
        status=ExperimentStatus.DRAFT,
        version=1,
        audience_fraction=0.2,
        variants=[v_control, v_b],
        targeting_rule=None,
        owner_id=str(uuid4()),
        completion=None,
    )

    await repo.save(exp)

    assert len(indexed) == 0


@pytest.mark.asyncio
async def test_save_no_op_when_client_is_none() -> None:
    """save() does nothing when OpenSearch client is not connected."""

    class FakeOpenSearch:
        _client = None

        @property
        def client(self):
            return None

        @property
        def index_name(self) -> str:
            return "learnings"

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    exp = _make_completed_experiment()

    await repo.save(exp)


@pytest.mark.asyncio
async def test_get_similar_maps_docs_to_experiments() -> None:
    """get_similar() returns experiments mapped from _source experiment_snapshot."""
    search_body: list[dict] = []
    exp1 = _make_completed_experiment()
    exp2 = _make_completed_experiment()
    doc1 = _experiment_to_doc(exp1)
    doc2 = _experiment_to_doc(exp2)

    class FakeOpenSearch:
        @property
        def client(self):
            return self

        @property
        def index_name(self) -> str:
            return "learnings"

        async def search(self, index: str, body: dict) -> dict:
            search_body.append(body)
            return {
                "hits": {
                    "hits": [
                        {"_id": str(exp1.id), "_source": doc1},
                        {"_id": str(exp2.id), "_source": doc2},
                    ],
                }
            }

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    criteria = GetSimilarCriteria(
        query="button",
        flag_key="button_color",
        limit=10,
    )

    result = await repo.get_similar(criteria)

    assert len(search_body) == 1
    assert search_body[0]["size"] == 10
    assert "query" in search_body[0]
    assert len(result) == 2
    assert result[0].id == exp1.id
    assert result[0].name == exp1.name
    assert result[1].id == exp2.id
    assert result[1].name == exp2.name


@pytest.mark.asyncio
async def test_get_similar_returns_empty_when_client_is_none() -> None:
    """get_similar() returns [] when OpenSearch client is not connected."""

    class FakeOpenSearch:
        @property
        def client(self):
            return None

        @property
        def index_name(self) -> str:
            return "learnings"

    repo = LearningsRepository(opensearch=FakeOpenSearch())
    criteria = GetSimilarCriteria(limit=5)

    result = await repo.get_similar(criteria)

    assert result == []
