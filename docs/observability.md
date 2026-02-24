# Наблюдаемость и эксплуатационная готовность

## 1. Структурированные логи

Сервис пишет логи в **структурированном JSON-формате**.  
Формат инициализируется в `src/infra/observability/logging.py` и подключается в `src/main.py`.

- Переменная окружения **`LOG_FORMAT`**:
  - `json` (по умолчанию) — каждая запись лога одна строка JSON;
  - `plain` — человекочитаемый текстовый формат (удобен для локальной отладки).
- Переменная окружения **`LOG_LEVEL`** — уровень логирования (`INFO` по умолчанию).

Базовые поля JSON-записи:

- `timestamp` — время в ISO 8601, UTC;
- `level` — уровень (`INFO`, `WARNING`, `ERROR`, ...);
- `logger` — имя логгера (`src.application.usecases.guardrails.check_guardrails`, и т.п.);
- `message` — текст сообщения;
- дополнительные поля из `extra` — например `experiment_id`, `metric_key`, `event`, и т.п.

### Примеры записей логов

**1. Запуск воркера проверки guardrails**

```json
{"timestamp":"2025-02-24T10:00:00+00:00","level":"INFO","logger":"src.infra.workers.guardrail_checker_worker","message":"[GuardrailChecker] Worker started, interval=60s"}
```

**2. Отсутствие метрики для guardrail**

```json
{
  "timestamp": "2025-02-24T10:05:00+00:00",
  "level": "WARNING",
  "logger": "src.application.usecases.guardrails.check_guardrails",
  "message": "Guardrail metric not found for experiment, skipping",
  "experiment_id": "4e9d2f36-1c8a-4c66-9b3e-6c5f9a3b1234",
  "metric_key": "errors_ratio",
  "event": "guardrail_metric_missing"
}
```

**3. Срабатывание guardrail**

```json
{
  "timestamp": "2025-02-24T10:06:30+00:00",
  "level": "WARNING",
  "logger": "src.application.usecases.guardrails.check_guardrails",
  "message": "Guardrail triggered for experiment",
  "experiment_id": "4e9d2f36-1c8a-4c66-9b3e-6c5f9a3b1234",
  "metric_key": "errors_ratio",
  "threshold": 0.05,
  "actual_value": 0.083,
  "action": "pause",
  "event": "guardrail_triggered"
}
```

В Docker-композе логирование по умолчанию включено в JSON-формате через `LOG_FORMAT=json` для сервиса `api`.

---

## 2. Проверки liveness и readiness

Реализованы два эндпоинта в `src/presentation/rest/app.py`:

- **`GET /health`** — проверка живости процесса:
  - всегда возвращает `200 OK`, если процесс жив;
  - тело: `{"status": "ok"}`.
- **`GET /ready`** — проверка готовности к приёму запросов:
  - проверяет подключение к PostgreSQL и OpenSearch;
  - при успешной проверке зависимостей:
    - `200 OK`, тело: `{"status": "ready"}`;
  - при недоступности БД или OpenSearch:
    - `503 Service Unavailable`,
    - тело: `{"status": "not_ready", "db_ok": bool, "opensearch_ok": bool}`.

### Команды проверки

```bash
curl -i http://localhost:80/health
curl -i http://localhost:80/ready
```

Требование по критерию B9-1: `/ready` должен перейти в `200` не позднее чем через 180 секунд после старта сервиса (после того, как зависимости станут доступны).

---

## 3. Метрики Prometheus

Экспорт метрик настроен через эндпоинт:

- **`GET /metrics`** — в формате Prometheus text (см. `src/presentation/rest/app.py` и `src/infra/observability/metrics.py`).

Доступные метрики:

- `http_requests_total{method, path, status_code}` — общее число HTTP-запросов;
- `http_errors_total{method, path, status_code}` — число HTTP-ответов с 5xx;
- `decide_requests_total` — количество запросов к `/decide`;
- `events_received_total` — количество событий, полученных эндпоинтом `/events`;
- `events_rejected_total` — количество отклонённых событий в `/events`;
- `guardrail_triggered_total{metric_key, action}` — число срабатываний guardrail;
- `experiment_exposures_total{experiment_id, variant}` — количество экспозиций вариантов экспериментов;
- `active_experiments` — число запущенных экспериментов.

### Как проверить метрики на демо

1. Вызвать несколько раз `/decide` и `/events` согласно сценариям демо.
2. Открыть метрики:

```bash
curl http://localhost:8000/metrics
```

3. Убедиться, что счётчики `decide_requests_total`, `events_received_total`, `experiment_exposures_total` увеличиваются.

При использовании Docker Compose Prometheus и Grafana поднимаются согласно `docs/runbook_observability.md` и `prometheus.yml`, а дашборд можно импортировать из `docs/grafana_experiment_insights_dashboard.json`.

---

## 4. Команды lint и форматирования кода

Инструмент для линтинга и форматирования — **Ruff** (см. конфигурацию в `pyproject.toml`).

- **Линтинг:**

```bash
uv run ruff check .
```

- **Форматирование:**

```bash
uv run ruff format .
```

Эти команды используются в отчёте по тестированию и в runbook как часть инженерной дисциплины (критерий B10).
