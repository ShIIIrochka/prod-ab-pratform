from __future__ import annotations

from datetime import datetime

from application.dto.decide import (
    DecideRequest,
    DecideResponse,
    DecisionResponse,
)
from application.ports.decisions_repository import DecisionsRepositoryPort
from application.ports.experiments_repository import ExperimentsRepositoryPort
from application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from domain.aggregates.decision import Decision
from domain.exceptions import FeatureFlagNotFoundException
from domain.services.decision_engine import compute_decision
from domain.services.decision_id_generator import (
    generate_deterministic_decision_id,
)


class DecideUseCase:
    def __init__(
        self,
        feature_flags_repository: FeatureFlagsRepositoryPort,
        experiments_repository: ExperimentsRepositoryPort,
        decisions_repository: DecisionsRepositoryPort,
    ) -> None:
        self._feature_flags_repository = feature_flags_repository
        self._experiments_repository = experiments_repository
        self._decisions_repository = decisions_repository

    async def execute(self, data: DecideRequest) -> DecideResponse:
        flag = await self._feature_flags_repository._get_by_key_async(
            data.flag_key
        )

        if flag is None:
            raise FeatureFlagNotFoundException(flag_key=data.flag_key)

        experiment = await self._experiments_repository._get_active_by_flag_key_async(
            data.flag_key
        )

        decision_result = compute_decision(
            experiment=experiment,
            subject_id=str(data.subject_id),
            attributes=data.attributes,
        )

        # Формируем итоговое значение и метаданные
        timestamp = datetime.utcnow()

        if decision_result.applied:
            # Эксперимент применился - берём значение из варианта
            value = decision_result.value
            experiment_id = experiment.id  # UUID
            variant_id = decision_result.variant_id
            experiment_version = experiment.version
        else:
            # Эксперимент не применился - берём default из флага
            value = flag.default_value.value
            experiment_id = None
            variant_id = None
            experiment_version = None

        # Генерируем детерминированный decision_id для идемпотентности (ТЗ 3.5.3)
        decision_id = generate_deterministic_decision_id(
            subject_id=data.subject_id,
            flag_key=data.flag_key,
            experiment_id=experiment_id,
            variant_id=variant_id,
        )

        # Проверяем, существует ли уже решение с таким ID (идемпотентность)
        existing_decision = await self._decisions_repository.get_by_id(
            str(decision_id)
        )

        if existing_decision:
            # Решение уже существует - возвращаем его (ретрай запроса)
            decision = existing_decision
        else:
            # Создаём новое решение с детерминированным UUID
            decision = Decision(
                id=decision_id,  # Передаём явно для идемпотентности
                subject_id=data.subject_id,
                flag_key=data.flag_key,
                value=value,
                experiment_id=experiment_id,
                variant_id=variant_id,
                experiment_version=experiment_version,
                timestamp=timestamp,
            )
            await self._decisions_repository.save(decision)

        # Формируем ответ для продукта
        decision_response = DecisionResponse(
            decision_id=decision.decision_id,  # str(decision.id) через property
            subject_id=data.subject_id,
            flag_key=data.flag_key,
            value=value,
            experiment_id=str(experiment_id) if experiment_id else None,
            variant_id=variant_id,
            timestamp=timestamp,
        )

        return DecideResponse(decision=decision_response)
