# Runbook запуска и проверки A/B Platform (RU)

## 1. Предусловия

Перед запуском убедитесь, что выполнены следующие условия:

- Установлен **Python 3.14+**.
- Установлен менеджер пакетов **`uv`**.
- Доступна СУБД **PostgreSQL** (по умолчанию `localhost:5432`).
- Доступен **Redis** (по умолчанию `localhost:6379`).
- (Опционально) Доступны:
  - **OpenSearch** — для поиска похожих экспериментов (Learnings Library);
  - **RabbitMQ** — для фоновой отправки уведомлений через Celery.
- Настроены переменные окружения (см. `.env.example` или таблицу ниже).

### 1.1. Основные переменные окружения

| Переменная | Значение по умолчанию | Назначение |
|-----------|------------------------|------------|
| `DB_HOST` | `localhost` | хост PostgreSQL |
| `DB_PORT` | `5432` | порт PostgreSQL |
| `DB_USER` | `postgres` | пользователь БД |
| `DB_PASSWORD` | `postgres` | пароль БД |
| `DB_NAME` | `ab_platform` | имя БД |
| `REDIS_URL` | `redis://localhost:6379/0` | URL Redis (broker / rate limiter) |
| `JWT_SECRET` | — (обязательно задать) | секрет для подписи JWT |
| `JWT_ALG` | `HS256` | алгоритм подписи JWT |
| `JWT_ACCESS_EXPIRES` | `3600` | TTL access-токена (секунды) |
| `JWT_REFRESH_EXPIRES` | `86400` | TTL refresh-токена (секунды) |
| `GUARDRAIL_CHECK_INTERVAL_SECONDS` | `60` | период проверки guardrails (секунды) |
| `OPENSEARCH_URL` | `https://localhost:9200` | базовый URL OpenSearch |
| `OPENSEARCH_INDEX` | `learnings` | индекс для Learnings Library |
| `LOG_FORMAT` | `json` | формат логов (`json` или `plain`) |
| `LOG_LEVEL` | `INFO` | уровень логирования |
| `ADMIN_EMAIL` | — (опционально) | e-mail первого админа: при старте создаётся пользователь с ролью Admin, если такого ещё нет |
| `ADMIN_PASSWORD` | — (опционально) | пароль для этого пользователя |

**Регистрация пользователей:** эндпоинт `POST /auth/register` доступен **только администратору** (Admin). Чтобы получить первого админа, задайте `ADMIN_EMAIL` и `ADMIN_PASSWORD` и запустите приложение — при старте будет создан пользователь-админ, после чего можно войти через `POST /auth/login` и создавать остальных пользователей через `/auth/register`.

Для Docker Compose значения по умолчанию заданы в `docker-compose.yml`.

---

## 2. Инициализация базы данных

Перед первым запуском API необходимо применить миграции:

```bash
uv run aerich upgrade
```

Команда использует конфигурацию Tortoise ORM/Aerich из `src/main.py` и `src/infra/aerich_config.py`.

---

## 3. Запуск API-сервера

### 3.1. Запуск с granian (рекомендуется для продакшена)

```bash
uv run granian --interface asgi src.main:app --host 0.0.0.0 --port 8000
```

После запуска API будет доступен по адресу `http://localhost:8000`.

### 3.2. Запуск с uvicorn (для разработки)

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 4. Запуск фонового воркера (уведомления)

Если вы используете функциональность уведомлений (Telegram/Slack и др.), необходимо запустить Celery worker:

```bash
celery -A src.infra.celery_app worker -l info
```

При необходимости можно задать очередь и конкуренцию:

```bash
celery -A src.infra.celery_app worker -l info -Q celery --concurrency=2
```

---

## 5. Запуск стека через Docker Compose

Для быстрого старта всех зависимостей можно воспользоваться Docker Compose (см. `docker-compose.yml`):

```bash
docker compose up --build
```

В составе docker-compose поднимаются:

- `api` — backend на FastAPI/Granian (`http://localhost:8000`);
- `postgres` — PostgreSQL;
- `redis` — Redis;
- `opensearch` — OpenSearch (для Learnings);
- `rabbitmq` — брокер для Celery.

---

## 6. Проверки готовности сервиса

После запуска API выполните проверки:

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

