# Карта репозитория

Краткий ориентир по структуре проекта и точкам входа. Соответствует критерию B7-8.

---

## Точки входа

| Назначение | Путь | Описание |
|------------|------|----------|
| ASGI-приложение | `src/main.py` | Инициализация логирования, конфига, создание `app`. Точка входа для `granian`/`uvicorn`. |
| Конфигурация миграций | `src/infra/aerich_config.py` | Используется Aerich для Tortoise ORM. |
| Сборка DI-контейнера | `src/infra/bootstrap.py` | Регистрация портов, адаптеров и use case. |

---

## Основные папки и модули

```
src/
├── main.py                 # Точка входа, setup_logging(), app
├── application/            # Слой приложения
│   ├── dto/                # DTO запросов/ответов (auth, decide, user, reports, events, notifications, learnings)
│   ├── ports/              # Абстракции репозиториев и сервисов
│   ├── usecases/           # Сценарии: auth, decide, user, experiment, events, guardrails, reports, notifications, learnings, metrics, event_type, feature_flag
│   └── services/           # DomainEventPublisher, NotificationDispatcher, NotificationEventProcessor
├── domain/                 # Доменный слой
│   ├── aggregates/         # Experiment, User, Decision, Event, Metric и др.
│   ├── entities/           # GuardrailConfig, NotificationRule, NotificationChannelConfig и др.
│   ├── value_objects/      # Роли, статусы, типы событий, JWT payload
│   ├── services/           # DecisionEngine, ParticipationGuard, EventAttribution, MetricCalculator
│   ├── events/             # Доменные события (GuardrailTriggered и др.)
│   └── exceptions/         # Доменные исключения
├── presentation/
│   └── rest/               # HTTP API
│       ├── app.py          # FastAPI, lifespan, /health, /ready, /metrics, подключение роутов
│       ├── routes/         # auth, decide, events, experiments, feature_flags, reports, metrics, event_types, notifications, learnings, experiment_versions
│       ├── dependencies.py # Контейнер, require_roles
│       ├── middlewares.py  # JWTBackend, MetricsMiddleware
│       └── exception_handlers.py
└── infra/                  # Инфраструктура
    ├── adapters/           # БД (Tortoise), Redis, OpenSearch, Celery, JWT, password hasher, репозитории, каналы уведомлений
    ├── observability/      # Логирование (JSON), метрики Prometheus
    └── workers/            # GuardrailCheckerWorker, PendingEventsTTLListener
```

---

## Критичный поток decide → event → report / guardrail

| Этап | Где смотреть |
|------|----------------------|
| **Decide** | `src/presentation/rest/routes/decide.py` → `src/application/usecases/decide.py` (DecideUseCase), домен: `src/domain/services/decision_engine.py`, `src/domain/services/participation_guard.py`. Репозитории: feature_flags, experiments, decisions, users. |
| **Events** | `src/presentation/rest/routes/events.py` → `src/application/usecases/events/send.py` (SendEventsUseCase). Валидация, дедупликация, атрибуция, запись в events и обновление метрик (MetricAggregatorPort). |
| **Report** | `src/presentation/rest/routes/reports.py` → `src/application/usecases/reports/get_experiment_report.py` (GetExperimentReportUseCase). Чтение событий по эксперименту/вариантам, расчёт метрик. |
| **Guardrail** | Фоновый цикл в `src/infra/workers/guardrail_checker_worker.py` → `src/application/usecases/guardrails/check_guardrails.py` (CheckGuardrailsUseCase). Чтение конфигов guardrails, получение метрик через MetricAggregatorPort, сравнение с порогом, запись триггера и смена статуса эксперимента. |

Тесты критичного пути: `tests/e2e/test_decide_event_report.py`, `tests/unit/usecases/test_check_guardrails*.py`.
