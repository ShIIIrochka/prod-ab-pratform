import logging

from datetime import datetime
from uuid import UUID

from src.application.ports.learnings_repository import LearningsRepositoryPort
from src.domain.aggregates.learning import Learning
from src.domain.entities.guardrail_config import (
    GuardrailAction,
    GuardrailConfig,
)
from src.domain.entities.variant import Variant
from src.domain.exceptions.learnings import LearningNotFoundError
from src.domain.value_objects.experiment_completion import (
    ExperimentOutcome,
)
from src.domain.value_objects.targeting_rule import TargetingRule
from src.infra.adapters.opensearch.opensearch import OpenSearch


logger = logging.getLogger(__name__)


def _learning_to_doc(learning: Learning) -> dict:
    return {
        "experiment_id": str(learning.experiment_id),
        "flag_key": learning.flag_key,
        "name": learning.name,
        "status": "completed",
        "audience_fraction": learning.audience_fraction,
        "variants": [
            {
                "id": str(v.id),
                "name": v.name,
                "value": v.value,
                "weight": v.weight,
                "is_control": v.is_control,
            }
            for v in learning.variants
        ],
        "targeting_rule": (
            learning.targeting_rule.rule_expression
            if learning.targeting_rule
            else None
        ),
        "owner_id": learning.owner_id,
        "target_metric_key": learning.target_metric_key,
        "metric_keys": learning.metric_keys or [],
        "guardrails": [
            {
                "id": str(g.id),
                "metric_key": g.metric_key,
                "threshold": g.threshold,
                "observation_window_minutes": g.observation_window_minutes,
                "action": g.action.value,
            }
            for g in learning.guardrails
        ],
        "completion": {
            "outcome": learning.outcome.value,
            "winner_variant_id": learning.winner_variant_id,
            "comment": learning.outcome_comment,
            "completed_at": learning.completed_at.isoformat(),
            "completed_by": learning.completed_by,
        },
        "created_at": learning.created_at.isoformat(),
        "updated_at": learning.updated_at.isoformat(),
        "hypothesis": learning.hypothesis,
        "context_and_segment": learning.context_and_segment,
        "links": learning.links,
        "notes": learning.notes,
        "tags": learning.tags,
    }


