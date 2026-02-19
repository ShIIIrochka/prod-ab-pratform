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
from src.application.ports.guardrail_configs_repository import (
    GuardrailConfigsRepositoryPort,
)
from src.application.ports.guardrail_triggers_repository import (
    GuardrailTriggersRepositoryPort,
)
from src.application.ports.jwt import JWTPort
from src.application.ports.metric_aggregator import MetricAggregatorPort
from src.application.ports.metrics_repository import MetricsRepositoryPort
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
from src.application.usecases.guardrails.check_guardrails import (
    CheckGuardrailsUseCase,
)
from src.application.usecases.metrics.create import CreateMetricUseCase
from src.application.usecases.metrics.get import GetMetricUseCase
from src.application.usecases.metrics.list import ListMetricsUseCase
from src.application.usecases.reports.get_experiment_report import (
    GetExperimentReportUseCase,
)
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
    GuardrailConfigsRepository,
    GuardrailTriggersRepository,
    MetricsRepository,
    UserRepository,
)
from src.infra.adapters.services.event_id_generator import EventIdGenerator
from src.infra.adapters.services.event_validator import PydanticEventValidator
from src.infra.adapters.services.pending_events_store import (
    RedisPendingEventsStore,
)
from src.infra.adapters.services.redis_metric_aggregator import (
    RedisMetricAggregator,
)
from src.infra.workers.guardrail_checker_worker import GuardrailCheckerWorker
from src.infra.workers.pending_events_ttl_listener import (
    PendingEventsTTLListener,
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
    container.register(MetricsRepositoryPort, MetricsRepository)
    container.register(
        GuardrailConfigsRepositoryPort, GuardrailConfigsRepository
    )
    container.register(
        GuardrailTriggersRepositoryPort, GuardrailTriggersRepository
    )

    redis_client = Redis.from_url(config.redis_url, decode_responses=True)
    container.register(Redis, instance=redis_client)

    container.register(
        EventValidatorPort,
        instance=PydanticEventValidator(),
    )

    container.register(
        PendingEventsStorePort,
        instance=RedisPendingEventsStore(
            redis=redis_client, ttl_seconds=config.pending_events_ttl_seconds
        ),
    )

    container.register(
        MetricAggregatorPort,
        instance=RedisMetricAggregator(redis=redis_client),
    )

    container.register(CreateUserUseCase)
    container.register(LoginUseCase)
    container.register(GetUserByIdUseCase)
    container.register(
        DecideUseCase,
        factory=lambda: DecideUseCase(
            feature_flags_repository=container.resolve(
                FeatureFlagsRepositoryPort
            ),
            experiments_repository=container.resolve(ExperimentsRepositoryPort),
            decisions_repository=container.resolve(DecisionsRepositoryPort),
            user_repository=container.resolve(UsersRepositoryPort),
            uow=container.resolve(UnitOfWorkPort),
            max_concurrent_experiments=config.max_concurrent_experiments,
            cooldown_period_days=config.cooldown_period_days,
            experiments_before_cooldown=config.experiments_before_cooldown,
            cooldown_experiment_probability=config.cooldown_experiment_probability,
            rotation_period_days=config.rotation_period_days,
        ),
    )

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

    container.register(
        SendEventsUseCase,
        factory=lambda: SendEventsUseCase(
            events_repository=container.resolve(EventsRepositoryPort),
            event_types_repository=container.resolve(EventTypesRepositoryPort),
            decisions_repository=container.resolve(DecisionsRepositoryPort),
            event_id_generator=container.resolve(EventIdGeneratorPort),
            event_validator=container.resolve(EventValidatorPort),
            pending_events_store=container.resolve(PendingEventsStorePort),
            guardrail_configs_repository=container.resolve(
                GuardrailConfigsRepositoryPort
            ),
            metrics_repository=container.resolve(MetricsRepositoryPort),
            metric_aggregator=container.resolve(MetricAggregatorPort),
            uow=container.resolve(UnitOfWorkPort),
        ),
    )
    container.register(CreateEventTypeUseCase)
    container.register(GetEventTypeUseCase)
    container.register(ListEventTypesUseCase)
    container.register(CreateMetricUseCase)
    container.register(GetMetricUseCase)
    container.register(ListMetricsUseCase)
    container.register(GetExperimentReportUseCase)
    container.register(
        CheckGuardrailsUseCase,
        factory=lambda: CheckGuardrailsUseCase(
            experiments_repository=container.resolve(ExperimentsRepositoryPort),
            guardrail_configs_repository=container.resolve(
                GuardrailConfigsRepositoryPort
            ),
            guardrail_triggers_repository=container.resolve(
                GuardrailTriggersRepositoryPort
            ),
            metrics_repository=container.resolve(MetricsRepositoryPort),
            metric_aggregator=container.resolve(MetricAggregatorPort),
            uow=container.resolve(UnitOfWorkPort),
        ),
    )

    container.register(
        PendingEventsTTLListener,
        instance=PendingEventsTTLListener(
            redis=redis_client,
            pending_store=container.resolve(PendingEventsStorePort),
            events_repository=container.resolve(EventsRepositoryPort),
        ),
    )

    guardrail_checker_interval = int(
        __import__("os").environ.get("GUARDRAIL_CHECK_INTERVAL_SECONDS", "60")
    )
    container.register(
        GuardrailCheckerWorker,
        instance=GuardrailCheckerWorker(
            check_use_case=container.resolve(CheckGuardrailsUseCase),
            interval_seconds=guardrail_checker_interval,
        ),
    )

    return container