- `/health` должен вернуть `200 OK` и `{"status": "ok"}`.
- `/ready`:
  - `200 OK` и `{"status": "ready"}` — сервис готов принимать запросы;
  - `503 Service Unavailable` и тело `{"status": "not_ready", "db_ok": ..., "opensearch_ok": ...}` — пока не готовы внешние зависимости.

Критерий B9-1: `/ready` должен перейти в `200` не позднее чем через 180 секунд после старта.

---

## 7. Запуск тестов

### 7.1. Unit-тесты

```bash
uv run pytest tests/unit/ -v
```

### 7.2. E2E-тесты

Требуется запущенный PostgreSQL и Redis, а также корректные переменные окружения (см. `tests/e2e/conftest.py`).

```bash
cp .env.example .env
export $(cat .env)

uv run pytest tests/e2e/ -v
```

### 7.3. Все тесты

```bash
uv run pytest -v
```

При необходимости можно добавить запуск покрытия (coverage), например:

```bash
uv run coverage run -m pytest
uv run coverage report
```

---

## 8. Команды lint и форматирования

Для поддержания инженерной дисциплины используются команды Ruff:

- Линтинг:

```bash
uv run ruff check .
```

- Форматирование:

```bash
uv run ruff format .
```


- Линтинг + форматирование + статическая проверка типов:
```bash
pip install pre-commit
pre-commit run --all-files
```


Конфигурация линтера и форматтера находится в `pyproject.toml` в секциях `[tool.ruff]`.

---

## 9. Краткий сценарий проверки (happy-path B1/B2/B4/B6)

1. Запустить сервисы (PostgreSQL, Redis, API) по инструкциям выше.
2. Зарегистрировать администратора и получить JWT-токен (`/auth/register`, `/auth/login`).
3. Создать feature flag, типы событий и метрику, затем эксперимент (см. подробный пакет сценариев в `docs/demo_scenarios_ru.md`).
4. Перевести эксперимент через статусы `draft → in_review → approved → running`.
5. Вызвать `/decide` для нескольких субъектов, сохранить `decision_id`.
6. Отправить события `/events` (exposure + conversion) с правильными `decision_id`.
7. Получить отчёт `/experiments/{id}/report` и убедиться, что по вариантам есть метрики, а fields `from_time`/`to_time` — unix-таймштампы.

Детализированные шаги, негативные и граничные сценарии приведены в `docs/demo_scenarios_ru.md`.

---

## 10. Скрипты для проверки (жюри)

В каталоге `scripts/` лежат Python-скрипты для быстрой проверки ключевых сценариев без ручного вызова API. Требуется установленный `requests` (или запуск через `uv run python scripts/...` в корне репозитория).

**Переменные окружения:**

- `BASE_URL` — базовый URL API (по умолчанию `http://localhost:80`);
- `ADMIN_EMAIL`, `ADMIN_PASSWORD` — учётные данные администратора (должны совпадать с созданным при старте админом, например из `ADMIN_EMAIL`/`ADMIN_PASSWORD` в docker-compose или .env).

### 10.1. Смоук: decide → events → report

Проверяет полный happy-path: создание флага, типов событий, метрики, эксперимента, ревью и запуск, вызов `/decide`, отправка событий, получение отчёта и наличие блока `data_quality`.

```bash
export ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=admin_pass
python scripts/smoke_decide_events_report.py
# или: uv run python scripts/smoke_decide_events_report.py
```

Код выхода: 0 — успех, 1 — ошибка.

### 10.2. Проверка уведомлений

Подключает Slack (если задан `SLACK_WEBHOOK_URL`), создаёт эксперимент и переводит его в статус «запущен», чтобы в очередь уведомлений попали события. Доставка зависит от работающего Celery worker.

```bash
export ADMIN_EMAIL=... ADMIN_PASSWORD=...
# опционально: export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
python scripts/check_notifications.py
```

### 10.3. Проверка метрик и Insights

Выводит блок `data_quality` отчёта по эксперименту и проверяет наличие счётчиков в `/metrics`. Если `EXPERIMENT_ID` не задан, выбирается первый запущенный эксперимент.

```bash
export ADMIN_EMAIL=... ADMIN_PASSWORD=...
# опционально: export EXPERIMENT_ID=... FROM_TIME=... TO_TIME=...
python scripts/check_insights_metrics.py
```
