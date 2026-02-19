"""Unit tests for Metric domain model with key as primary identifier."""

from __future__ import annotations

from src.domain.aggregates.metric import Metric


def test_metric_has_key():
    """Metric должен использовать key как primary identifier."""
    metric = Metric(
        key="error_rate",
        name="Error Rate",
        calculation_rule='{"type":"RATIO"}',
    )
    assert metric.key == "error_rate"


def test_metric_key_is_unique_identifier():
    """Два разных Metric имеют разные key."""
    m1 = Metric(
        key="m1",
        name="M1",
        calculation_rule='{"type":"COUNT","event_type_key":"click"}',
    )
    m2 = Metric(
        key="m2",
        name="M2",
        calculation_rule='{"type":"COUNT","event_type_key":"click"}',
    )
    assert m1.key != m2.key


def test_metric_calculation_rule_stored():
    """calculation_rule сохраняется как есть."""
    rule = '{"type":"COUNT","event_type_key":"click"}'
    metric = Metric(key="ctr", name="CTR", calculation_rule=rule)
    assert metric.calculation_rule == rule


def test_metric_dsl_rule_stored():
    """DSL calculation_rule сохраняется без изменений."""
    metric = Metric(
        key="err", name="Err", calculation_rule="COUNT(error) / COUNT(exposure)"
    )
    assert metric.calculation_rule == "COUNT(error) / COUNT(exposure)"


def test_metric_requires_exposure_default_false():
    """По умолчанию requires_exposure = False."""
    metric = Metric(key="m", name="M", calculation_rule="{}")
    assert metric.requires_exposure is False
