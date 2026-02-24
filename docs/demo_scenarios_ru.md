# Пакет тестовых данных и сценариев демо

Документ описывает контролируемый набор данных и сценариев для демонстрации ключевых критериев (B1, B2, B4, B5, B6, B9).

Во всех примерах предполагается, что сервис запущен согласно `docs/runbook_ru.md`, а авторизация выполняется с помощью JWT токена администратора (`Authorization: Bearer <token>`).

## 1. Тестовые данные

### 1.1. Субъекты (пользователи)

Для e2e-тестов используются заранее создаваемые пользователи (см. `tests/e2e/conftest.py`):

- `e2e-user-alice`
- `e2e-user-bob`
- `alice-diff`
- `bob-diff`
- `dedup-test-user`
- `validation-user`
- `anon-user`

В e2e-тестах пользователи создаются напрямую через модель `UserModel`. На демо можно либо воспользоваться готовыми фикстурами (запуск тестов), либо создать пользователей заранее через админские эндпоинты.

Для демонстрации распределения трафика и стабильности (determinism/weights) **рекомендуется завести ~100 пользователей**. Это можно сделать через `POST /auth/register` от имени администратора, например:

```bash
for i in $(seq -w 1 100); do
  curl -X POST http://localhost:8000/auth/register \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"demo-user-${i}@example.com\",
      \"password\": \"demo_user_pass\",
      \"role\": \"viewer\"
    }"
done
```

Далее в шагах с `/decide` можно использовать этих пользователей как `subject_id` (например, `demo-user-001`, `demo-user-002`, …) или продолжать использовать логически отделённые `subject_id` (u-001…u-100), если субъект идентифицируется иначе, чем пользователь.

### 1.2. Базовые сущности для сквозного сценария

Будем использовать следующие ключи:

- Флаг: `e2e_button_color`
- Типы событий:
  - `exposure` — факт показа варианта;
  - `e2e_conversion` — целевая конверсия (требует экспозиции).
- Метрика:
  - `e2e_conversion_rate` — отношение числа конверсий к числу экспозиций.
- Эксперимент:
  - флаг `e2e_button_color`;
  - варианты `control` (green) и `treatment` (blue) с весами 0.5 / 0.5;
  - целевая метрика `e2e_conversion_rate`.

Все примеры ниже опираются на этот набор.

---

## 2. Позитивные сценарии

### 2.1. Сквозной поток: decide → events → report

**Цель:** показать основной happy-path от настройки эксперимента до получения отчёта.

**Шаги:**

1. **Создать feature flag**

```bash
curl -X POST http://localhost:8000/feature-flags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "e2e_button_color",
    "value_type": "string",
    "default_value": "green"
  }'
```

Ожидаемый результат: `201 Created` (или `400`, если флаг уже существует).

2. **Создать типы событий**

```bash
curl -X POST http://localhost:8000/event-types \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "exposure",
    "name": "Exposure",
    "description": "User saw the variant",
    "required_params": {},
    "requires_exposure": false
  }'

curl -X POST http://localhost:8000/event-types \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "e2e_conversion",
    "name": "E2E Conversion",
    "description": "User converted",
    "required_params": {},
    "requires_exposure": true
  }'
```

Ожидаемый результат: `201 Created` (или `400`, если тип уже существует).

3. **Создать метрику конверсии**

```bash
curl -X POST http://localhost:8000/metrics \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "e2e_conversion_rate",
    "name": "E2E Conversion Rate",
    "calculation_rule": "{\"type\":\"RATIO\",\"numerator\":{\"type\":\"COUNT\",\"event_type_key\":\"e2e_conversion\"},\"denominator\":{\"type\":\"COUNT\",\"event_type_key\":\"exposure\"}}",
    "aggregation_unit": "user"
  }'
```

Ожидаемый результат: `201 Created` (или `400`).

4. **Создать эксперимент**

