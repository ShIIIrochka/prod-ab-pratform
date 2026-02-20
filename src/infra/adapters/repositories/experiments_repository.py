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
from src.infra.adapters.db.models.user import UserModel
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
        existing_model = await ExperimentModel.get_or_none(id=experiment.id)
        if existing_model:
            model = ExperimentModel.from_domain(experiment)
            await model.save(force_update=True)
        else:
            model = ExperimentModel.from_domain(experiment)
            await model.save()

        await self._upsert_variants(experiment)

        await ApprovalModel.filter(experiment_id=experiment.id).delete()
        if experiment.approvals:
            experiment_model = await ExperimentModel.get(id=experiment.id)
            approval_models = []
            for a in experiment.approvals:
                user_model = await UserModel.get(id=a.user_id)
                approval_models.append(
                    ApprovalModel(
                        experiment=experiment_model,
                        user=user_model,
                        comment=a.comment,
                        timestamp=a.timestamp,
                    )
                )
            await ApprovalModel.bulk_create(approval_models)

    async def _upsert_variants(self, experiment: Experiment) -> None:
        """Upsert variants by (experiment_id, name) to preserve IDs and FK integrity.

        Preserves existing variant IDs so that decisions referencing them via FK
        are not CASCADE-deleted. Only deletes variants no longer in the aggregate.
        """
        incoming_names = {v.name for v in experiment.variants}

        # Delete variants removed from the aggregate (safe — no decisions reference them yet
        # since variants can only be changed before launch/while in DRAFT)
        await (
            VariantModel.filter(
                experiment_id=experiment.id,
            )
            .exclude(name__in=list(incoming_names))
            .delete()
        )

        for v in experiment.variants:
            existing = await VariantModel.get_or_none(
                experiment_id=experiment.id, name=v.name
            )
            if existing is not None:
                # Update in place — preserve the DB id so decisions keep FK intact
                existing.value = {"value": v.value}
                existing.weight = v.weight
                existing.is_control = v.is_control
                await existing.save(force_update=True)
            else:
                try:
                    await VariantModel.from_domain(v, experiment.id).save()
                except IntegrityError:
                    msg = f"Variant name already exists: {v.name}"
                    raise ValueError(msg)

    async def get_by_id(self, experiment_id: UUID) -> Experiment | None:
        model = (
            await ExperimentModel.filter(id=experiment_id)
            .prefetch_related("variants", "owner")
            .first()
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
