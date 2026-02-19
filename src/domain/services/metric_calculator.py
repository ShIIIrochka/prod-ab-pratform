from __future__ import annotations

import statistics

from typing import Any

from src.domain.aggregates.event import AttributionStatus, Event
from src.domain.aggregates.metric import Metric
from src.domain.services.calculation_rule_parser import parse_calculation_rule


def _filter_attributed(events: list[Event]) -> list[Event]:
    return [
        e
        for e in events
        if e.attribution_status == AttributionStatus.ATTRIBUTED
    ]


def _filter_by_type(events: list[Event], event_type_key: str) -> list[Event]:
    return [e for e in events if e.event_type_key == event_type_key]


def _extract_numeric_property(
    events: list[Event], property_name: str
) -> list[float]:
    values = []
    for e in events:
        raw = e.props.get(property_name)
        if raw is not None:
            try:
                values.append(float(raw))
            except (TypeError, ValueError):
                pass
    return values


def _evaluate_rule(rule: dict[str, Any], events: list[Event]) -> float:
    """Вычисляет значение одного правила агрегации.

    Поддерживаемые типы:
    - COUNT: количество событий указанного типа
    - SUM: сумма числового свойства из props
    - AVG: среднее числового свойства
    - PERCENTILE: перцентиль числового свойства
    - RATIO: соотношение двух под-правил (numerator / denominator)
    """
    rule_type = rule.get("type", "").upper()

    if rule_type == "COUNT":
        event_type_key = rule.get("event_type_key")
        if not event_type_key:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        return float(len(filtered))

    if rule_type == "SUM":
        event_type_key = rule.get("event_type_key")
        prop = rule.get("property")
        if not event_type_key or not prop:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        values = _extract_numeric_property(filtered, prop)
        return sum(values) if values else 0.0

    if rule_type == "AVG":
        event_type_key = rule.get("event_type_key")
        prop = rule.get("property")
        if not event_type_key or not prop:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        values = _extract_numeric_property(filtered, prop)
        return statistics.mean(values) if values else 0.0

    if rule_type == "PERCENTILE":
        event_type_key = rule.get("event_type_key")
        prop = rule.get("property")
        percentile = rule.get("percentile", 95)
        if not event_type_key or not prop:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        values = _extract_numeric_property(filtered, prop)
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile / 100)
        idx = min(idx, len(sorted_values) - 1)
        return sorted_values[idx]

    if rule_type == "RATIO":
        numerator_rule = rule.get("numerator")
        denominator_rule = rule.get("denominator")
        if not numerator_rule or not denominator_rule:
            return 0.0
        numerator = _evaluate_rule(numerator_rule, events)
        denominator = _evaluate_rule(denominator_rule, events)
        if denominator == 0:
            return 0.0
        return numerator / denominator

    return 0.0


def calculate_metric(metric: Metric, events: list[Event]) -> float:
    """Вычисляет значение метрики по списку событий.

    Перед вычислением фильтрует только ATTRIBUTED-события.
    Правило вычисления задаётся в JSON формате в поле calculation_rule.

    Пример calculation_rule:
        '{"type": "COUNT", "event_type_key": "conversion"}'
        '{"type": "RATIO",
          "numerator": {"type": "COUNT", "event_type_key": "conversion"},
          "denominator": {"type": "COUNT", "event_type_key": "exposure"}}'
        '{"type": "PERCENTILE", "event_type_key": "latency",
          "property": "duration_ms", "percentile": 95}'
    """
    attributed_events = _filter_attributed(events)

    rule = parse_calculation_rule(metric.calculation_rule)
    if rule is None:
        return 0.0

    return _evaluate_rule(rule, attributed_events)