def _doc_to_learning(doc_id: str, source: dict) -> Learning | None:
    try:
        _id = UUID(doc_id)
    except (KeyError, ValueError, TypeError):
        return None
    variants_data = source.get("variants") or []
    variants = []
    for v in variants_data:
        try:
            variants.append(
                Variant(
                    id=UUID(v["id"]),
                    name=v["name"],
                    value=v["value"],
                    weight=float(v["weight"]),
                    is_control=bool(v.get("is_control", False)),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    if not variants:
        return None
    targeting_rule = None
    if source.get("targeting_rule"):
        try:
            targeting_rule = TargetingRule(
                rule_expression=source["targeting_rule"]
            )
        except ValueError:
            pass
    guardrails = []
    for g in source.get("guardrails") or []:
        try:
            guardrails.append(
                GuardrailConfig(
                    id=UUID(g["id"]),
                    metric_key=g["metric_key"],
                    threshold=float(g["threshold"]),
                    observation_window_minutes=int(
                        g["observation_window_minutes"]
                    ),
                    action=GuardrailAction(g["action"]),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    completion_data = source.get("completion") or {}
    completed_at_str = completion_data.get("completed_at")
    try:
        completed_at = (
            datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
            if completed_at_str
            else datetime.now()
        )
    except (ValueError, AttributeError):
        completed_at = datetime.now()
    created_at_str = source.get("created_at")
    updated_at_str = source.get("updated_at")
    try:
        created_at = (
            datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if created_at_str
            else datetime.now()
        )
    except (ValueError, AttributeError):
        created_at = datetime.now()
    try:
        updated_at = (
            datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            if updated_at_str
            else created_at
        )
    except (ValueError, AttributeError):
        updated_at = created_at
    return Learning(
        id=_id,
        experiment_id=UUID(source.get("experiment_id")),
        hypothesis=source.get("hypothesis") or "",
        context_and_segment=source.get("context_and_segment") or "",
        links=list(source.get("links") or []),
        notes=source.get("notes"),
        tags=list(source.get("tags") or []),
        flag_key=source.get("flag_key", ""),
        name=source.get("name", ""),
        target_metric_key=source.get("target_metric_key") or None,
        metric_keys=source.get("metric_keys") or [],
        guardrails=guardrails,
        outcome=ExperimentOutcome(completion_data.get("outcome", "no_effect")),
        outcome_comment=completion_data.get("comment", ""),
        winner_variant_id=completion_data.get("winner_variant_id"),
        completed_at=completed_at,
        completed_by=completion_data.get("completed_by", ""),
        owner_id=source.get("owner_id", ""),
        audience_fraction=float(source.get("audience_fraction", 0)),
        variants=variants,
        targeting_rule=targeting_rule,
        created_at=created_at,
        updated_at=updated_at,
    )


class LearningsRepository(LearningsRepositoryPort):
    def __init__(self, opensearch: OpenSearch) -> None:
        self._client = opensearch.client
        self._index_name = opensearch.index_name

    async def save(self, learning: Learning) -> None:
        doc = _learning_to_doc(learning)
        if self._client is None:
            return
        try:
            await self._client.index(
                index=self._index_name,
                id=str(learning.id),
                body=doc,
                refresh=True,
            )
        except Exception as e:
            logger.exception(
                "Failed to index learning %s: %s",
                learning.id,
                e,
            )
            raise

    async def update_learning(self, learning: Learning) -> None:
        doc = {
            "hypothesis": learning.hypothesis,
            "context_and_segment": learning.context_and_segment,
            "links": learning.links,
            "notes": learning.notes,
            "tags": learning.tags,
        }
        try:
            await self._client.update(
                index=self._index_name,
                id=str(learning.id),
                body={"doc": doc},
                refresh=True,
            )
        except Exception as e:
            if getattr(e, "status_code", None) == 404:
                raise LearningNotFoundError(
                    f"Learning record not found for experiment {learning.id}"
                ) from e
            logger.exception(
                "Failed to update learning for experiment %s: %s",
                learning.experiment_id,
                e,
            )
            raise

    async def get_by_experiment_id(
        self,
        experiment_id: UUID,
    ) -> Learning | None:
        try:
            response = await self._client.search(
                index=self._index_name,
                body={"query": {"term": {"user_id": 123}}},
            )
        except Exception as e:
            if getattr(e, "status_code", None) == 404:
                return None
            logger.exception(
                "Failed to get learning for experiment %s: %s",
                experiment_id,
                e,
            )
            raise
        hit = response.get("hits", {}).get("hits", [])
        return _doc_to_learning(hit[0].get("_id"), hit[0].get("_source"))

    async def get_similar(
        self,
        limit: int,
        query: str | None = None,
        flag_key: str | None = None,
        owner_id: str | None = None,
        outcome: ExperimentOutcome | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        target_metric_key: str | None = None,
    ) -> list[Learning]:
        must = []
        filters = []

        if query and query.strip():
            must.append(
                {
                    "multi_match": {
                        "query": query.strip(),
                        "fields": [
                            "name^3",
                            "hypothesis^2",
                            "notes^2",
                            "tags",
                            "completion.comment^2",
                            "targeting_rule",
                        ],
                        "fuzziness": "AUTO",
                    }
                }
            )

        if flag_key:
            filters.append({"term": {"flag_key": flag_key}})

        if owner_id:
            filters.append({"term": {"owner_id": owner_id}})

        if outcome:
            filters.append({"term": {"completion.outcome": outcome.value}})

        if target_metric_key:
            filters.append({"term": {"target_metric_key": target_metric_key}})

        if date_from or date_to:
            range_q: dict = {"completion.completed_at": {}}
            if date_from:
                range_q["completion.completed_at"]["gte"] = (
                    date_from.isoformat()
                )
            if date_to:
                range_q["completion.completed_at"]["lte"] = date_to.isoformat()
            filters.append({"range": range_q})

        body = {
            "size": limit,
            "sort": [
                {"_score": {"order": "desc"}},
                {"completion.completed_at": {"order": "desc"}},
            ],
        }

        if must or filters:
            body["query"] = {
                "bool": {
                    "must": must if must else [{"match_all": {}}],
                    "filter": filters,
                }
            }
        else:
            body["query"] = {"match_all": {}}

        try:
            response = await self._client.search(
                index=self._index_name,
                body=body,
            )
        except Exception as e:
            logger.exception("Learnings search failed: %s", e)
            return []

        hits = response.get("hits", {}).get("hits", [])
        result: list[Learning] = []
        for hit in hits:
            source = hit.get("_source") or {}
            learning = _doc_to_learning(hit.get("_id"), source)
            if learning:
                result.append(learning)
        return result
