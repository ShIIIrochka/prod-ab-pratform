from __future__ import annotations

from src.domain.services.calculation_rule_parser import parse_calculation_rule


def test_json_count_rule() -> None:
    rule = '{"type":"COUNT","event_type_key":"click"}'
    result = parse_calculation_rule(rule)
    assert result == {"type": "COUNT", "event_type_key": "click"}


def test_json_ratio_rule() -> None:
    rule = '{"type":"RATIO","numerator":{"type":"COUNT","event_type_key":"conv"},"denominator":{"type":"COUNT","event_type_key":"view"}}'
    result = parse_calculation_rule(rule)
    assert result is not None
    assert result["type"] == "RATIO"
    assert result["numerator"]["event_type_key"] == "conv"


def test_json_sum_rule() -> None:
    rule = '{"type":"SUM","event_type_key":"purchase","property":"amount"}'
    result = parse_calculation_rule(rule)
    assert result is not None
    assert result["type"] == "SUM"
    assert result["property"] == "amount"


def test_json_avg_rule() -> None:
    rule = '{"type":"AVG","event_type_key":"session","property":"duration"}'
    result = parse_calculation_rule(rule)
    assert result is not None
    assert result["type"] == "AVG"


def test_json_percentile_rule() -> None:
    rule = '{"type":"PERCENTILE","event_type_key":"latency","property":"ms","percentile":95}'
    result = parse_calculation_rule(rule)
    assert result is not None
    assert result["type"] == "PERCENTILE"
    assert result["percentile"] == 95
    assert result["event_type_key"] == "latency"
    assert result["property"] == "ms"


def test_json_percentile_p50() -> None:
    rule = '{"type":"PERCENTILE","event_type_key":"response_time","property":"duration_ms","percentile":50}'
    result = parse_calculation_rule(rule)
    assert result is not None
    assert result["percentile"] == 50


def test_dsl_count() -> None:
    result = parse_calculation_rule("COUNT(click)")
    assert result == {"type": "COUNT", "event_type_key": "click"}


def test_dsl_count_case_insensitive() -> None:
    result = parse_calculation_rule("count(click)")
    assert result is not None
    assert result["type"] == "COUNT"


def test_dsl_ratio() -> None:
    result = parse_calculation_rule("COUNT(conversion) / COUNT(exposure)")
    assert result is not None
    assert result["type"] == "RATIO"
    assert result["numerator"]["event_type_key"] == "conversion"
    assert result["denominator"]["event_type_key"] == "exposure"


def test_dsl_sum() -> None:
    result = parse_calculation_rule("SUM(purchase, amount)")
    assert result is not None
    assert result["type"] == "SUM"
    assert result["event_type_key"] == "purchase"
    assert result["property"] == "amount"


def test_dsl_avg() -> None:
    result = parse_calculation_rule("AVG(session, duration)")
    assert result is not None
    assert result["type"] == "AVG"
    assert result["event_type_key"] == "session"


def test_dsl_p95_shorthand() -> None:
    """P95(event, prop) shorthand should resolve to PERCENTILE type with percentile=95."""
    result = parse_calculation_rule("P95(latency, duration_ms)")
    assert result is not None
    assert result["type"] == "PERCENTILE"
    assert result["percentile"] == 95
    assert result["event_type_key"] == "latency"
    assert result["property"] == "duration_ms"


def test_dsl_p50_shorthand() -> None:
    result = parse_calculation_rule("P50(latency, duration_ms)")
    assert result is not None
    assert result["type"] == "PERCENTILE"
    assert result["percentile"] == 50


def test_dsl_percentile_explicit() -> None:
    result = parse_calculation_rule("PERCENTILE(latency, duration_ms, 99)")
    assert result is not None
    assert result["type"] == "PERCENTILE"
    assert result["percentile"] == 99
    assert result["event_type_key"] == "latency"
    assert result["property"] == "duration_ms"


def test_dsl_percentile_with_whitespace() -> None:
    result = parse_calculation_rule(
        "  PERCENTILE( latency , duration_ms , 75 )  "
    )
    assert result is not None
    assert result["type"] == "PERCENTILE"
    assert result["percentile"] == 75


def test_empty_string_returns_none() -> None:
    assert parse_calculation_rule("") is None
    assert parse_calculation_rule("   ") is None


def test_invalid_json_falls_back_to_dsl_or_none() -> None:
    result = parse_calculation_rule("{invalid json}")
    assert result is None


def test_completely_invalid_returns_none() -> None:
    assert parse_calculation_rule("NOT_A_FUNCTION(foo)") is None


def test_ratio_without_valid_operands_returns_none() -> None:
    result = parse_calculation_rule("NOT_VALID / ALSO_NOT_VALID")
    assert result is None


def test_nested_json_ratio_is_parsed() -> None:
    rule = """{
        "type": "RATIO",
        "numerator": {"type": "COUNT", "event_type_key": "signup"},
        "denominator": {"type": "COUNT", "event_type_key": "pageview"}
    }"""
    result = parse_calculation_rule(rule)
    assert result is not None
    assert result["type"] == "RATIO"
