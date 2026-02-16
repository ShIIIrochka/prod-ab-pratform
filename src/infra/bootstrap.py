from jam.aio import Jam
from punq import Container

from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.application.ports.jwt import JWTPort
from src.application.ports.password_hasher import PasswordHasherPort
from src.application.ports.uow import UnitOfWorkPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.application.usecases import (
    ApproveExperimentUseCase,
    CompleteExperimentUseCase,
    CreateExperimentUseCase,
    CreateFeatureFlagUseCase,
    CreateUserUseCase,
    DecideUseCase,
    GetExperimentUseCase,
    GetFeatureFlagUseCase,
    GetUserByIdUseCase,
    LaunchExperimentUseCase,
    ListExperimentsUseCase,
    ListFeatureFlagsUseCase,
    LoginUseCase,
    PauseExperimentUseCase,
    RejectExperimentUseCase,
    RequestChangesUseCase,
    ResumeExperimentUseCase,
    SendExperimentToReviewUseCase,
    UpdateExperimentUseCase,
    UpdateFeatureFlagDefaultValueUseCase,
)
from src.infra.adapters.config import Config
from src.infra.adapters.db.uow import UnitOfWork
from src.infra.adapters.jwt import JWTAdapter
from src.infra.adapters.password_hasher import PasswordHasher
from src.infra.adapters.repositories import (
    DecisionsRepository,
    ExperimentsRepository,
    FeatureFlagsRepository,
    UserRepository,
)


def create_container() -> Container:
    container = Container()
    config = Config.get_config()
    container.register(Config, instance=config)
    jam_config = {
        "jwt": {
            "alg": config.jwt_alg,
            "secret_key": config.jwt_secret_key,
        }
    }
    container.register(
        Jam,
        instance=Jam(
            config=jam_config,
        ),
    )

    container.register(
        JWTPort,
        instance=JWTAdapter(
            jam_instance=container.resolve(Jam),
            access_exp=config.jwt_access_expires,
            refresh_exp=config.jwt_refresh_expires,
        ),
    )
    container.register(PasswordHasherPort, PasswordHasher)
    container.register(UnitOfWorkPort, UnitOfWork)

    container.register(UsersRepositoryPort, UserRepository)
    container.register(DecisionsRepositoryPort, DecisionsRepository)
    container.register(FeatureFlagsRepositoryPort, FeatureFlagsRepository)
    container.register(ExperimentsRepositoryPort, ExperimentsRepository)

    container.register(CreateUserUseCase)
    container.register(LoginUseCase)
    container.register(GetUserByIdUseCase)
    container.register(DecideUseCase)

    container.register(CreateFeatureFlagUseCase)
    container.register(GetFeatureFlagUseCase)
    container.register(ListFeatureFlagsUseCase)
    container.register(UpdateFeatureFlagDefaultValueUseCase)

    container.register(CreateExperimentUseCase)
    container.register(GetExperimentUseCase)
    container.register(ListExperimentsUseCase)
    container.register(UpdateExperimentUseCase)
    container.register(SendExperimentToReviewUseCase)
    container.register(ApproveExperimentUseCase)
    container.register(RequestChangesUseCase)
    container.register(RejectExperimentUseCase)
    container.register(LaunchExperimentUseCase)
    container.register(PauseExperimentUseCase)
    container.register(ResumeExperimentUseCase)
    container.register(CompleteExperimentUseCase)

    return container
