from __future__ import annotations

import statistics

from collections import defaultdict
from typing import Any

from src.domain.aggregates.event import Event
from src.domain.aggregates.metric import AggregationUnit, Metric
from src.domain.services.calculation_rule_parser import parse_calculation_rule


# def _filter_attributed(events: list[Event]) -> list[Event]:
#     return [
#         e
#         for e in events
#         if e.attribution_status == AttributionStatus.ATTRIBUTED
#     ]


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


def _deduplicate_by_user(events: list[Event]) -> list[Event]:
    seen: set[tuple[str, str]] = set()
    result: list[Event] = []
    for e in events:
        key = (e.subject_id, e.event_type_key)
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


def _group_by_user(events: list[Event]) -> dict[str, list[Event]]:
    groups: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        groups[e.subject_id].append(e)
    return dict(groups)


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


def _evaluate_rule_user(rule: dict[str, Any], events: list[Event]) -> float:
    """Вычисляет метрику с единицей агрегации = пользователь.

    - COUNT: количество уникальных пользователей, у которых есть хотя бы одно
      событие указанного типа.
    - SUM/AVG/PERCENTILE: агрегация по значениям, усреднённым на пользователя
      (один пользователь — одно значение, равное среднему по его событиям).
    - RATIO: числитель/знаменатель считаются поверх user-deduplicated событий.
    """
    rule_type = rule.get("type", "").upper()

    if rule_type == "COUNT":
        event_type_key = rule.get("event_type_key")
        if not event_type_key:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        return float(len({e.subject_id for e in filtered}))
    if rule_type == "SUM":
        event_type_key = rule.get("event_type_key")
        prop = rule.get("property")
        if not event_type_key or not prop:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        by_user = _group_by_user(filtered)
        per_user_values = [
            statistics.mean(_extract_numeric_property(u_events, prop))
            for u_events in by_user.values()
            if _extract_numeric_property(u_events, prop)
        ]
        return sum(per_user_values) if per_user_values else 0.0

    if rule_type == "AVG":
        event_type_key = rule.get("event_type_key")
        prop = rule.get("property")
        if not event_type_key or not prop:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        by_user = _group_by_user(filtered)
        per_user_values = [
            statistics.mean(_extract_numeric_property(u_events, prop))
            for u_events in by_user.values()
            if _extract_numeric_property(u_events, prop)
        ]
        return statistics.mean(per_user_values) if per_user_values else 0.0

    if rule_type == "PERCENTILE":
        event_type_key = rule.get("event_type_key")
        prop = rule.get("property")
        percentile = rule.get("percentile", 95)
        if not event_type_key or not prop:
            return 0.0
        filtered = _filter_by_type(events, event_type_key)
        by_user = _group_by_user(filtered)
        per_user_values = [
            statistics.mean(_extract_numeric_property(u_events, prop))
            for u_events in by_user.values()
            if _extract_numeric_property(u_events, prop)
        ]
        if not per_user_values:
            return 0.0
        sorted_vals = sorted(per_user_values)
        idx = min(
            int(len(sorted_vals) * percentile / 100), len(sorted_vals) - 1
        )
        return sorted_vals[idx]

    if rule_type == "RATIO":
        numerator_rule = rule.get("numerator")
        denominator_rule = rule.get("denominator")
        if not numerator_rule or not denominator_rule:
            return 0.0
        numerator = _evaluate_rule_user(numerator_rule, events)
        denominator = _evaluate_rule_user(denominator_rule, events)
        if denominator == 0:
            return 0.0
        return numerator / denominator

    return 0.0


def calculate_metric(metric: Metric, events: list[Event]) -> float:
    """Вычисляет значение метрики по списку событий.

    Перед вычислением фильтрует только ATTRIBUTED-события.
    Если aggregation_unit == "user", агрегирует по уникальным пользователям.

    Пример calculation_rule:
        '{"type": "COUNT", "event_type_key": "conversion"}'
        '{"type": "RATIO",
          "numerator": {"type": "COUNT", "event_type_key": "conversion"},
          "denominator": {"type": "COUNT", "event_type_key": "exposure"}}'
        '{"type": "PERCENTILE", "event_type_key": "latency",
          "property": "duration_ms", "percentile": 95}'
    """
    # attributed_events = _filter_attributed(events)

    rule = parse_calculation_rule(metric.calculation_rule)
    if rule is None:
        return 0.0

    if metric.aggregation_unit == AggregationUnit.USER:
        return _evaluate_rule_user(rule, events)
    return _evaluate_rule(rule, events)