```bash
curl -X POST http://localhost:8000/experiments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "flag_key": "e2e_button_color",
    "name": "E2E Button Color Test",
    "audience_fraction": 1.0,
    "variants": [
      {"name": "control", "value": "green", "weight": 0.5, "is_control": true},
      {"name": "treatment", "value": "blue", "weight": 0.5, "is_control": false}
    ],
    "target_metric_key": "e2e_conversion_rate",
    "metric_keys": ["e2e_conversion_rate"]
  }'
```

Ожидаемый результат: `201 Created`, в теле — `id` эксперимента.

5. **Ревью и запуск эксперимента**

```bash
EXP_ID=<id_эксперимента_из_шага_4>

curl -X POST "http://localhost:8000/experiments/$EXP_ID/send-to-review" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "http://localhost:8000/experiments/$EXP_ID/approve" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"comment": "LGTM"}'

curl -X POST "http://localhost:8000/experiments/$EXP_ID/launch" \
  -H "Authorization: Bearer $TOKEN"
```

Ожидаемый результат:

- после `approve` — статус `approved`;
- после `launch` — статус `running`.

6. **Получить решения `/decide` для нескольких субъектов**

```bash
for subj in e2e-user-alice e2e-user-bob; do
  curl -X POST http://localhost:8000/decide \
    -H "Content-Type: application/json" \
    -d "{
      \"subject_id\": \"${subj}\",
      \"flag_keys\": [\"e2e_button_color\"],
      \"attributes\": {}
    }"
done
```

Ожидаемый результат:

- статус `200 OK`;
- в ответе `decisions.e2e_button_color` содержит:
  - `id` (UUID) — `decision_id`;
  - `value` — `green` или `blue`;
  - `experiment_id` — не `null`;
  - `variant_name` — `control` или `treatment`;
  - `timestamp` — unix-число.

7. **Отправить события `/events` для выданных решений**

Для простоты можно взять `decision_id` из ответов предыдущего шага и сформировать payload:

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type_key": "exposure",
        "decision_id": "<decision_id_alice>",
        "timestamp": 1737720000,
        "props": {}
      },
      {
        "event_type_key": "e2e_conversion",
        "decision_id": "<decision_id_alice>",
        "timestamp": 1737720010,
        "props": {}
      }
    ]
  }'
```

Ожидаемый результат:

- статус `200 OK`;
- `accepted > 0`, `rejected = 0`.

8. **Получить отчёт**

```bash
FROM_UNIX=1737716400   # now - 1h (пример)
TO_UNIX=1737723600     # now + 1h (пример)

curl -X GET "http://localhost:8000/experiments/$EXP_ID/report?from_time=$FROM_UNIX&to_time=$TO_UNIX" \
  -H "Authorization: Bearer $TOKEN"
```

Ожидаемый результат:

- статус `200 OK`;
- поля:
  - `experiment_id` = `$EXP_ID`;
  - `variants` — два варианта, у каждого есть `metrics`;
  - `overall.metrics` не пустой;
  - `from_time` и `to_time` — unix-числа.

### 2.2. Детерминизм / decide

**Цель:** B2-4 — при неизменной конфигурации один и тот же субъект получает стабильный вариант.

Шаги:

1. Дважды вызвать `/decide` для одного и того же `subject_id` и `flag_key` при запущенном эксперименте:

```bash
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "e2e-user-alice",
    "flag_keys": ["e2e_button_color"],
    "attributes": {}
  }'
```

2. Сравнить `variant_name` и `id` решения.

Ожидаемый результат: `variant_name` и `id` (decision_id) остаются одинаковыми при повторном запросе.

---

## 3. Негативные сценарии

### 3.1. Неизвестный тип события

**Цель:** B4-1/B4-2 — валидировать тип и обязательные поля события.

Шаги:

1. Получить `decision_id` через `/decide` (как в позитивном сценарии).
2. Отправить событие с несуществующим `event_type_key`:

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d "{
    \"events\": [
      {
        \"event_type_key\": \"nonexistent_event_xyz\",
        \"decision_id\": \"${DECISION_ID}\",
        \"timestamp\": 1737720000,
        \"props\": {}
      }
    ]
  }"
```

