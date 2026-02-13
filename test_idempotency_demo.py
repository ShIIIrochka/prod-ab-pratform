"""Демонстрация идемпотентности Decision API.

Этот тест показывает, что повторные запросы с одинаковыми параметрами
возвращают один и тот же decision_id (ТЗ 3.5.3).
"""

from uuid import UUID

from src.domain.services.decision_id_generator import (
    generate_deterministic_decision_id,
)


def test_idempotency():
    """Проверяет, что одинаковые параметры → один decision_id."""
    # Параметры первого запроса
    subject_id = "user-123"
    flag_key = "button_color"
    experiment_id = UUID("550e8400-e29b-41d4-a716-446655440000")
    variant_id = "blue"
    timestamp_day = "2026-02-13"

    # Первый запрос
    decision_id_1 = generate_deterministic_decision_id(
        subject_id=subject_id,
        flag_key=flag_key,
        experiment_id=experiment_id,
        variant_id=variant_id,
        timestamp_day=timestamp_day,
    )

    # Ретрай с теми же параметрами
    decision_id_2 = generate_deterministic_decision_id(
        subject_id=subject_id,
        flag_key=flag_key,
        experiment_id=experiment_id,
        variant_id=variant_id,
        timestamp_day=timestamp_day,
    )

    # ✅ Должны быть одинаковыми!
    assert decision_id_1 == decision_id_2
    print(f"✅ Идемпотентность работает: {decision_id_1}")

    # Проверяем, что изменение параметра → другой ID
    decision_id_3 = generate_deterministic_decision_id(
        subject_id="user-456",  # Другой пользователь
        flag_key=flag_key,
        experiment_id=experiment_id,
        variant_id=variant_id,
        timestamp_day=timestamp_day,
    )

    assert decision_id_1 != decision_id_3
    print(f"✅ Разные параметры → разный ID: {decision_id_3}")

    # Проверяем default (без эксперимента)
    decision_id_default = generate_deterministic_decision_id(
        subject_id=subject_id,
        flag_key=flag_key,
        experiment_id=None,  # Нет эксперимента
        variant_id=None,
        timestamp_day=timestamp_day,
    )

    assert decision_id_1 != decision_id_default
    print(f"✅ Default значение → свой ID: {decision_id_default}")


if __name__ == "__main__":
    test_idempotency()
    print("\n" + "=" * 60)
    print("DEMO: Идемпотентность Decision API")
    print("=" * 60)
    print()
    print("Сценарий: Продукт ретраит запрос из-за сетевого сбоя")
    print()
    print("1. Первый запрос decide(user-123, button_color)")
    print("   → decision_id: abc123...")
    print()
    print("2. Сеть глючит, продукт ретраит")
    print("   → decision_id: abc123... (ТОТ ЖЕ!)")
    print()
    print("3. Продукт отправляет событие с decision_id: abc123")
    print("   ✅ Событие корректно атрибутируется")
    print()
    print("=" * 60)
