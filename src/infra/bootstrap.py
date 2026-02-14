from jam import Jam
from punq import Container

from application.ports.decisions_repository import DecisionsRepositoryPort
from application.ports.experiments_repository import ExperimentsRepositoryPort
from application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from application.ports.jwt import JWTPort
from application.ports.password_hasher import PasswordHasherPort
from application.ports.users_repository import UsersRepositoryPort
from application.usecases.auth.login import LoginUseCase
from application.usecases.decide import DecideUseCase
from application.usecases.user.create import CreateUserUseCase
from application.usecases.user.get_by_id import GetUserByIdUseCase
from infra.adapters.config import Config
from infra.adapters.jwt import JWTAdapter
from infra.adapters.password_hasher import PasswordHasher
from infra.adapters.repositories.decisions_repository import DecisionsRepository
from infra.adapters.repositories.experiments_repository import (
    ExperimentsRepository,
)
from infra.adapters.repositories.feature_flags_repository import (
    FeatureFlagsRepository,
)
from infra.adapters.repositories.users_repository import UserRepository


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

    container.register(UsersRepositoryPort, UserRepository)
    container.register(DecisionsRepositoryPort, DecisionsRepository)
    container.register(FeatureFlagsRepositoryPort, FeatureFlagsRepository)
    container.register(ExperimentsRepositoryPort, ExperimentsRepository)

    container.register(CreateUserUseCase)
    container.register(LoginUseCase)
    container.register(GetUserByIdUseCase)
    container.register(DecideUseCase)

    return container
