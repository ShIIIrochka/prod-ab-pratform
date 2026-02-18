from jam.aio import Jam
from punq import Container
from redis.asyncio import Redis

from src.application.ports.decisions_repository import DecisionsRepositoryPort
from src.application.ports.event_id_generator import EventIdGeneratorPort
from src.application.ports.event_types_repository import (
    EventTypesRepositoryPort,
)
from src.application.ports.event_validator import EventValidatorPort
from src.application.ports.events_repository import EventsRepositoryPort
from src.application.ports.experiments_repository import (
    ExperimentsRepositoryPort,
)
from src.application.ports.feature_flags_repository import (
    FeatureFlagsRepositoryPort,
)
from src.application.ports.jwt import JWTPort
from src.application.ports.password_hasher import PasswordHasherPort
from src.application.ports.pending_events_store import PendingEventsStorePort
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
    SendExperimentToReviewUseCase,
    UpdateExperimentUseCase,
    UpdateFeatureFlagDefaultValueUseCase,
)
from src.application.usecases.event_type.create import CreateEventTypeUseCase
from src.application.usecases.event_type.get import GetEventTypeUseCase
from src.application.usecases.event_type.list import ListEventTypesUseCase
from src.application.usecases.events.send import SendEventsUseCase
from src.infra.adapters.config import Config
from src.infra.adapters.db.uow import UnitOfWork
from src.infra.adapters.jwt import JWTAdapter
from src.infra.adapters.password_hasher import PasswordHasher
from src.infra.adapters.repositories import (
    DecisionsRepository,
    EventTypesRepository,
    EventsRepository,
    ExperimentsRepository,
    FeatureFlagsRepository,
    UserRepository,
)
from src.infra.adapters.services.event_id_generator import EventIdGenerator
from src.infra.adapters.services.event_validator import PydanticEventValidator
from src.infra.adapters.services.pending_events_store import (
    RedisPendingEventsStore,
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
    container.register(EventsRepositoryPort, EventsRepository)
    container.register(EventTypesRepositoryPort, EventTypesRepository)
    container.register(EventIdGeneratorPort, EventIdGenerator)

    # Redis клиент — синглтон для всего приложения
    redis_client = Redis.from_url(config.redis_url, decode_responses=False)
    container.register(Redis, instance=redis_client)

    # Валидатор событий (Pydantic, без проникновения в usecase)
    container.register(
        EventValidatorPort,
        instance=PydanticEventValidator(),
    )

    # Pending-хранилище (Redis)
    container.register(
        PendingEventsStorePort,
        instance=RedisPendingEventsStore(redis=redis_client),
    )

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
    container.register(CompleteExperimentUseCase)

    container.register(SendEventsUseCase)
    container.register(CreateEventTypeUseCase)
    container.register(GetEventTypeUseCase)
    container.register(ListEventTypesUseCase)

    return container
