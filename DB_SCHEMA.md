# База данных LOTTY A/B Platform

## Обзор

База данных спроектирована для поддержки всех основных функций платформы:
- Feature flags и управление конфигурацией
- Эксперименты и A/B тестирование
- Runtime решения (decision_log)
- События и атрибуция
- Каталоги метрик и типов событий
- Управление пользователями и ревью

**СУБД:** PostgreSQL (через asyncpg)  
**ORM:** Tortoise ORM  
**Миграции:** Aerich

---

## Почему subject_id: string, а не UUID?

**Из ТЗ (раздел 3.2):**
> **идентификатор субъекта** — стабильный идентификатор субъекта (например, **идентификатор пользователя или устройства**)

**Причины:**

1. **Гибкость интеграции**: продукт может использовать:
   - `device_id` (строка типа "DEVICE-ABC-123")
   - `external_user_id` (из внешней системы, не наш UUID)
   - `cookie_id`, `session_id` (строки)
   - Композитные ключи (например, "platform:user_id")

2. **Независимость от внутренней системы**: продукт не обязан использовать UUID платформы

3. **Детерминизм хеширования**: для decision_engine важна строковая стабильность

4. **Соответствие индустрии**: Google Optimize, LaunchDarkly, Optimizely — все принимают строковый user_id

**Вывод:** `subject_id: VARCHAR` правильно по ТЗ.

---

## ER-диаграмма

```mermaid
erDiagram
    users ||--o{ experiments : owns
    users ||--o{ approvals : approves
    
    feature_flags ||--o{ experiments : "uses flag"
    
    experiments ||--|{ variants : "has variants"
    experiments ||--o{ approvals : "receives approvals"
    experiments ||--o{ guardrail_configs : "has guardrails"
    experiments ||--o{ decisions : "applied in"
    
    decisions ||--o{ events : "linked by decision_id"
    
    event_types ||--o{ events : "categorizes"
    metrics }o--o{ experiments : "measures"
    
    users {
        uuid id PK
        string email UK
        string role
        json approval_group_json
        datetime created_at
    }
    
    feature_flags {
        string key PK
        string value_type
        json default_value_json
        string description
        uuid owner_id FK
        datetime created_at
        datetime updated_at
    }
    
    experiments {
        uuid id PK
        string flag_key FK
        string name
        string status
        int version
        float audience_fraction
        json targeting_rule_json
        uuid owner_id FK
        string target_metric_key FK
        json metric_keys_json
        bool rollback_to_control_active
        json completion_json
        datetime created_at
        datetime updated_at
    }
    
    variants {
        int id PK
        uuid experiment_id FK
        string name
        json value_json
        float weight
        bool is_control
    }
    
    approvals {
        int id PK
        uuid experiment_id FK
        uuid user_id FK
        string comment
        datetime timestamp
    }
    
    guardrail_configs {
        int id PK
        uuid experiment_id FK
        string metric_key FK
        float threshold
        int observation_window_minutes
        string action
    }
    
    decisions {
        uuid id PK
        string subject_id
        string flag_key
        json value
        uuid experiment_id
        string variant_id
        int experiment_version
        datetime timestamp
    }
    
    events {
        string id PK
        string event_type_key FK
        uuid decision_id FK
        string subject_id
        datetime timestamp
        json props
        string attribution_status
    }
    
    event_types {
        string key PK
        string name
        string description
        json required_params_json
        bool requires_exposure
    }
    
    metrics {
        string key PK
        string name
        string calculation_rule
        bool requires_exposure
        string description
    }
```
