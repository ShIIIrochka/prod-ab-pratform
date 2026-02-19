"""Парсер правил вычисления метрик.

Поддерживает два формата calculation_rule:

1. JSON:
   {"type":"COUNT","event_type_key":"conversion"}
   {"type":"RATIO","numerator":{...},"denominator":{...}}
   {"type":"PERCENTILE","event_type_key":"latency","property":"duration_ms","percentile":95}

2. DSL (человекочитаемый):
   COUNT(conversion)
   COUNT(error) / COUNT(exposure)
   AVG(latency, duration_ms)
   P95(latency, duration_ms)
   SUM(latency, duration_ms)
   PERCENTILE(latency, duration_ms, 95)
"""

from __future__ import annotations

import json
import re

from typing import Any


def _parse_simple_expr(expr: str) -> dict[str, Any] | None:
    """Парсит простое DSL-выражение (без '/')."""
    expr = expr.strip()
    if not expr:
        return None

    # COUNT(event_type)
    m = re.fullmatch(r"COUNT\s*\(\s*([\w.-]+)\s*\)", expr, re.IGNORECASE)
    if m:
        return {"type": "COUNT", "event_type_key": m.group(1)}

    # SUM(event_type, property)
    m = re.fullmatch(
        r"SUM\s*\(\s*([\w.-]+)\s*,\s*([\w.-]+)\s*\)", expr, re.IGNORECASE
    )
    if m:
        return {
            "type": "SUM",
            "event_type_key": m.group(1),
            "property": m.group(2),
        }

    # AVG(event_type, property)
    m = re.fullmatch(
        r"AVG\s*\(\s*([\w.-]+)\s*,\s*([\w.-]+)\s*\)", expr, re.IGNORECASE
    )
    if m:
        return {
            "type": "AVG",
            "event_type_key": m.group(1),
            "property": m.group(2),
        }

    # P95(event_type, property) или P50(...) и т.д.
    m = re.fullmatch(
        r"P(\d+)\s*\(\s*([\w.-]+)\s*,\s*([\w.-]+)\s*\)", expr, re.IGNORECASE
    )
    if m:
        return {
            "type": "PERCENTILE",
            "event_type_key": m.group(2),
            "property": m.group(3),
            "percentile": int(m.group(1)),
        }

    # PERCENTILE(event_type, property, N)
    m = re.fullmatch(
        r"PERCENTILE\s*\(\s*([\w.-]+)\s*,\s*([\w.-]+)\s*,\s*(\d+)\s*\)",
        expr,
        re.IGNORECASE,
    )
    if m:
        return {
            "type": "PERCENTILE",
            "event_type_key": m.group(1),
            "property": m.group(2),
            "percentile": int(m.group(3)),
        }

    return None


def _split_by_top_level_slash(raw: str) -> tuple[str, str] | None:
    """Находит '/' вне скобок и возвращает (левую, правую) части."""
    depth = 0
    for i, ch in enumerate(raw):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "/" and depth == 0:
            return raw[:i].strip(), raw[i + 1 :].strip()
    return None


def parse_calculation_rule(raw: str) -> dict[str, Any] | None:
    """Разбирает calculation_rule из JSON или DSL в словарь правила.

    Возвращает None если формат не распознан или строка пустая.
    """
    if not raw or not raw.strip():
        return None

    stripped = raw.strip()

    # Пробуем JSON первым (большинство правил в тестах — JSON)
    if stripped.startswith("{"):
        try:
            result = json.loads(stripped)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

    # DSL: проверяем RATIO (наличие '/' вне скобок)
    parts = _split_by_top_level_slash(stripped)
    if parts is not None:
        left, right = parts
        numerator = _parse_simple_expr(left)
        denominator = _parse_simple_expr(right)
        if numerator and denominator:
            return {
                "type": "RATIO",
                "numerator": numerator,
                "denominator": denominator,
            }

    # DSL: одиночное выражение
    return _parse_simple_expr(stripped)