Ожидаемый результат:

- статус `200 OK`;
- `rejected = 1`, `accepted = 0`;
- в поле `errors[0].index = 0` — индекс проблемного события.

### 3.2. Невалидный тип поля `timestamp`

**Цель:** показать типовую валидацию (B4-1).

Шаги:

1. В payload одного события указать `"timestamp": "NOT_A_DATE"`.

Ожидаемый результат:

- `rejected` увеличивается;
- в `errors[0].index` указан индекс невалидного элемента;
- второе (валидное) событие в батче либо `accepted`, либо `duplicates`, но не теряется.

### 3.3. Дубликат события

**Цель:** B4-3 — дедупликация.

Шаги:

1. Сформировать событие `exposure` с фиксированным `decision_id` и `timestamp`.
2. Дважды подряд отправить один и тот же payload в `/events`.

Ожидаемый результат:

- первый запрос: `accepted = 1`, `duplicates = 0`;
- второй запрос: `accepted = 0`, `duplicates = 1`.

---

## 4. Граничные сценарии

### 4.1. Флаг без активного эксперимента (B2-1)

**Цель:** подтвердить, что при отсутствии активного эксперимента возвращается `default`.

Шаги:

1. Создать флаг без эксперимента:

```bash
curl -X POST http://localhost:8000/feature-flags \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "key": "e2e_no_exp_flag",
    "value_type": "string",
    "default_value": "default_val"
  }'
```

2. Вызвать `/decide`:

```bash
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{
    "subject_id": "anon-user",
    "flag_keys": ["e2e_no_exp_flag"],
    "attributes": {}
  }'
```

Ожидаемый результат:

- статус `200 OK`;
- `value = "default_val"`;
- `experiment_id = null`;
- `variant_name = null`.

### 4.2. Отчёт по несуществующему эксперименту

**Цель:** проверить поведение при запросе отчёта по несуществующему `experiment_id`.

Шаги:

```bash
curl -X GET "http://localhost:8000/experiments/00000000-0000-0000-0000-000000000001/report?from_time=1577836800&to_time=1577923200" \
  -H "Authorization: Bearer $TOKEN"
```

Ожидаемый результат: `404 Not Found`.

### 4.3. Частичный reject в батче событий

**Цель:** B4-1 — один невалидный элемент не должен ломать весь батч.

Шаги:

1. Сформировать батч из двух событий: первое с `"timestamp": "NOT_A_DATE"`, второе — валидное.
2. Отправить в `/events`.

Ожидаемый результат:

- статус `200 OK`;
- `rejected = 1`, `accepted >= 1` или `duplicates >= 1`;
- `errors` содержит одну запись с `index = 0`.

---

## 5. Сценарий для guardrails

Полноценный сценарий с срабатыванием guardrail зависит от конкретных порогов и объёма данных. Базовая проверка (см. юнит- и e2e-тесты) включает:

- создание guardrail-конфига с `metric_key`, `threshold`, `observation_window_minutes`, `action`;
- генерацию событий так, чтобы метрика превысила порог;
- ожидание запуска воркера `GuardrailCheckerWorker` (фоновый цикл на интервале `GUARDRAIL_CHECK_INTERVAL_SECONDS`);
- проверку:
  - что эксперимент переведён в состояние `paused` или активирован rollback;
  - что в логе есть запись со структурированными полями (`event="guardrail_triggered"`, `experiment_id`, `metric_key`, `threshold`, `actual_value`, `action`);
  - что в хранилище guardrail-триггеров есть соответствующая запись.

Для формальной защиты по критериям B5 на демо достаточно сослаться на конкретный тест/сценарий и показать один пример срабатывания (в логах и в состоянии эксперимента).

