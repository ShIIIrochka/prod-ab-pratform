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
from src.application.ports.experiment_versions_repository import (
    ExperimentVersionsRepositoryPort,
)
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
from src.application.ports.learnings_repository import (
    LearningsRepositoryPort,
)
from src.application.ports.metric_aggregator import MetricAggregatorPort
from src.application.ports.metrics_repository import MetricsRepositoryPort
from src.application.ports.notification_channel_configs_repository import (
    NotificationChannelConfigsRepositoryPort,
)
from src.application.ports.notification_deliveries_repository import (
    NotificationDeliveriesRepositoryPort,
)
from src.application.ports.notification_events_repository import (
    NotificationEventsRepositoryPort,
)
from src.application.ports.notification_rate_limiter import (
    NotificationRateLimiterPort,
)
from src.application.ports.notification_rules_repository import (
    NotificationRulesRepositoryPort,
)
from src.application.ports.notification_task_enqueuer import (
    NotificationTaskEnqueuerPort,
)
from src.application.ports.password_hasher import PasswordHasherPort
from src.application.ports.pending_events_store import PendingEventsStorePort
from src.application.ports.uow import UnitOfWorkPort
from src.application.ports.users_repository import UsersRepositoryPort
from src.application.services.domain_event_publisher import DomainEventPublisher
from src.application.services.notification_dispatcher import (
    NotificationDispatcher,
)
from src.application.usecases import (
    ApproveExperimentUseCase,
    ArchiveExperimentUseCase,
    CompleteExperimentUseCase,
    CreateExperimentUseCase,
    CreateFeatureFlagUseCase,
    CreateUserUseCase,
    DecideUseCase,
    GetExperimentUseCase,
    GetFeatureFlagUseCase,
    GetSimilarExperimentsUseCase,
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
from src.application.usecases.notifications.connect_slack import (
    ConnectSlackUseCase,
)
from src.application.usecases.notifications.connect_telegram import (
    ConnectTelegramUseCase,
)
from src.application.usecases.notifications.create_channel_config import (
    CreateChannelConfigUseCase,
)
from src.application.usecases.notifications.create_rule import (
    CreateNotificationRuleUseCase,
)
from src.application.usecases.notifications.delete_channel_config import (
    DeleteChannelConfigUseCase,
)
from src.application.usecases.notifications.list_channel_configs import (
    ListChannelConfigsUseCase,
)
from src.application.usecases.notifications.list_deliveries import (
    ListNotificationDeliveriesUseCase,
)
from src.application.usecases.notifications.list_rules import (
    ListNotificationRulesUseCase,
)
from src.application.usecases.notifications.update_rule import (
    UpdateNotificationRuleUseCase,
)
from src.application.usecases.reports.get_experiment_report import (
    GetExperimentReportUseCase,
)
from src.infra.adapters.config import Config
from src.infra.adapters.db.uow import UnitOfWork
from src.infra.adapters.jwt import JWTAdapter
from src.infra.adapters.opensearch.opensearch import OpenSearch
from src.infra.adapters.password_hasher import PasswordHasher
from src.infra.adapters.repositories import (
    DecisionsRepository,
    EventTypesRepository,
    EventsRepository,
    ExperimentsRepository,
    FeatureFlagsRepository,
    GuardrailConfigsRepository,
    GuardrailTriggersRepository,
    LearningsRepository,
    MetricsRepository,
    UserRepository,
)
from src.infra.adapters.repositories.experiment_versions_repository import (
    ExperimentVersionsRepository,
)
from src.infra.adapters.repositories.notification_channel_configs_repository import (
    NotificationChannelConfigsRepository,
)
from src.infra.adapters.repositories.notification_deliveries_repository import (
    NotificationDeliveriesRepository,
)
from src.infra.adapters.repositories.notification_events_repository import (
    NotificationEventsRepository,
)
from src.infra.adapters.repositories.notification_rules_repository import (
    NotificationRulesRepository,
)
from src.infra.adapters.services.celery_notification_task_enqueuer import (
    CeleryNotificationTaskEnqueuer,
)
from src.infra.adapters.services.event_id_generator import EventIdGenerator
from src.infra.adapters.services.event_validator import PydanticEventValidator
from src.infra.adapters.services.pending_events_store import (
    RedisPendingEventsStore,
)
from src.infra.adapters.services.redis_metric_aggregator import (
    RedisMetricAggregator,
)
from src.infra.adapters.services.redis_notification_rate_limiter import (
    RedisNotificationRateLimiter,
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
    container.register(
        ExperimentVersionsRepositoryPort, ExperimentVersionsRepository
    )

    container.register(
        OpenSearch,
        instance=OpenSearch(
            host=config.opensearch_host,
            port=config.opensearch_port,
            username=config.opensearch_username,
            password=config.opensearch_password,
            index_name=config.opensearch_index,
        ),
    )
    container.register(LearningsRepositoryPort, LearningsRepository)

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

    container.register(
        NotificationChannelConfigsRepositoryPort,
        NotificationChannelConfigsRepository,
    )
    container.register(
        NotificationRulesRepositoryPort, NotificationRulesRepository
    )
    container.register(
        NotificationEventsRepositoryPort, NotificationEventsRepository
    )
    container.register(
        NotificationDeliveriesRepositoryPort, NotificationDeliveriesRepository
    )
    container.register(
        NotificationRateLimiterPort,
        instance=RedisNotificationRateLimiter(redis=redis_client),
    )
    container.register(
        NotificationTaskEnqueuerPort,
        instance=CeleryNotificationTaskEnqueuer(),
    )
    container.register(NotificationDispatcher)
    container.register(DomainEventPublisher)

    container.register(CreateChannelConfigUseCase)
    container.register(ConnectTelegramUseCase)
    container.register(ConnectSlackUseCase)
    container.register(DeleteChannelConfigUseCase)
    container.register(ListChannelConfigsUseCase)
    container.register(CreateNotificationRuleUseCase)
    container.register(ListNotificationRulesUseCase)
    container.register(UpdateNotificationRuleUseCase)
    container.register(ListNotificationDeliveriesUseCase)

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
    container.register(ArchiveExperimentUseCase)

    container.register(SendEventsUseCase)
    container.register(CreateEventTypeUseCase)
    container.register(GetEventTypeUseCase)
    container.register(ListEventTypesUseCase)
    container.register(CreateMetricUseCase)
    container.register(GetMetricUseCase)
    container.register(ListMetricsUseCase)
    container.register(GetExperimentReportUseCase)
    container.register(CheckGuardrailsUseCase)
    container.register(GetSimilarExperimentsUseCase)

    container.register(
        PendingEventsTTLListener,
        instance=PendingEventsTTLListener(
            redis=redis_client,
            pending_store=container.resolve(PendingEventsStorePort),
            events_repository=container.resolve(EventsRepositoryPort),
        ),
    )

    container.register(
        GuardrailCheckerWorker,
        instance=GuardrailCheckerWorker(
            check_use_case=container.resolve(CheckGuardrailsUseCase),
            interval_seconds=config.guardrail_check_interval_seconds,
        ),
    )

    return container
