# from uuid import UUID

# from src.application.ports.experiments_repository import (
#     ExperimentsRepositoryPort,
# )
# from src.application.ports.uow import UnitOfWorkPort
# from src.domain.aggregates.experiment import Experiment

# class ArchiveExperimentUseCase:
#     def __init__(
#         self,
#         experiments_repository: ExperimentsRepositoryPort,
#         uow: UnitOfWorkPort,
#     ) -> None:
#         self._experiments_repository = experiments_repository
#         self._uow = uow

#     async def execute(
#         self,
#         experiment_id: UUID,
#     ) -> Experiment:
