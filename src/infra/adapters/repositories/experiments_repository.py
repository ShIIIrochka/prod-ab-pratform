from __future__ import annotations

from uuid import UUID

from tortoise.exceptions import IntegrityError

from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.domain.aggregates.experiment import Experiment
from src.domain.value_objects.experiment_status import ExperimentStatus
from src.infra.adapters.db.models.approval import ApprovalModel
from src.infra.adapters.db.models.experiment import ExperimentModel
from src.infra.adapters.db.models.variant import VariantModel


class ExperimentsRepository(ExperimentsRepositoryPort):
    async def get_active_by_flag_key(self, flag_key: str) -> Experiment | None:
        model = (
            await ExperimentModel.filter(
                flag_key=flag_key,
                status=ExperimentStatus.RUNNING.value,
            )
            .prefetch_related("variants")
            .prefetch_related("owner")
            .first()
        )

        if model is None:
            return None
        return await model.to_domain()

    async def save(self, experiment: Experiment) -> None:
        model = ExperimentModel.from_domain(experiment)
        await model.save()

        await VariantModel.filter(experiment_id=experiment.id).delete()
        variant_models = [
            VariantModel.from_domain(v, experiment.id)
            for v in experiment.variants
        ]
        if variant_models:
            try:
                await VariantModel.bulk_create(variant_models)
            except IntegrityError:
                msg = "Variant name already exists"
                raise ValueError(msg)

        await ApprovalModel.filter(experiment_id=experiment.id).delete()
        approval_models = [
            ApprovalModel(
                experiment_id=experiment.id,
                user_id=a.user_id,
                comment=a.comment,
                timestamp=a.timestamp,
            )
            for a in experiment.approvals
        ]
        if approval_models:
            await ApprovalModel.bulk_create(approval_models)

    async def get_by_id(self, experiment_id: UUID) -> Experiment | None:
        model = (
            await ExperimentModel.filter(id=experiment_id)
            .first()
            .prefetch_related("variants", "owner")
        )
        if model is None:
            return None
        return await model.to_domain()

    async def list_all(
        self,
        flag_key: str | None = None,
        status: ExperimentStatus | None = None,
    ) -> list[Experiment]:
        query = ExperimentModel.all().prefetch_related("variants", "owner")

        if flag_key:
            query = query.filter(flag_key=flag_key)
        if status:
            query = query.filter(status=status.value)

        models = await query
        return [await m.to_domain() for m in models]
